from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params
from scripts.api.Rosters import Rosters
from scripts.api.Teams import Teams
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
n_sims = 10

if day in ['Sun', 'Mon', 'Wed', 'Thu', 'Fri', 'Sat']:
    data = DataLoader(year=constants.SEASON)
    rosters = Rosters(year=constants.SEASON)
    params = Params(data)
    teams = Teams(data=data)
    week = params.current_week

    week_data = data.load_week(week=week)
    matchups = [m for m in teams.matchups['schedule'] if m['matchupPeriodId'] == week]
    projections_df = simulations.get_week_projections(week=params.current_week)
    projections_df.columns = ['name', 'projection', 'position', 'receptions', 'team', 'season', 'week', 'match_on', 'id', 'espn_id']
    projections_dict = projections_df.to_dict(orient='records')

    start = time.perf_counter()
    sim_scores, sim_wins, sim_tophalf, sim_highest, sim_lowest = simulations.simulate_week(week_data=week_data,
                                                                                          teams=teams,
                                                                                          rosters=rosters,
                                                                                          matchups=matchups,
                                                                                          projections=projections_dict,
                                                                                          week=week,
                                                                                          n_sims=n_sims)
    end = time.perf_counter()

    for team in teams.team_ids:
        display_name = constants.TEAM_IDS[teams.teamid_to_primowner[team]]['name']['display']
        db_id = f'{constants.SEASON}_{week:02d}_{display_name}'
        matchup_id = simulations.get_matchup_id(teams=teams, week=week, display_name=display_name)
        avg_score = sim_scores[team] / n_sims
        p_win = sim_wins[team] / n_sims
        p_tophalf = sim_tophalf[team] / n_sims
        p_highest = sim_highest[team] / n_sims
        p_lowest = sim_lowest[team] / n_sims
        week_sim_vals = (db_id, constants.SEASON, week, matchup_id, display_name, avg_score, p_win, p_tophalf, p_highest, p_lowest)
        # print(week_sim_vals)
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
