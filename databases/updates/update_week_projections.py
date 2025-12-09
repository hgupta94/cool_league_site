from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params
from scripts.simulations.simulations import get_week_projections
from scripts.utils.database import Database
from scripts.utils import constants

import pandas as pd
import mysql.connector.errors

import re
from datetime import datetime as dt

wk_proj_table = 'player_projections'
wk_proj_cols = constants.PROJECTIONS_COLUMNS
data = DataLoader(year=constants.SEASON)
params = Params(data=data)
week = params.current_week

data = get_week_projections(week=week)
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
if day == 'Wed':
    players = data.load_week(week=1)['players']
    for player in players:
        # if player['id'] == 3120348:break
        print(player['player']['fullName'])
        actual = 0
        # name = re.sub(r'[^a-zA-Z]', '', player['player']['fullName'])
        # db_id = f'{name}_{constants.SEASON}_{week-1:02d}'
        for stat in player['player']['stats']:
            if stat['seasonId'] == 2025 and stat['scoringPeriodId'] == week-1 and stat['statSourceId'] == 0:
                actual = stat['appliedTotal']
        db = Database(table=wk_proj_table)
        db.sql_update_table(set_column='actual', new_value=actual, id_column='espn_id', id_value=player['id'], season=constants.SEASON, week=week-1)
