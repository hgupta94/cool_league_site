from scripts.api.dataloader import DataLoader
from scripts.api.settings import LeagueSettings, RosterSettings, TeamSettings
from scripts.utils.database import Database
from scripts.utils import constants
from scripts.simulations import simulations

import mysql.connector.errors
from datetime import datetime as dt
import time
import pandas as pd

# TODO only run simulation if a roster move was made
# load parameters
day = dt.now().strftime('%a')
n_sims = 50000

data = DataLoader(year=constants.SEASON)
rosters = RosterSettings(year=constants.SEASON)
params = LeagueSettings(data)
teams = TeamSettings(data=data)
week = params.current_week
replacement_players = rosters.replacement_players

week_data = data.load_week(week=week)
matchups = [m for m in teams.matchups if m['week'] == week]
try:
    projections_df = simulations.get_week_projections(week=params.current_week)
    projections_df.columns = ['name', 'projection', 'position', 'receptions', 'team', 'season', 'week', 'match_on', 'id', 'espn_id']
except TypeError:
    projections_df = pd.DataFrame(columns=['name', 'projection', 'position', 'receptions', 'team', 'season', 'week', 'match_on', 'id', 'espn_id'])
projections_dict = projections_df.to_dict(orient='records')

start = time.perf_counter()
sim_scores, sim_wins, sim_tophalf, sim_highest, sim_lowest = simulations.simulate_week(week_data=week_data,
                                                                                       teams=teams,
                                                                                       rosters=rosters,
                                                                                       params=params,
                                                                                       replacement_players=replacement_players,
                                                                                       matchups=matchups,
                                                                                       projections=projections_dict,
                                                                                       week=week,
                                                                                       n_sims=n_sims)
end = time.perf_counter()

rows = []
for team in teams.teams:
    db_id = f'{constants.SEASON}_{week:02d}_{team}'
    if day in ['Thu', 'Sun']:  # save out on gameday. TODO check if game is being played today (ie saturday/christmas/weird schedule)
        db_id += f'_{day}'
    matchup_id = simulations.get_matchup_id(teams=teams, week=week, team_id=team)
    if matchup_id is None:  # byes?
        matchup_id = 99
    avg_score = sim_scores[team] / n_sims
    p_win = sim_wins[team] / n_sims
    p_tophalf = sim_tophalf[team] / n_sims
    p_highest = sim_highest[team] / n_sims
    p_lowest = sim_lowest[team] / n_sims
    rows.append((db_id, constants.SEASON, week, matchup_id, team, avg_score, p_win, p_tophalf, p_highest, p_lowest))

try:
    Database().batch_insert(
        table='betting_table',
        columns=constants.WEEK_SIM_COLUMNS,
        rows=rows
    )
except mysql.connector.errors.IntegrityError:
    Database().batch_insert(
        table='betting_table',
        columns=constants.WEEK_SIM_COLUMNS,
        rows=rows,
        upsert=True,
        update_columns=['avg_score', 'p_win', 'p_tophalf', 'p_highest', 'p_lowest']
    )
