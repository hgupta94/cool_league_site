from scripts.api.dataloader import DataLoader
from scripts.api.settings import LeagueSettings, TeamSettings
from scripts.utils.database import Database
from scripts.home.standings import Standings
from scripts.utils import constants


data = DataLoader(year=constants.SEASON)
params = LeagueSettings(data=data)
teams = TeamSettings(data=data)
week = params.as_of_week
standings = Standings(season=constants.SEASON, week=week)

rows = []
for t in teams.team_ids:
    matchups = standings.get_matchup_results(week=week, team_id=t)
    rows.append(tuple(matchups.values()))

Database().batch_insert(
    table='matchups',
    columns=constants.MATCHUP_COLUMNS,
    rows=rows
)
