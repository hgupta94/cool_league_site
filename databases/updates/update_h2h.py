from scripts.api.dataloader import DataLoader
from scripts.api.settings import LeagueSettings, TeamSettings
from scripts.utils.database import Database
from scripts.scenarios.scenarios import get_h2h
from scripts.utils import constants


data = DataLoader(year=constants.SEASON)
params = LeagueSettings(data)
week = params.as_of_week
teams = TeamSettings(data)

h2h = get_h2h(teams=teams, season=constants.SEASON, week=week)

Database().batch_insert(
    table='h2h',
    columns=constants.H2H_COLUMNS,
    rows=[tuple(row) for _, row in h2h.iterrows()]
)
