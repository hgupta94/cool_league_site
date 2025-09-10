from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params
from scripts.api.Teams import Teams
from scripts.api.Rosters import Rosters
from scripts.utils.database import Database
from scripts.utils import constants
from scripts.simulations import simulations
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

import pandas as pd

import time


n_sims = 1000

data = DataLoader()
params = Params(data)
teams = Teams(data)
rosters = Rosters()
players_data = data.players_info()
replacement_players = simulations.get_replacement_players(data)

team_names = []
for team in teams.team_ids:
    team_names.append(constants.TEAM_IDS[teams.teamid_to_primowner[team]]['name']['display'])

lineups = simulations.get_ros_projections(data=data, params=params, teams=teams, rosters=rosters, replacement_players=replacement_players)
results = Database(table='matchups', season=constants.SEASON, week=params.as_of_week).retrieve_data(how='season')
results = results[['team', 'score', 'matchup_result', 'tophalf_result']].groupby('team').sum()
results.columns = ['total_points', 'matchup_wins', 'tophalf_wins']

start = time.perf_counter()
all_sim_results = []
for sim in range(n_sims):
    if sim % 10 == 0: print(sim)
    sim_results = {  # initialize sim counter
        o: {
            'matchup_wins': 0,
            'tophalf_wins': 0,
            'total_wins': 0,
            'total_points': 0,
            'playoffs': 0,
            'finals': 0,
            'champion': 0
        }
        for o in team_names
    }
    # get actual season results
    if len(results) > 0:
        for team, row in results.iterrows():
            sim_results[team]['matchup_wins'] += row.matchup_wins
            sim_results[team]['tophalf_wins'] += row.tophalf_wins
            sim_results[team]['total_wins'] += row.matchup_wins + row.tophalf_wins
            sim_results[team]['total_points'] += row.total_points

    sim_data = simulations.simulate_season(params=params, teams=teams, lineups=lineups, team_names=team_names)
    playoff_teams = simulations.get_playoff_teams(params=params, sim_data=sim_data)

    sf_teams = simulations.sim_playoff_round(week=15, lineups=lineups, n_bye=2, round_teams=playoff_teams)
    finals_teams = simulations.sim_playoff_round(week=16, lineups=lineups, round_teams=sf_teams)
    champion = simulations.sim_playoff_round(week=17, lineups=lineups, round_teams=finals_teams)

    ## update sim stats
    for team in team_names:
        # regular season
        sim_results[team]['matchup_wins'] += sim_data[team]['matchup_wins']
        sim_results[team]['tophalf_wins'] += sim_data[team]['tophalf_wins']
        sim_results[team]['total_wins'] += sim_data[team]['total_wins']
        sim_results[team]['total_points'] += sim_data[team]['total_points']

        # playoffs
        if team in playoff_teams:
            sim_results[team]['playoffs'] += 1

        if team in finals_teams:
            sim_results[team]['finals'] += 1

        if team in champion:
            sim_results[team]['champion'] += 1

    all_sim_results.append(sim_results)
end = time.perf_counter()
print(end-start, 'seconds')

# Flatten all_sim_results into a DataFrame
flattened_results = []
for sim_index, sim_result in enumerate(all_sim_results):
    for team, stats in sim_result.items():
        stats['team'] = team
        stats['simulation'] = sim_index
        flattened_results.append(stats)

# Convert to a DataFrame
all_sim_results_df = pd.DataFrame(flattened_results)
columns_order = ['simulation', 'team', 'matchup_wins', 'tophalf_wins', 'total_wins', 'total_points', 'playoffs', 'finals', 'champion']
all_sim_results_df = all_sim_results_df[columns_order]

rows = []
for team in team_names:
    temp = all_sim_results_df[all_sim_results_df.team == team]
    for wins in range(0, (2*params.regular_season_end)+1):
        prob = len(temp[temp.total_wins == wins]) / n_sims
        if prob > 0:
            rows.append([team, wins, prob])
wins_prob_df = pd.DataFrame(rows, columns=['team', 'wins', 'p'])
wins_prob_df['season'] = constants.SEASON
wins_prob_df['week'] = params.current_week
wins_prob_df['id'] = wins_prob_df.season.astype(str) + '_' + wins_prob_df.week.astype(str).str.zfill(2) + '_' + wins_prob_df.wins.astype(str).str.zfill(2) + '_' + wins_prob_df.team
sim_wins_table = 'season_sim_wins'
sim_wins_cols = 'id, season, week, team, wins, p'
for idx, row in wins_prob_df.iterrows():
    sim_vals = (row.id, row.season, row.week, row.team, row.wins, row.p)
    db = Database(data=wins_prob_df, table=sim_wins_table, columns=sim_wins_cols, values=sim_vals)
    db.commit_row()


team_totals = {  # initialize sim counter
        o: {
            'matchup_wins': 0,
            'tophalf_wins': 0,
            'total_wins': 0,
            'total_points': 0,
            'playoffs': 0,
            'finals': 0,
            'champion': 0
        }
        for o in team_names
    }
for team in team_names:
    for a in all_sim_results:
        team_sim = {k: v for k, v in a.items() if k == team}
        team_totals[team]['matchup_wins'] += team_sim[team]['matchup_wins']
        team_totals[team]['tophalf_wins'] += team_sim[team]['tophalf_wins']
        team_totals[team]['total_wins'] += team_sim[team]['total_wins']
        team_totals[team]['total_points'] += team_sim[team]['total_points']
        team_totals[team]['playoffs'] += team_sim[team]['playoffs']
        team_totals[team]['finals'] += team_sim[team]['finals']
        team_totals[team]['champion'] += team_sim[team]['champion']


sim_df = pd.DataFrame(team_totals).transpose() / n_sims
sim_df = sim_df.reset_index().rename(columns={'index': 'team'})
sim_df['season'] = constants.SEASON
sim_df['week'] = params.current_week
sim_df['id'] = sim_df.season.astype(str) + '_' + sim_df.week.astype(str).str.zfill(2) + '_' + sim_df.team

season_sim_table = 'season_sim'
season_sim_cols = constants.SEASON_SIM_COLUMNS
for idx, row in sim_df.iterrows():
    sim_vals = (row.id, row.season, row.week, row.team, row.matchup_wins, row.tophalf_wins,
                row.total_wins, row.total_points, row.playoffs, row.finals, row.champion)
    db = Database(data=sim_df, table=season_sim_table, columns=season_sim_cols, values=sim_vals)
    db.commit_row()
