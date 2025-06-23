import pandas as pd
import json
from flask import Flask, render_template
from flask_fontawesome import FontAwesome

from scripts.api.DataLoader import DataLoader
from scripts.utils.database import Database
from scripts.api.Settings import Params
from scripts.api.Teams import Teams
from scripts.api.Rosters import Rosters
import scripts.utils.utils as ut
from scripts.utils.constants import STANDINGS_COLUMNS_FLASK, RECORDS_COLUMNS_FLASK
from scripts.home.standings import Standings
from scripts.scenarios.scenarios import get_total_wins, get_wins_by_week, get_wins_vs_opp, get_schedule_switcher_display
from scripts.simulations import week_sim as ws
from scripts.efficiency.efficiencies import plot_efficiency

# TODO: webpage errors out if past regular season
season, week = 2024, 12  # just finished previous week
data = DataLoader(season)
params = Params(data)
teams = Teams(data)
matchups = data.matchups()

week = params.regular_season_end+1 if week > params.regular_season_end+1 else week
# week_data = data.load_week(week=week)
# rosters = Rosters()

standings = Standings(season=season, week=week)
standings_df = standings.format_standings()
clinches = standings.clinching_scenarios()
# TODO: fix last week clinches/elims. if team is ahead (cl) or behind (el), net wins should be 0?

db_pr = Database(table='power_ranks', season=season, week=week)
pr_data = db_pr.retrieve_data(how='season')
pr_data[['power_score_norm', 'score_norm_change']] = round(pr_data[['power_score_norm', 'score_norm_change']] * 100).astype('Int32')
pr_table = pr_data[pr_data.week == week-1]
pr_table = pr_table.sort_values('power_score_raw', ascending=False)
pr_table['rank_change'] = -pr_table.rank_change
pr_table[['total_points', 'weekly_points', 'consistency', 'luck']] = pr_table[['season_idx', 'week_idx', 'consistency_idx', 'luck_idx']].rank(ascending=False, method='min').astype('Int32')
pr_cols = ['team', 'total_points', 'weekly_points', 'consistency', 'luck', 'power_rank', 'rank_change', 'power_score_norm', 'score_norm_change']
rank_data = pr_data[['team', 'week', 'power_rank', 'power_score_norm']].sort_values(['week', 'power_score_norm'], ascending=[True, False]).to_dict(orient='records')
rank_data = json.dumps(rank_data, indent=2)
rank_data = {'rank_data': rank_data}

db_betting = Database(table='betting_table', season=season, week=week)
betting_table = db_betting.retrieve_data(how='week')
betting_table = betting_table.sort_values(['matchup_id', 'avg_score'])
betting_table['avg_score'] = betting_table.avg_score.round(1).apply(lambda x: f'{x:.2f}')
betting_table['p_win'] = betting_table.p_win.apply(lambda x: ws.calculate_odds(init_prob=x))
betting_table['p_tophalf'] = betting_table.p_tophalf.apply(lambda x: ws.calculate_odds(init_prob=x))
betting_table['p_highest'] = betting_table.p_highest.apply(lambda x: ws.calculate_odds(init_prob=x))
betting_table['p_lowest'] = betting_table.p_lowest.apply(lambda x: ws.calculate_odds(init_prob=x))

db_h2h = Database(table='h2h', season=season, week=week)
h2h_data = db_h2h.retrieve_data(how='season')
total_wins = get_total_wins(h2h_data=h2h_data, params=params, teams=teams, week=week)
wins_by_week = get_wins_by_week(h2h_data=h2h_data, total_wins=total_wins, teams=teams)
wins_vs_opp = get_wins_vs_opp(h2h_data=h2h_data, total_wins=total_wins, wins_by_week=wins_by_week, params=params, week=week)

db_ss = Database(table='switcher', season=season, week=week)
ss_data = db_ss.retrieve_data(how='season')
ss_disp = get_schedule_switcher_display(ss_data=ss_data, total_wins=total_wins, params=params, week=week)

eff_plot = plot_efficiency(database=Database(),
                           season=season, week=week-1,
                           x='actual_lineup_score', y='optimal_lineup_score',
                           xlab='Difference From Optimal Points per Week',
                           ylab='Optimal Points per Week',
                           title='')

db = Database(table='records')
records_df = db.retrieve_data(how='all')

# champs = pd.read_csv("//home//hgupta//fantasy-football-league-report//champions.csv")
champs = pd.read_csv('C:\Dev\hgupta94\cool_league\champions.csv').sort_values('Season', ascending=False)
champs["Count"] = champs.groupby("Team").cumcount()+1
champs = champs.assign(Icon=champs["Count"].apply(
    lambda n: ''.join(
        [
            # '<i class="fa fa-trophy icon-gold"></i>' for _ in range(n)
            f'<i class="fa fa-trophy icon-gold"></i>{"" if (i + 1) % 3 else "<span><br></span>"}' for i in range(n)
        ]
    ) + '<br>'
))
prev_champs = champs[['Season', 'Team', 'Runner Up']]
champ_count = (
    champs
    .drop_duplicates(subset='Team', keep='last')
    .sort_values(['Count'], ascending=False)
    .drop(['Season', 'Count'], axis=1)
    .rename(columns={'Icon': 'Count'})
)


