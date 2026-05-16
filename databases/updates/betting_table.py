from scripts.api.dataloader import DataLoader
from scripts.api.settings import LeagueSettings, RosterSettings, TeamSettings
from scripts.utils.database import Database
from scripts.utils import constants
from scripts.simulations import simulations

import mysql.connector.errors
from datetime import datetime as dt
import time


# TODO only run simulation if a roster move was made
# load parameters
week_sim_table = 'betting_table'
week_sim_cols = constants.WEEK_SIM_COLUMNS
day = dt.now().strftime('%a')
n_sims = 1

data = DataLoader(year=constants.SEASON)
rosters = RosterSettings(year=constants.SEASON)
params = LeagueSettings(data)
teams = TeamSettings(data=data)
week = params.current_week

week_data = data.load_week(week=week)
matchups = [m for m in teams.matchups if m['week'] == week]
projections_df = simulations.get_week_projections(week=params.current_week)
projections_df.columns = ['name', 'projection', 'position', 'receptions', 'team', 'season', 'week', 'match_on', 'id', 'espn_id']
projections_dict = projections_df.to_dict(orient='records')
replacement_players = simulations.get_replacement_players(data)

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
    week_sim_vals = (db_id, constants.SEASON, week, matchup_id, team, avg_score, p_win, p_tophalf, p_highest, p_lowest)
    print(week_sim_vals)
    try:
        db = Database(table=week_sim_table, columns=week_sim_cols, values=week_sim_vals)
        db.sql_insert_query()
        db.commit_row()
    except mysql.connector.errors.IntegrityError:
        db = Database(table=week_sim_table)
        db.sql_update_table(set_column='avg_score', new_value=avg_score, id_column='id', id_value=db_id, season=constants.SEASON, week=week)
        db.sql_update_table(set_column='p_win', new_value=p_win, id_column='id', id_value=db_id, season=constants.SEASON, week=week)
        db.sql_update_table(set_column='p_tophalf', new_value=p_tophalf, id_column='id', id_value=db_id, season=constants.SEASON, week=week)
        db.sql_update_table(set_column='p_highest', new_value=p_highest, id_column='id', id_value=db_id, season=constants.SEASON, week=week)
        db.sql_update_table(set_column='p_lowest', new_value=p_lowest, id_column='id', id_value=db_id, season=constants.SEASON, week=week)
print(f'Commited week {week} in {round((end-start)/60, 2)} minutes', end='\n')
