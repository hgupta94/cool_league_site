from scripts.api.dataloader import DataLoader
from scripts.api.settings import LeagueSettings, RosterSettings, TeamSettings
from scripts.utils.database import Database
from scripts.utils import constants
from scripts.simulations import simulations

import pandas as pd

import time
from datetime import datetime as dt
import warnings
warnings.filterwarnings("ignore", category=UserWarning)


n_sims = 20_000

data = DataLoader()
params = LeagueSettings(data)
teams = TeamSettings(data)
rosters = RosterSettings()
players_data = data.players_info()
team_names = teams.teams
replacement_players = simulations.get_replacement_players(data)
lineups = simulations.get_ros_projections(data=data, params=params, teams=teams, rosters=rosters, replacement_players=replacement_players)

# get actual standings
results = Database(table='matchups', season=constants.SEASON, week=params.as_of_week).retrieve_data(how='season')
results = results[['team', 'score', 'matchup_result', 'tophalf_result']].groupby('team').sum()
results.columns = ['total_points', 'matchup_wins', 'tophalf_wins']

# get current week sim results and combine
week_data = None
playoff_matchups = None
projections_dict = None
if params.current_week > params.regular_season_end:
    # get winners bracket matchups
    week_data = data.load_week(week=params.current_week)
    week_matchups = [m for m in week_data['schedule'] if m['playoffTierType'] == 'WINNERS_BRACKET']
    playoff_matchup_ids = [
        i['id'] for i in
        week_matchups
        if all(name in i.keys() for name in ['home', 'away'])
           and i['matchupPeriodId'] == params.current_week
    ]
    matchups = [m for m in teams.matchups if m['matchup_id'] in playoff_matchup_ids]
    projections_dict = simulations.query_projections_db(season=constants.SEASON, week=params.current_week)