# create flask app
app = Flask(__name__)
fa = FontAwesome(app)

###########################
# Flask routes
##########################


@app.route("/")
def home():
    headings_st = tuple(['Rk', 'Team', 'Overall', 'Win%', 'Matchup', 'THW', 'Points', 'WB-Bye', 'WB-5', 'PB-6'])
    data_st = ut.flask_get_data(standings_df[STANDINGS_COLUMNS_FLASK])

    cl_cols = ['Team', 'To Clinch', 'Net Wins', 'Clinch Over (Net Pts)' if week == params.regular_season_end else 'Clinch Over']
    headings_cl = tuple(cl_cols) if clinches['clinches'] else tuple()
    data_cl = ut.flask_get_data(clinches['clinches']) if clinches['clinches'] else tuple()

    el_cols = ['Team', 'Elim. From', 'Net Wins', 'Elim. By (Net Pts)' if week == params.regular_season_end else 'Elim. By']
    headings_el = tuple(el_cols) if clinches['eliminations'] else tuple()
    data_el = ut.flask_get_data(clinches['eliminations']) if clinches['eliminations'] else tuple()

    headings_pr = tuple(['Team', 'Season', 'Recency', 'Consistency', 'Luck', 'Rank', '1 Week \u0394', 'Score', '1 Week \u0394'])
    data_pr = ut.flask_get_data(pr_table[pr_cols])
    # TODO: add vertical line to separate inputs from outputs

    return render_template(
        "powerrank.html", week=f'Week {week-1}',
        headings_st=headings_st, data_st=data_st,
        headings_cl=headings_cl, data_cl=data_cl,
        headings_el=headings_el, data_el=data_el,
        headings_pr=headings_pr, data_pr=data_pr,
        rank_data=rank_data
    )

@app.route("/simulations/")
def sims():
    headings_bets = tuple(['ID', 'Team', 'Points', 'Matchup', 'THW', 'Highest', 'Lowest'])
    data_bets = ut.flask_get_data(betting_table[['matchup_id', 'team', 'avg_score', 'p_win', 'p_tophalf', 'p_highest', 'p_lowest']])
    return render_template(
        "simulations.html", week=f'Week {week}',
        headings_bets=headings_bets, data_bets=data_bets,
        # headings_s=headings_s, data_s=data_s,
        # headings_w=headings_w, data_w=data_w,
        # headings_r=headings_r, data_r=data_r,
        # headings_p=headings_p, data_p=data_p,
        # week_bet=week_bet, tstamp=tstamp,
        # tstamp_ssn=tstamp_ssn
    )

@app.route("/scenarios/")
def scenarios():
    headings_h2h = tuple(
        ut.flatten_list(
            [
                ['Team'], list(wins_vs_opp.columns[1:len(teams.team_ids)+1]), ['Record', 'Win%']
            ]
        )
    )
    data_h2h = ut.flask_get_data(wins_vs_opp)

    headings_wk = tuple(
        ut.flatten_list(
            [
                ['Team'], list(wins_by_week.columns[1:week]), ['# First', '# Last']
            ]
        )
    )
    data_wk = ut.flask_get_data(wins_by_week)
    data_styled = ut.flask_get_data([
        [
            f'<span class="perfect-week">{cell}</span>' if cell.endswith('-0')
            else f'<span class="winless-week">{cell}</span>' if cell.startswith('0-')
            else cell
            for cell in row
        ]
        for row in data_wk
    ])

    headings_ss = tuple(ut.flatten_list([['Team'], list(ss_disp.columns[1:len(teams.team_ids)+1])]))
    data_ss = ut.flask_get_data(ss_disp)

    return render_template("scenarios.html",
                           headings_h2h=headings_h2h, data_h2h=data_h2h,
                           headings_wk=headings_wk, data_wk=data_styled,
                           headings_ss=headings_ss, data_ss=data_ss)

@app.route("/efficiency/")
def eff():
    return render_template("efficiencies.html", eff_plot=eff_plot)

@app.route("/champions/")
def champs():
    headings_pc = tuple(prev_champs.columns)
    data_pc = ut.flask_get_data(prev_champs)

    headings_cc = tuple(champ_count.columns)
    data_cc = ut.flask_get_data(champ_count)

    return render_template("champions.html",
                           headings_pc=headings_pc, data_pc=data_pc,
                           headings_cc=headings_cc, data_cc=data_cc)

@app.route("/records/")
def records():
    headings_rec = tuple(['Category', 'Record', 'Holder', 'Season', 'Week'])
    data_rec = ut.flask_get_data(records_df[RECORDS_COLUMNS_FLASK])
    return render_template("records.html", #headings_alltime=headings_alltime, data_alltime=data_alltime,
                                           headings_rec=headings_rec, data_rec=data_rec)

# Run app
if __name__ == "__main__":
    app.run()
