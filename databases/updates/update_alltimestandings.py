from scripts.records.initialize import *
from scripts.utils.database import Database
from scripts.utils import constants


season=constants.SEASON+1
standings = get_all_time_standings(season)
rows = list(standings.itertuples(index=False, name=None))

Database().batch_insert(
    table='alltime_standings',
    columns=constants.ALLTIME_STANDINGS_COLUMNS,
    rows=rows,
    upsert=False,
    update_columns=None
)
