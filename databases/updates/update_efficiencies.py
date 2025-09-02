from scripts.efficiency.efficiencies import get_optimal_points
from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params
from scripts.api.Teams import Teams
from scripts.api.Rosters import Rosters
from scripts.utils.database import Database
from scripts.utils import constants


data = DataLoader(year=constants.SEASON)
rosters = Rosters(year=constants.SEASON)
params = Params(data)
week = params.as_of_week
teams = Teams(data=data)

week_data = data.load_week(week=week)
eff = get_optimal_points(params=params, teams=teams, rosters=rosters, week_data=week_data, season=constants.SEASON, week=week)
eff_table = 'efficiency'
eff_cols = constants.EFFICIENCY_COLUMNS
for idx, row in eff.iterrows():
    vals = (row.id, row.season, row.week, row.team,
            row.actual_score, row.actual_projected,
            row.best_projected_actual, row.best_projected_proj,
            row.best_lineup_actual, row.best_lineup_proj)
    db = Database(data=eff, table=eff_table, columns=eff_cols, values=vals)
    db.sql_insert_query()
    db.commit_row()
