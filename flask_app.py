from flask import Flask, render_template
from flask_fontawesome import FontAwesome

import scripts.utils.utils as ut
from data_prep import *
from scripts.utils.constants import STANDINGS_COLUMNS_FLASK, RECORDS_COLUMNS_FLASK, ALLTIME_COLUMNS_FLASK


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

    headings_season_sim = tuple(['Team', 'Matchup', 'THW', 'Total', 'Points', 'Playoff%', 'Finals%', 'Champion%'])
    data_season_sim = ut.flask_get_data(season_sim_table)
    return render_template(
        "simulations.html", week=f'Week {week}',
        headings_bets=headings_bets, data_bets=data_bets,
        headings_s=headings_season_sim, data_s=data_season_sim,
        # headings_w=headings_w, data_w=data_w,
        # headings_r=headings_r, data_r=data_r,
        # headings_p=headings_p, data_p=data_p,
        tstamp_bets=timestamp_betting, tstamp_s=timestamp_season_sim
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

    headings_ss = tuple(ut.flatten_list([['Team'], list(ss_disp.columns[1:len(teams.team_ids)+2])]))
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
    headings_alltime = tuple(['Team', 'Seasons', 'Playoffs', 'Overall', 'Win%', 'Matchup', 'Top Half', 'Points'])
    data_alltime = ut.flask_get_data(alltime_df[ALLTIME_COLUMNS_FLASK])

    headings_rec = tuple(['Category', 'Record', 'Holder', 'Season', 'Week'])
    data_rec = ut.flask_get_data(records_df[RECORDS_COLUMNS_FLASK])
    return render_template("records.html",
                           headings_alltime=headings_alltime, data_alltime=data_alltime,
                           headings_rec=headings_rec, data_rec=data_rec)

# Run app
if __name__ == "__main__":
    app.run()
