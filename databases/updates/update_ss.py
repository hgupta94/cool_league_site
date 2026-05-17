from scripts.api.dataloader import DataLoader
from scripts.api.settings import LeagueSettings, TeamSettings
from scripts.utils.database import Database
from scripts.scenarios.scenarios import schedule_switcher
from scripts.utils import constants


data = DataLoader(year=constants.SEASON)
params = LeagueSettings(data)
week = params.as_of_week
teams = TeamSettings(data)

switcher = schedule_switcher(teams=teams, season=constants.SEASON, week=week)
sch_sw_table = 'schedule_switcher'
sch_sw_cols = constants.SCHEDULE_SWITCH_COLUMNS
for idx, row in switcher.iterrows():
    ss_vals = (row.id, row.season, row.week, row.team, row.schedule_of, row.result)
    db = Database(data=switcher, table=sch_sw_table, columns=sch_sw_cols, values=ss_vals)
    db.commit_row()
print(f'Commited week {week}')
