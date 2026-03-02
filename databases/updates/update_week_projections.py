from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params
from scripts.simulations.simulations import get_week_projections
from scripts.utils.database import Database
from scripts.utils import constants

import mysql.connector.errors

wk_proj_table = 'player_projections'
wk_proj_cols = constants.PROJECTIONS_COLUMNS
datal = DataLoader(year=constants.SEASON)
params = Params(data=datal)
week = params.current_week
players = DataLoader().players_info()['players']

data = get_week_projections(players=players, week=week)
data = data[['id', 'season', 'week', 'player', 'espn_id', 'position', 'rec', 'fpts']]
data.columns = ['id', 'season', 'week', 'name', 'espn_id', 'position', 'receptions', 'projection']
for idx, row in data.iterrows():
    vals = (row.id, row.season, row.week, row['name'],
            row.espn_id, row.position, row.receptions, row.projection)
    try:
        db = Database(data=data, table=wk_proj_table, columns=wk_proj_cols, values=vals)
        db.sql_insert_query()
        db.commit_row()
    except mysql.connector.errors.IntegrityError:
        db = Database(table=wk_proj_table)
        db.sql_update_table(set_column='projection', new_value=row.projection, id_column='id', id_value=row.id, season=constants.SEASON, week=week)


# get actual scores
# if day == 'Wed':
players = datal.load_week(week=week)['players']
for player in players:
    actual = 0
    for stat in player['player']['stats']:
        if stat['seasonId'] == 2025 and stat['scoringPeriodId'] == week and stat['statSourceId'] == 0:
            actual = stat['appliedTotal']
    db = Database(table=wk_proj_table)
    db.sql_update_table(set_column='actual', new_value=actual, id_column='espn_id', id_value=player['id'], season=constants.SEASON, week=week)
