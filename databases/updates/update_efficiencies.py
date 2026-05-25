from scripts.efficiency.efficiencies import get_optimal_points
from scripts.api.dataloader import DataLoader
from scripts.api.settings import LeagueSettings, RosterSettings, TeamSettings
from scripts.utils.database import Database
from scripts.utils import constants


data = DataLoader(year=constants.SEASON)
rosters = RosterSettings(year=constants.SEASON)
params = LeagueSettings(data)
week = params.as_of_week
teams = TeamSettings(data=data)
week_data = data.load_week(week=week)

eff = get_optimal_points(params=params, teams=teams, rosters=rosters, week_data=week_data, season=constants.SEASON, week=week)

Database().batch_insert(
    table='efficiency',
    columns=constants.EFFICIENCY_COLUMNS,
    rows=[tuple(row) for _, row in eff.iterrows()]
)
