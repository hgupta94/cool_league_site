from scripts.api.dataloader import DataLoader
from scripts.api.fantasy_pros import FantasyPros
from scripts.api.settings import TeamSettings
from scripts.utils.database import Database
from scripts.utils import constants
from scripts.utils import utils
from scripts.simulations.simulations import Simulation

from datetime import datetime as dt
import time
# import json
#
#
# with open(r'/Users/hirshgupta/PycharmProjects/cool_league_site/tables/fp_espn_lookup.json', 'r') as f:
#     mapping = json.load(f)


# TODO only run simulation if a roster move was made
# load parameters
day = constants._TODAY.strftime('%a')
N_SIMS = 100_000

dataloader = DataLoader(year=constants.SEASON, week=constants.WEEK)
fp = FantasyPros(dataloader=dataloader)#, mapping=mapping)
teams = TeamSettings(dataloader)
start = time.perf_counter()
sim_results = Simulation(dataloader, fpros=fp).simulate_week(n=N_SIMS)
end = time.perf_counter()
print((end-start) / 60)


rows = []
for team in teams.team_ids:
    db_id = f'{constants.SEASON}_{constants.WEEK:02}_{team:02}'
    if day in ['Thu', 'Sun']:  # save out on gameday. TODO check if game is being played today (ie saturday/christmas/weird schedule)
        db_id += f'_{day}'
    matchup_id = utils.get_matchup_id(teams=teams, week=constants.WEEK, team_id=team)
    if matchup_id is None:  # byes?
        matchup_id = 99
    avg_score = sim_results['scores'][team] / N_SIMS
    p_win = sim_results['n_wins'][team] / N_SIMS
    p_tophalf = sim_results['n_tophalf'][team] / N_SIMS
    p_highest = sim_results['n_highest'][team] / N_SIMS
    p_lowest = sim_results['n_lowest'][team] / N_SIMS
    rows.append((db_id, constants.SEASON, constants.WEEK, matchup_id, team, avg_score, p_win, p_tophalf, p_highest, p_lowest))


Database().batch_insert(
    table='betting_table',
    columns=constants.WEEK_SIM_COLUMNS,
    rows=rows,
    upsert=True,
    update_columns=['avg_score', 'p_win', 'p_tophalf', 'p_highest', 'p_lowest']
)
