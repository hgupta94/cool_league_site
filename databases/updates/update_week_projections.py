from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params
from scripts.simulations.week_sim import get_week_projections
from scripts.utils.database import Database
from scripts.utils import constants

import pandas as pd


data = DataLoader(year=constants.SEASON)
params = Params(data=data)
week = params.current_week

data = get_week_projections(week=week)
data = data[['id', 'season', 'week', 'player', 'espn_id', 'position', 'rec', 'fpts']]
data.columns = ['id', 'season', 'week', 'name', 'espn_id', 'position', 'receptions', 'projection']
wk_proj_table = 'player_projections'
wk_proj_cols = constants.PROJECTIONS_COLUMNS
for idx, row in data.iterrows():
    vals = (row.id, row.season, row.week, row['name'],
            row.espn_id, row.position, row.receptions, row.projection)
    db = Database(data=data, table=wk_proj_table, columns=wk_proj_cols, values=vals)
    db.sql_insert_query()
    db.commit_row()
