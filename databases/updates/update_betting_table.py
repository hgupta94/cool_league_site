from scripts.api.dataloader import DataLoader
from scripts.api.fantasy_pros import FantasyPros
from scripts.api.settings import TeamSettings
from scripts.utils.database import Database
from scripts.utils import constants
from scripts.utils import utils
from scripts.simulations.simulations import Simulation

import time
# import json
#
#
# with open(r'/Users/hirshgupta/PycharmProjects/cool_league_site/tables/fp_espn_lookup.json', 'r') as f:
#     mapping = json.load(f)


def load_betting_table(dataloader:DataLoader, fpros: FantasyPros, n_sims: int=100_000):
    day = constants._TODAY.strftime('%a')

    # load parameters
    teams = TeamSettings(dataloader)
    start = time.perf_counter()
    sim_results = Simulation(dataloader, fpros=fpros).simulate_week(n_sims=n_sims)
    end = time.perf_counter()
    print((end-start) / 60)

    rows = []
    bye_id = 0
    for team in teams.team_ids:
        db_id = f'{constants.SEASON}_{constants.WEEK:02}_{team:02}_{day}'  # save out every day
        matchup_id = utils.get_matchup_id(teams=teams, week=constants.WEEK, team_id=team)
        if not matchup_id:  # byes?
            bye_id -= 1
            matchup_id = bye_id
        avg_score = sim_results['scores'][team] / n_sims
        p_win = sim_results['n_wins'][team] / n_sims
        p_tophalf = sim_results['n_tophalf'][team] / n_sims
        p_highest = sim_results['n_highest'][team] / n_sims
        p_lowest = sim_results['n_lowest'][team] / n_sims
        rows.append((db_id, constants.SEASON, constants.WEEK, matchup_id, team, avg_score, p_win, p_tophalf, p_highest, p_lowest))


    Database().batch_insert(
        table='betting_table',
        columns=constants.WEEK_SIM_COLUMNS,
        rows=rows,
        upsert=True,
        update_columns=['avg_score', 'p_win', 'p_tophalf', 'p_highest', 'p_lowest']
    )

if __name__ == '__main__':
    dataloader = DataLoader(year=constants.SEASON, week=constants.WEEK)
    fp = FantasyPros(dataloader=dataloader)
    load_betting_table(dataloader=dataloader, fpros=fp)
