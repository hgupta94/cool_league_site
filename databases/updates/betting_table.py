from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params
from scripts.api.Rosters import Rosters
from scripts.api.Teams import Teams
from scripts.utils.database import Database
from scripts.utils import constants
from scripts.simulations import simulations

import pandas as pd
from datetime import datetime as dt
import time


# TODO only run simulation if a roster move was made
# load parameters
week_sim_table = 'betting_table'
week_sim_cols = constants.WEEK_SIM_COLUMNS
day = dt.now().strftime('%a')
betting_timestamp = f'Updated: {dt.now().strftime("%A, %b %d %Y")}'
n_sims = 10

data = DataLoader(year=constants.SEASON)
params = Params(data)
rosters = Rosters(year=constants.SEASON)
teams = Teams(data=data)
week = params.current_week
week_data = data.load_week(week=week)
matchups = [m for m in teams.matchups['schedule'] if m['matchupPeriodId'] == week]
projections = simulations.query_projections_db(season=constants.SEASON, week=week)
projections = projections.to_dict(orient='records')

start = time.perf_counter()
sim_scores, sim_wins, sim_tophalf, sim_highest, sim_lowest = simulations.simulate_week(week_data=week_data,
                                                                                       teams=teams,
                                                                                       rosters=rosters,
                                                                                       matchups=matchups,
                                                                                       projections=projections,
                                                                                       week=week,
                                                                                       n_sims=n_sims)
end = time.perf_counter()

for team in teams.team_ids:
    display_name = constants.TEAM_IDS[teams.teamid_to_primowner[team]]['name']['display']
    db_id = f'{constants.SEASON}_{str(week).zfill(2)}_{display_name}_{day}'
    matchup_id = simulations.get_matchup_id(teams=teams, week=week, display_name=display_name)
    avg_score = sim_scores[team] / n_sims
    p_win = sim_wins[team] / n_sims
    p_tophalf = sim_tophalf[team] / n_sims
    p_highest = sim_highest[team] / n_sims
    p_lowest = sim_lowest[team] / n_sims
    week_sim_vals = (db_id, constants.SEASON, week, matchup_id, display_name, avg_score, p_win, p_tophalf, p_highest, p_lowest)
    db = Database(table=week_sim_table, columns=week_sim_cols, values=week_sim_vals)
    db.sql_insert_query()
    db.commit_row()
print(f'Commited week {week} in {round((end-start)/60, 2)} minutes', end='\n')
