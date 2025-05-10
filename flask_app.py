import pandas as pd
from flask import Flask, render_template
from flask_fontawesome import FontAwesome

import scripts.utils.utils as ut
from scripts.utils.constants import STANDINGS_COLUMNS
from scripts.home.standings import Standings

season, week = 2024, 10  # just finished previous week
standings = Standings(season=season, week=week)
standings_df = standings.format_standings()
clinches = standings.clinching_scenarios()

# create flask app
app = Flask(__name__)
fa = FontAwesome(app)

###########################
# Flask routes
##########################


@app.route("/")
def home():
    headings_st = tuple(['Seed', 'Team', 'Overall', 'Win%', 'Matchup', 'THW', 'Points', 'WB-Bye', 'WB-5', 'PB-6'])
    data_st = ut.flask_get_data(standings_df[STANDINGS_COLUMNS])

    return render_template(
        "powerrank.html", week=f'Week {week}',
        headings_st=headings_st, data_st=data_st,
        # headings_pr=headings_pr, data_pr=data_pr,
        # rank_data=rank_data
    )

# @app.route("/simulations/")
def sims():
    pass
#     return render_template("simulations.html", headings_bets=headings_bets, data_bets=data_bets,
#                                             #   headings_s=headings_s, data_s=data_s,
#                                             #   headings_w=headings_w, data_w=data_w,
#                                             #   headings_r=headings_r, data_r=data_r,
#                                             #   headings_p=headings_p, data_p=data_p,
#                                               week_bet=week_bet, tstamp=tstamp,
#                                               tstamp_ssn=tstamp_ssn)

@app.route("/scenarios/")
def scen():
    pass
#     return render_template("scenarios.html", headings_scen=headings_scen, data_scen=data_scen,
#                                              headings2_scen=headings2_scen, data2_scen=data2_scen)

@app.route("/efficiency/")
def eff():
    pass
#     return render_template("efficiencies.html", eff_plot=eff_plot2, pos_plot=pos_plot2)

@app.route("/champions/")
def champs():
    pass
#     champs = pd.read_csv("//home//hgupta//fantasy-football-league-report//champions.csv")
#     champs["Count"] = champs.groupby("Team").cumcount()+1
#     #champs = champs.assign(Icon=champs["Count"].apply(lambda n: n*'<span class="fab fa-trophy"></span>'))
#     prev_champs = champs[["Season", "Team"]]
#     champ_count = champs.drop_duplicates(subset="Team", keep="last").sort_values(["Count", "Season"], ascending=False).drop("Season", axis=1)
#
#     headings_pc = tuple(prev_champs.columns)
#     data_pc = [tuple(x) for x in prev_champs.to_numpy()]
#
#     headings_cc = tuple(champ_count.columns)
#     data_cc = [tuple(x) for x in champ_count.to_numpy()]
#
#     return render_template("champions.html", headings_pc=headings_pc, data_pc=data_pc,
#                                              headings_cc=headings_cc, data_cc=data_cc,
#                                              champs=champs)

@app.route("/records/")
def records():
    pass
    # return render_template("records.html", headings_alltime=headings_alltime, data_alltime=data_alltime,
    #                                        headings_rec=headings_rec, data_rec=data_rec)

# Run app
if __name__ == "__main__":
    app.run()
