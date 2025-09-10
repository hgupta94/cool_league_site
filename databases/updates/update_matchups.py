from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params
from scripts.api.Teams import Teams
from scripts.utils.database import Database
from scripts.home.standings import Standings
from scripts.utils import constants


data = DataLoader(year=constants.SEASON)
teams = Teams(data=data)
params = Params(data=data)
week = params.as_of_week

standings = Standings(season=constants.SEASON, week=week)
matchups_table = 'matchups'
matchup_cols = constants.MATCHUP_COLUMNS
for t in teams.team_ids:
    matchups = standings.get_matchup_results(week=week, team_id=t)
    m_vals = tuple(matchups.values())
    db = Database(data=matchups, table=matchups_table, columns=matchup_cols, values=m_vals)
    db.commit_row()
