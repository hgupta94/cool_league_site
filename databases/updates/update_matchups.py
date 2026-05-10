from scripts.api.dataloader import DataLoader
from scripts.api.settings import LeagueSettings, TeamSettings
from scripts.utils.database import Database
from scripts.home.standings import Standings
from scripts.utils import constants


data = DataLoader(year=constants.SEASON)
params = LeagueSettings(data=data)
teams = TeamSettings(data=data)
# week = params.as_of_week
# print(week)
week=15
standings = Standings(season=constants.SEASON, week=week)
matchups_table = 'matchups'
matchup_cols = constants.MATCHUP_COLUMNS
for t in teams.team_ids:
    matchups = standings.get_matchup_results(week=week, team_id=t)
    m_vals = tuple(matchups.values())
    print(m_vals)
    # db = Database(data=matchups, table=matchups_table, columns=matchup_cols, values=m_vals)
    # db.commit_row()
