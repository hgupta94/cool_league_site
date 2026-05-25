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

Database().batch_insert(
    table='schedule_switcher',
    columns=constants.SCHEDULE_SWITCH_COLUMNS,
    rows=[tuple(row) for _, row in switcher.iterrows()]
)
