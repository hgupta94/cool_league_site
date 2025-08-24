from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params
from scripts.utils.database import Database
from scripts.api.Teams import Teams
from scripts.scenarios.scenarios import get_h2h
from scripts.utils import constants

week = constants.WEEK

h2h_table = 'h2h'
h2h_cols = constants.H2H_COLUMNS
data = DataLoader(year=constants.SEASON)
params = Params(data)
teams = Teams(data)
h2h = get_h2h(teams=teams, season=constants.SEASON, week=week)
for idx, row in h2h.iterrows():
    h2h_vals = (row.id, row.season, row.week, row.team, row.opp, row.result)
    db = Database(data=h2h, table=h2h_table, columns=h2h_cols, values=h2h_vals)
    db.commit_row()
