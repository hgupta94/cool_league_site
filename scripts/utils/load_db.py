import mysql.connector.errors

from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params
from scripts.api.Teams import Teams
from scripts.api.Rosters import Rosters
from scripts.utils.database import Database
from scripts.utils import constants


##### MATCHUPS
from scripts.home.standings import Standings
matchups_table = 'matchups'
matchup_cols = constants.MATCHUP_COLUMNS
for s in range(2018, 2024):
    data = DataLoader(year=s)
    teams = Teams(data=data)
    params = Params(data=data)
    for w in range(1, params.regular_season_end+1):
        standings = Standings(season=s, week=w)
        print(s, w)
        for t in teams.team_ids:
            matchups = standings.get_matchup_results(week=w, team_id=t)
            m_vals = tuple(matchups.values())
            db = Database(data=matchups, table=matchups_table, columns=matchup_cols, values=m_vals)
            db.commit_row()


##### POWER RANKS
from scripts.home.power_ranks import power_rank
import pandas as pd

pr_table = 'power_ranks'
pr_cols = constants.POWER_RANK_COLUMNS
for s in range(2023, 2024):
    data = DataLoader(year=s)
    params = Params(data=data)
    df_final = pd.DataFrame()
    for wk in range(1, params.regular_season_end+1):
        df = pd.DataFrame(power_rank(s, wk)).transpose()
        df['season'] = s
        df['week'] = wk
        df = df.reset_index().rename(columns={'index': 'team'})
        df['id'] = df['season'].astype(str) + '_' + df['week'].astype(str) + '_' + df['team']
        df['power_rank'] = df.power_score_norm.rank(ascending=False)
        df_final = pd.concat([df_final, df])
    df_final['score_raw_change'] = df_final.groupby(['team'])['power_score_raw'].diff()
    df_final['score_norm_change'] = df_final.groupby(['team'])['power_score_norm'].diff()
    df_final['rank_change'] = df_final.groupby(['team'])['power_rank'].diff()
    df_final = df_final[pr_cols.split(', ')].fillna(0)
    for _, row in df_final.iterrows():
        pr_vals = tuple(row)
        db = Database(data=df_final, table=pr_table, columns=pr_cols, values=pr_vals)
        db.commit_row()



##### SCENARIOS
import mysql
from scripts.api.Teams import Teams
from scripts.scenarios.scenarios import get_h2h, schedule_switcher
h2h_table = 'h2h'
h2h_cols = constants.H2H_COLUMNS
sch_sw_table = 'switcher'
sch_sw_cols = constants.SCHEDULE_SWITCH_COLUMNS
for s in range(2018, 2024):
    data = DataLoader(year=s)
    params = Params(data)
    teams = Teams(data)
    for w in range(1, params.regular_season_end+1):
        print(s, w)
        h2h = get_h2h(teams=teams, season=s, week=w)
        for idx, row in h2h.iterrows():
            h2h_vals = (row.id, row.season, row.week, row.team, row.opp, row.result)
            db = Database(data=h2h, table=h2h_table, columns=h2h_cols, values=h2h_vals)
            db.commit_row()

        switcher = schedule_switcher(teams=teams, season=s, week=w)
        for idx, row in switcher.iterrows():
            try:
                ss_vals = (row.id, row.season, row.week, row.team, row.schedule_of, row.result)
                db = Database(data=switcher, table=sch_sw_table, columns=sch_sw_cols, values=ss_vals)
                db.commit_row()
            except mysql.connector.errors.IntegrityError:
                continue


##### Efficiency
from scripts.efficiency.efficiencies import get_optimal_points, plot_efficiency

eff_table = 'efficiency'
eff_cols = constants.EFFICIENCY_COLUMNS
for s in range(2018, 2024):
    data = DataLoader(year=s)
    rosters = Rosters(year=s)
    params = Params(data)
    teams = Teams(data=data)
    for w in range(1, params.regular_season_end+1):
        print(s, w)
        week_data = data.load_week(week=w)
        eff = get_optimal_points(params=params, teams=teams, rosters=rosters, week_data=week_data, season=s, week=w)
        for idx, row in eff.iterrows():
            vals = (row.id, row.season, row.week, row.team,
                    row.actual_score, row.actual_projected,
                    row.best_projected_actual, row.best_projected_proj,
                    row.best_lineup_actual, row.best_lineup_proj)
            db = Database(data=eff, table=eff_table, columns=eff_cols, values=vals)
            db.sql_insert_query()
            db.commit_row()

plot = plot_efficiency(database=Database(), season=2023, week=10)


##### Projections
from scripts.api.Rosters import Rosters
from scripts.api.Teams import Teams
from scripts.simulations import week_sim as ws
from datetime import datetime as dt
import time
proj_table = 'player_projections'
proj_cols = constants.PROJECTIONS_COLUMNS
for w in range(3, 19):
    print(w)
    projections = ws.get_week_projections(w)
    for idx, row in projections.iterrows():
        vals = (row.id, row.season, row.week, row.player, row.espn_id, row.position, row.rec, row.fpts)
        db = Database(data=projections, table=proj_table, columns=proj_cols, values=vals)
        db.commit_row()

##### Week sim
# TODO only run simulation if a roster move was made
# load parameters
from datetime import datetime as dt
season = 2022
week_sim_table = 'betting_table'
week_sim_cols = constants.WEEK_SIM_COLUMNS
# day = dt.now().strftime('%a')
day = 'Sun'
n_sims = constants.N_SIMS

for week in range(3,15):
    print(f'Simulating week {week}', end='...')
    try:
        data = DataLoader(year=season)
        rosters = Rosters(year=season)
        teams = Teams(data=data)
        week_data = data.load_week(week=week)
        matchups = [m for m in teams.matchups['schedule'] if m['matchupPeriodId'] == week]
        projections = ws.get_week_projections(week)
        projections = projections.to_dict(orient='records')

        start = time.perf_counter()
        sim_scores, sim_wins, sim_tophalf, sim_highest, sim_lowest = ws.simulate_week(week_data=week_data,
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
            matchup_id = ws.get_matchup_id(teams=teams, week=week, display_name=display_name)
            avg_score = sim_scores[team] / n_sims
            p_win = sim_wins[team] / n_sims
            p_tophalf = sim_tophalf[team] / n_sims
            p_highest = sim_highest[team] / n_sims
            p_lowest = sim_lowest[team] / n_sims
            week_sim_vals = (db_id, season, week, matchup_id, display_name, avg_score, p_win, p_tophalf, p_highest, p_lowest)
            print(week_sim_vals)
            db = Database(table=week_sim_table, columns=week_sim_cols, values=week_sim_vals)
            db.sql_insert_query()
            db.commit_row()
        print(f'Commited week {week} in {round((end-start)/60, 2)} minutes', end='\n')
    except Exception as e:
        print(f'Could not commit week {week}: {e}', end='\n')
        continue


##### Records
from scripts.records.initialize import *
season=constants.SEASON+1
standings_recs = get_standings_records(season)
matchups_recs = get_matchup_records(season)
per_stat_recs = get_per_stat_records(season)
stat_group_records = get_stat_group_records(season)
points_by_position = get_most_points_by_position(season)
records = pd.concat([standings_recs, matchups_recs, per_stat_recs, stat_group_records, points_by_position])
records = records.reset_index(drop=True).reset_index().rename(columns={'index': 'id'})

records_table = 'records'
records_cols = constants.RECORDS_COLUMNS
for idx, row in records.iterrows():
    db = Database(table=records_table, columns=records_cols, values=tuple(row))
    db.sql_insert_query()
    db.commit_row()