# run simulation
start = time.perf_counter()
all_sim_results = []
for sim in range(n_sims):
    print(f'{sim+1}/{n_sims}', end='\r')
    sim_results = {  # initialize sim counter
        o: {
            'rank': 0,
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

    # add actual season and current week sim results
    sim_data = simulations.simulate_season(params=params, teams=teams, lineups=lineups, team_names=team_names)
    if len(results):
        for team, row in results.iterrows():
            sim_data[team]['matchup_wins'] += row.matchup_wins
            sim_data[team]['tophalf_wins'] += row.tophalf_wins
            sim_data[team]['total_wins'] += row.matchup_wins + row.tophalf_wins
            sim_data[team]['total_points'] += row.total_points

    # get playoff standings
    top_by_wins = sorted(sim_data.items(), key=lambda x: (x[1]['total_wins'], x[1]['total_points']), reverse=True)[:params.playoff_teams-1]
    bottom_five = {k: v for k, v in sim_data.items() if k not in [t[0] for t in top_by_wins]}
    wild_card = sorted(bottom_five.items(), key=lambda x: x[1]['total_points'], reverse=True)[:1]
    rest_by_wins = sorted({k: v for k, v in bottom_five.items() if k not in [t[0] for t in wild_card]}.items(), key=lambda x: (x[1]['total_wins']), reverse=True)
    sim_data_standings = dict(top_by_wins + wild_card + rest_by_wins)
    for i, (k, v) in enumerate(sim_data_standings.items()):
        sim_data_standings[k]['rank'] = i+1

    if params.current_week <= params.regular_season_end:
        playoff_teams = list({k: v for k, v in sim_data_standings.items() if v['rank'] <= params.playoff_teams}.keys())
    else:
        # if currently in playoffs, get teams and ranks
        playoff_teams = []
        for m in playoff_matchups:
            tmid = m.get('home').get('teamId')
            tmrk = [d for d in teams.teams['teams'] if d['id'] == tmid][0]['playoffSeed']
            playoff_teams.append({'team': constants.TEAM_IDS[teams.teamid_to_primowner[tmid]]['name']['display'], 'rank': tmrk})
            if 'away' in m:
                tmid = m.get('away').get('teamId')
                tmrk = [d for d in teams.teams['teams'] if d['id'] == tmid][0]['playoffSeed']
                playoff_teams.append({'team': constants.TEAM_IDS[teams.teamid_to_primowner[tmid]]['name']['display'], 'rank': tmrk})
        playoff_teams = [d['team'] for d in sorted(playoff_teams, key=lambda x: x['rank'])]


    # sim playoffs
    start_wk = params.regular_season_end+1 if params.current_week <= params.regular_season_end else params.current_week
    champ_wk = params.regular_season_end+4
    playoff_wks_left = champ_wk - start_wk
    playoff_weeks = list(range(params.regular_season_end+1, params.regular_season_end+4))

    round_kwargs = [
        {'n_bye': 2, 'week_data': week_data, 'matchups': playoff_matchups, 'projections': projections_dict, 'rosters': rosters} if champ_wk-wk == 3 else
        {'week_data': week_data, 'matchups': playoff_matchups, 'projections': projections_dict, 'rosters': rosters} if 0 < champ_wk-wk  < 3 else
        {}
        for wk in playoff_weeks
    ]

    r1_playoff_teams = playoff_teams.copy()
    finals_teams = None
    champion = None
    for i, week in enumerate(playoff_weeks[-playoff_wks_left:]):
        kwargs = round_kwargs[i]
        playoff_teams = simulations.sim_playoff_round(
            week=week,
            lineups=lineups,
            round_teams=playoff_teams,
            params=params,
            replacement_players=replacement_players,
            teams=teams,
            **kwargs
        )
        if i == playoff_wks_left - 2:
            finals_teams = playoff_teams
        if i == playoff_wks_left - 1:
            champion = playoff_teams

    ## update sim stats
    for team in team_names:
        sim_results[team]['rank'] += sim_data[team]['rank']
        sim_results[team]['matchup_wins'] += sim_data[team]['matchup_wins']
        sim_results[team]['tophalf_wins'] += sim_data[team]['tophalf_wins']
        sim_results[team]['total_wins'] += sim_data[team]['total_wins']
        sim_results[team]['total_points'] += sim_data[team]['total_points']

        # playoffs
        if team in r1_playoff_teams:
            sim_results[team]['playoffs'] += 1

        if team in finals_teams:
            sim_results[team]['finals'] += 1

        if team in champion:
            sim_results[team]['champion'] += 1

    all_sim_results.append(sim_results)
end = time.perf_counter()
print(end-start, 'seconds')

# get wins table
flattened_results = []
for sim_index, sim_result in enumerate(all_sim_results):
    for team, stats in sim_result.items():
        stats['team'] = team
        stats['simulation'] = sim_index
        flattened_results.append(stats)

# Convert to a DataFrame
all_sim_results_df = pd.DataFrame(flattened_results).sort_values('team')
columns_order = ['simulation', 'team', 'rank', 'matchup_wins', 'tophalf_wins', 'total_wins', 'total_points', 'playoffs', 'finals', 'champion']
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

# get ranks table
ranks_prob_df = all_sim_results_df.groupby(['team', 'rank']).simulation.count().reset_index().rename(columns={'simulation':'p'})
ranks_prob_df['p'] = ranks_prob_df.p / n_sims
ranks_prob_df['season'] = constants.SEASON
ranks_prob_df['week'] = params.current_week
ranks_prob_df['id'] = ranks_prob_df.season.astype(str) + '_' + ranks_prob_df.week.astype(str).str.zfill(2) + '_' + ranks_prob_df['rank'].astype(str).str.zfill(2) + '_' + ranks_prob_df.team

# get season_sims table
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

# update db's
season_sim_table = 'season_sim'
season_sim_cols = constants.SEASON_SIM_COLUMNS
for idx, row in sim_df.iterrows():
    sim_vals = (row.id, row.season, row.week, row.team, row.matchup_wins, row.tophalf_wins,
                row.total_wins, row.total_points, row.playoffs, row.finals, row.champion)
    db = Database(data=sim_df, table=season_sim_table, columns=season_sim_cols, values=sim_vals)
    db.commit_row()

if params.current_week <= params.regular_season_end+1:
    sim_wins_table = 'season_sim_wins'
    sim_wins_cols = 'id, season, week, team, wins, p'
    for idx, row in wins_prob_df.iterrows():
        sim_vals = (row.id, row.season, row.week, row.team, row.wins, row.p)
        db = Database(data=wins_prob_df, table=sim_wins_table, columns=sim_wins_cols, values=sim_vals)
        db.commit_row()

    sim_ranks_table = 'season_sim_ranks'
    sim_ranks_cols = 'id, season, week, team, ranks, p'
    for idx, row in ranks_prob_df.iterrows():
        sim_vals = (row.id, row.season, row.week, row.team, row['rank'], row.p)
        db = Database(data=ranks_prob_df, table=sim_ranks_table, columns=sim_ranks_cols, values=sim_vals)
        db.commit_row()
