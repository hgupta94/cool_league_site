from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params
from scripts.utils.database import Database
from scripts.api.Teams import Teams
from scripts.scenarios.scenarios import schedule_switcher
from scripts.utils import constants

week = constants.WEEK

sch_sw_table = 'switcher'
sch_sw_cols = constants.SCHEDULE_SWITCH_COLUMNS
data = DataLoader(year=constants.SEASON)
params = Params(data)
teams = Teams(data)

switcher = schedule_switcher(teams=teams, season=constants.SEASON, week=week)
for idx, row in switcher.iterrows():
    ss_vals = (row.id, row.season, row.week, row.team, row.schedule_of, row.result)
    db = Database(data=switcher, table=sch_sw_table, columns=sch_sw_cols, values=ss_vals)
    db.commit_row()
