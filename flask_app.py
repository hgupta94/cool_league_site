import pandas as pd
import json
from flask import Flask, render_template
from flask_fontawesome import FontAwesome

from scripts.api.DataLoader import DataLoader
from scripts.utils.database import Database
import scripts.utils.utils as ut
from scripts.utils.constants import STANDINGS_COLUMNS_FLASK, RECORDS_COLUMNS_FLASK
from scripts.home.standings import Standings
from scripts.simulations import week_sim as ws
from scripts.efficiency.efficiencies import plot_efficiency

season, week = 2023, 13  # just finished previous week
standings = Standings(season=season, week=week)
standings_df = standings.format_standings()
clinches = standings.clinching_scenarios()

db = Database(table='power_ranks', season=season, week=week)
pr_data = db.retrieve_data(how='season')
pr_data[['power_score_norm', 'score_norm_change']] = round(pr_data[['power_score_norm', 'score_norm_change']] * 100).astype('Int32')
pr_table = pr_data[pr_data.week == week]
pr_table = pr_table.sort_values('power_score_norm', ascending=False)
pr_table[['total_points', 'weekly_points', 'consistency', 'luck']] = pr_table[['season_idx', 'week_idx', 'consistency_idx', 'luck_idx']].rank(ascending=False, method='min').astype('Int32')
pr_cols = ['team', 'total_points', 'weekly_points', 'consistency', 'luck', 'power_rank', 'rank_change', 'power_score_norm', 'score_norm_change']
rank_data = pr_data[['team', 'week', 'power_rank', 'power_score_norm']].sort_values(['week', 'power_score_norm'], ascending=[True, False]).to_dict(orient='records')
rank_data = json.dumps(rank_data, indent=2)
rank_data = {'rank_data': rank_data}

db = Database(table='betting_table', season=season, week=week)
betting_table = db.retrieve_data(how='week')
betting_table = betting_table.sort_values(['matchup_id', 'avg_score'])
betting_table['p_win'] = betting_table.p_win.apply(lambda x: ws.calculate_odds(init_prob=x))
betting_table['p_tophalf'] = betting_table.p_tophalf.apply(lambda x: ws.calculate_odds(init_prob=x))
betting_table['p_highest'] = betting_table.p_highest.apply(lambda x: ws.calculate_odds(init_prob=x))
betting_table['p_lowest'] = betting_table.p_lowest.apply(lambda x: ws.calculate_odds(init_prob=x))


eff_plot = plot_efficiency(database=Database(),
                           season=season, week=week,
                           x='actual_lineup_score', y='optimal_lineup_score',
                           xlab='Difference From Optimal Points per Week',
                           ylab='Optimal Points per Week',
                           title='')

db = Database(table='records')
records_df = db.retrieve_data(how='all')


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

    headings_cl = tuple(['Team', 'To Clinch', 'Net Wins', 'Clinched Over']) if clinches['clinches'] else tuple()
    headings_el = tuple(['Team', 'Eliminated From', 'Net Wins', 'Eliminated By']) if clinches['eliminations'] else tuple()
    data_cl = ut.flask_get_data(clinches['clinches']) if clinches['clinches'] else tuple()
    data_el = ut.flask_get_data(clinches['eliminations']) if clinches['eliminations'] else tuple()

    headings_pr = tuple(['Team', 'Season', 'Recency', 'Consistency', 'Luck', 'Power Rank', '1 Week \u0394', 'Power Score', '1 Week \u0394'])
    data_pr = ut.flask_get_data(pr_table[pr_cols])
    # TODO: add vertical line to separate inputs from outputs

    return render_template(
        "powerrank.html", week=f'Week {week}',
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
        "simulations.html", week=f'Week {week+1}',
        headings_bets=headings_bets, data_bets=data_bets,
        # headings_s=headings_s, data_s=data_s,
        # headings_w=headings_w, data_w=data_w,
        # headings_r=headings_r, data_r=data_r,
        # headings_p=headings_p, data_p=data_p,
        # week_bet=week_bet, tstamp=tstamp,
        # tstamp_ssn=tstamp_ssn
    )

@app.route("/scenarios/")
def scen():
    pass
#     return render_template("scenarios.html", headings_scen=headings_scen, data_scen=data_scen,
#                                              headings2_scen=headings2_scen, data2_scen=data2_scen)

@app.route("/efficiency/")
def eff():
    return render_template("efficiencies.html", eff_plot=eff_plot)

@app.route("/champions/")
def champs():
    pass
#     champs = pd.read_csv("//home//hgupta//fantasy-football-league-report//champions.csv")
    champs = pd.read_csv('champions.csv')
    champs["Count"] = champs.groupby("Team").cumcount()+1
    #champs = champs.assign(Icon=champs["Count"].apply(lambda n: n*'<span class="fab fa-trophy"></span>'))
    prev_champs = champs[["Season", "Team"]]
    champ_count = champs.drop_duplicates(subset="Team", keep="last").sort_values(["Count", "Season"], ascending=False).drop("Season", axis=1)

    headings_pc = tuple(prev_champs.columns)
    data_pc = [tuple(x) for x in prev_champs.to_numpy()]

    headings_cc = tuple(champ_count.columns)
    data_cc = [tuple(x) for x in champ_count.to_numpy()]

    return render_template("champions.html", headings_pc=headings_pc, data_pc=data_pc,
                                             headings_cc=headings_cc, data_cc=data_cc,
                                             champs=champs)

@app.route("/records/")
def records():
    headings_rec = tuple(['Category', 'Record', 'Holder', 'Season', 'Week'])
    data_rec = ut.flask_get_data(records_df[RECORDS_COLUMNS_FLASK])
    return render_template("records.html", #headings_alltime=headings_alltime, data_alltime=data_alltime,
                                           headings_rec=headings_rec, data_rec=data_rec)

# Run app
if __name__ == "__main__":
    app.run()
