from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params

from scripts.utils.database import Database
from scripts.utils import constants
# from scripts.utils.utils import timer


##### MATCHUPS
from scripts.api.Teams import Teams
from scripts.home.standings import get_matchup_results
matchups_table = 'matchups'
matchup_cols = constants.MATCHUP_COLUMNS
for s in range(2018, 2024):
    data = DataLoader(year=s)
    params = Params(data)
    teams = Teams(data)
    for w in range(1, params.regular_season_end+1):
        print(s, w)
        matchups = get_matchup_results(teams=teams, season=s, week=w)
        for row in matchups:
            m_vals = tuple(value for value in row)
            db = Database(data=matchups, table=matchups_table, columns=matchup_cols, values=m_vals)
            db.commit_row()


##### SCENARIOS
from scripts.api.Teams import Teams
from scripts.scenarios.scenarios import get_h2h, schedule_switcher
h2h_table = 'h2h'
h2h_cols = constants.H2H_COLUMNS
sch_sw_table = 'switcher'
sch_sw_cols = constants.SCHEDULE_SWITCH_COLUMNS
for s in range(2018, 2024):
    # s, w = 2023, 10
    data = DataLoader(year=s)
    params = Params(data)
    teams = Teams(data)
    for w in range(1, params.regular_season_end+1):
        print(s, w)
        # h2h = get_h2h(teams=teams, season=s, week=w)
        # for idx, row in h2h.iterrows():
        #     h2h_vals = (row.id, row.season, row.week, row.team, row.opp, row.result)
        #     db = Database(data=h2h, table=h2h_table, columns=h2h_cols, values=h2h_vals)
        #     db.commit_row()

        switcher = schedule_switcher(teams=teams, season=s, week=w)
        for idx, row in switcher.iterrows():
            ss_vals = (row.id, row.season, row.week, row.team, row.schedule_of, row.result)
            db = Database(data=switcher, table=sch_sw_table, columns=sch_sw_cols, values=ss_vals)
            db.commit_row()


##### Efficiency
from scripts.efficiency.efficiencies import get_optimal_points
eff_table = 'efficiency'
eff_cols = constants.EFFICIENCY_COLUMNS
for s in range(2018, 2024):
    data = DataLoader(year=s)
    params = Params(data)
    for w in range(1, params.regular_season_end+1):
        print(s, w)
        week_data = data.load_week(week=w)
        eff = get_optimal_points(data=data, week_data=week_data, season=s, week=w)
        for idx, row in eff.iterrows():
            vals = (row.id, row.season, row.week, row.team,
                    row.actual_score, row.actual_projected,
                    row.best_projected_actual, row.best_projected_proj,
                    row.best_lineup_actual, row.best_lineup_proj)
            db = Database(data=eff, table=eff_table, columns=eff_cols, values=vals)
            db.sql_insert_query()
            db.commit_row()


##### Projections
from scripts.api.Rosters import Rosters
from scripts.api.Teams import Teams
from scripts.simulations import projections as proj
from datetime import datetime as dt
import time
proj_table = 'projections'
proj_cols = constants.PROJECTIONS_COLUMNS
for w in range(1, 19):
    print(w)
    w = 3
    projections = proj.get_week_projections(w)
    for idx, row in projections.iterrows():
        vals = (row.id, row.season, row.week, row.player, row.espn_id, row.position, row.rec, row.fpts)
        db = Database(data=projections, table=proj_table, columns=proj_cols, values=vals)
        db.commit_row()

##### Week sim
# load parameters
season = 2023
week_sim_table = 'betting_table'
week_sim_cols = constants.WEEK_SIM_COLUMNS
day = dt.now().strftime('%a')
n_sims = 100_000

for week in range(9,12):
    print(f'Simulating week {week}', end='...')
    try:
        data = DataLoader(year=season, week=week)
        rosters = Rosters(year=season)
        teams = Teams(data=data)
        week_data = data.load_week()
        matchups = [m for m in teams.matchups['schedule'] if m['matchupPeriodId'] == week]
        projections = proj.get_week_projections(week)
        projections = projections.to_dict(orient='records')

        start = time.perf_counter()
        sim_scores, sim_wins, sim_tophalf, sim_highest, sim_lowest = proj.simulate_week(week_data=week_data,
                                                                                        teams=teams,
                                                                                        rosters=rosters,
                                                                                        matchups=matchups,
                                                                                        projections=projections,
                                                                                        week=week,
                                                                                        n_sims=n_sims)
        end = time.perf_counter()

        for team in teams.team_ids:
            display_name = constants.TEAM_IDS[teams.teamid_to_primowner[team]]['name']['display']
            db_id = f'{season}_{str(week).zfill(2)}_{display_name}_{day}'
            avg_score = sim_scores[team] / n_sims
            p_win = sim_wins[team] / n_sims
            p_tophalf = sim_tophalf[team] / n_sims
            p_highest = sim_highest[team] / n_sims
            p_lowest = sim_lowest[team] / n_sims
            week_sim_vals = (db_id, season, week, display_name, avg_score, p_win, p_tophalf, p_highest, p_lowest)
            db = Database(table=week_sim_table, columns=week_sim_cols, values=week_sim_vals)
            db.sql_insert_query()
            db.commit_row()
        print(f'Commited week {week} in {round((end-start)/60, 2)} minutes', end='\n')
    except Exception as e:
        print(f'Could not commit week {week}: {e}', end='\n')
        continue


# proj.calculate_odds(sim_result=sim_wins, n_sims=n_sims)
# proj.calculate_odds(sim_result=sim_tophalf, n_sims=n_sims)
# proj.calculate_odds(sim_result=sim_highest, n_sims=n_sims)
# proj.calculate_odds(sim_result=sim_lowest, n_sims=n_sims)