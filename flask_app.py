import pandas as pd
from flask import Flask, render_template
from flask_fontawesome import FontAwesome

from scripts.api.DataLoader import DataLoader
from scripts.utils.database import Database
import scripts.utils.utils as ut
from scripts.utils.constants import STANDINGS_COLUMNS
from scripts.home.standings import Standings

season, week = 2024, 10  # just finished previous week
standings = Standings(season=season, week=week)
standings_df = standings.format_standings()
clinches = standings.clinching_scenarios()

db = Database(table='betting_table', season=season, week=week)
betting_table = db.retrieve_data()
betting_table = betting_table.sort_values(['matchup_id', 'avg_score'])

# from scripts.utils.constants import TEAM_IDS
# from scripts.api.Teams import Teams
# betting_table = pd.read_csv(r'tables/betting_table.csv')
# betting_table['matchup_id'] = None
# data23 = DataLoader(year=2023)
# teams23 = Teams(data23)
# data24 = DataLoader(year=2024)
# teams24 = Teams(data24)
# for idx, row in betting_table.iterrows():
#     tm = row.id[8:12]
#     if row.season == 2023:
#         matchups = teams23._fetch_matchups()
#         tm_matchup = [m for m in matchups if (TEAM_IDS[teams23.teamid_to_primowner[m['team1']]]['name']['display'] == tm or TEAM_IDS[teams23.teamid_to_primowner[m['team2']]]['name']['display'] == tm) and m['week'] == row.week][0]
#         betting_table.loc[idx, 'matchup_id'] = int((len(teams23.team_ids) / 2) - ((row.week * len(teams23.team_ids) / 2) - tm_matchup['matchup_id']))
#     if row.season == 2024:
#         matchups = teams24._fetch_matchups()
#         tm_matchup = [m for m in matchups if (TEAM_IDS[teams24.teamid_to_primowner[m['team1']]]['name']['display'] == tm or TEAM_IDS[teams24.teamid_to_primowner[m['team2']]]['name']['display'] == tm) and m['week'] == row.week][0]
#         betting_table.loc[idx, 'matchup_id'] = int((len(teams24.team_ids) / 2) - ((row.week * len(teams24.team_ids) / 2) - tm_matchup['matchup_id']))
#
# betting_table = betting_table.sort_values(['season', 'week', 'matchup_id', 'p_win'])
# betting_table.to_csv(r'tables/betting_table.csv', index=False)






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

@app.route("/simulations/")
def sims():
    headings_bets = tuple(['ID', 'Team', 'Points', 'Matchup', 'THW', 'Highest', 'Lowest'])
    data_bets = ut.flask_get_data(betting_table[['matchup_id', 'team', 'avg_score', 'p_win', 'p_tophalf', 'p_highest', 'p_lowest']])
    return render_template(
        "simulations.html",
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
