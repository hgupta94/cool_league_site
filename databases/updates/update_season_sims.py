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
replacement_players = rosters.get_replacements()
lineups = simulations.get_ros_projections(data=data, params=params, teams=teams, rosters=rosters, replacement_players=replacement_players)

# get top scorers so far
top_scores = Database(table='h2h', season=constants.SEASON, week=params.as_of_week).retrieve_data(how='season')
top_scores = top_scores.groupby(['team', 'week']).result.sum().reset_index()

# get standings
results = Database(table='matchups', season=constants.SEASON, week=params.as_of_week).retrieve_data(how='season')
results = results[['team', 'score', 'matchup_result', 'tophalf_result']].groupby('team').sum()
results.columns = ['total_points', 'matchup_wins', 'tophalf_wins']
if params.current_week > 1:
    top_scores = top_scores[top_scores.result == max(top_scores.result)].groupby('team').result.count()
    results = pd.merge(results, top_scores, left_index=True, right_index=True, how='outer').rename(columns={'result': 'top_scores'}).fillna(0)

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

# build playoff sim kwargs
start_wk = params.regular_season_end + 1 if params.current_week <= params.regular_season_end else params.current_week  # check if currently in playoffs
champ_wk = params.regular_season_end + params.playoff_length
playoff_wks_left = champ_wk - start_wk + 1
playoff_weeks = list(range(params.regular_season_end+1, champ_wk+1))
round_kwargs = [
    {
        'n_bye': 2,
        'week_data': week_data,
        'matchups': playoff_matchups,
        'projections': projections_dict,
        'rosters': rosters  # RosterSettings object
    } if champ_wk-wk == 2
    else {
        'week_data': week_data,
        'matchups': playoff_matchups,
        'projections': projections_dict,
        'rosters': rosters  # RosterSettings object
    }
    for wk in playoff_weeks
]

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
            'most_wins': 0,
            'most_points': 0,
            'top_scores': 0,
            'playoffs': 0,
            'third': 0,
            'finals': 0,
            'champion': 0
        }
        for o in team_names
    }

    # add actual season and current week sim results
    sim_data = simulations.simulate_season(params=params, teams=teams, lineups=lineups, team_names=team_names)
    if len(results):
        for team, row in results.iterrows():
            sim_data[team]['matchup_wins'] += int(row.matchup_wins)
            sim_data[team]['tophalf_wins'] += int(row.tophalf_wins)
            sim_data[team]['total_wins'] += int(row.matchup_wins + row.tophalf_wins)
            sim_data[team]['total_points'] += float(row.total_points)
            sim_data[team]['top_score'] += int(row.top_scores)

    # get playoff standings
    n_top = params.playoff_teams - 1
    ordered = sorted(
        sim_data.items(),
        key=lambda kv: (kv[1]['total_wins'], kv[1]['total_points']),
        reverse=True
    )
    top_teams = ordered[:n_top]
    bottom_teams = sorted(
        ordered[n_top:],
        key=lambda kv: (kv[1]['total_points'], kv[1]['total_wins']),
        reverse=True
    )
    sim_data_standings = dict(top_teams + bottom_teams)
    for rank, (team, data) in enumerate(sim_data_standings.items(), start=1):
        sim_data_standings[team]['rank'] = rank

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
    qf_teams = set(playoff_teams.copy())
    sf_teams = None
    third_place_teams = None
    third = None
    finals_teams = None
    champion = None
    for i, week in enumerate(playoff_weeks[-playoff_wks_left:]):
        kwargs = round_kwargs[i]
        this_week_lineups = lineups[week]
        playoff_teams = simulations.sim_playoff_round(
            week=week,
            lineups=this_week_lineups,
            round_teams=playoff_teams,
            params=params,
            replacement_players=replacement_players,
            teams=teams,  # TeamSettings object
            **kwargs
        )
        if week == champ_wk - 2:  # finished quarterfinals
            sf_teams = set(playoff_teams.copy())
        if week == champ_wk - 1:  # finished semifinals
            finals_teams = set(playoff_teams.copy())
            third_place_teams = set(t for t in sf_teams if t not in finals_teams)
        if week == champ_wk:  # finished championship
            third_place_lineups = {k: v for k, v in this_week_lineups.items() if k in third_place_teams}
            third_place_sim = {t: simulations.simulate_lineup(l) for t, l in third_place_lineups.items()}
            third = max(third_place_sim.items(), key=lambda x: x[1])[0]
            champion = playoff_teams.copy()[0]

    ## update sim stats
    most_wins = max(s['total_wins'] for s in sim_data.values())
    most_points = max(s['total_points'] for s in sim_data.values())
    n_most_wins = len([s['total_wins'] for s in sim_data.values() if s['total_wins'] == most_wins])
    n_most_points = len([s['total_points'] for s in sim_data.values() if s['total_points'] == most_points])
    for team in team_names:
        sim_results[team]['rank'] += sim_data[team]['rank']
        sim_results[team]['matchup_wins'] += sim_data[team]['matchup_wins']
        sim_results[team]['tophalf_wins'] += sim_data[team]['tophalf_wins']
        sim_results[team]['total_wins'] += sim_data[team]['total_wins']
        sim_results[team]['total_points'] += sim_data[team]['total_points']
        sim_results[team]['top_scores'] += sim_data[team]['top_score']

        if sim_data[team]['total_points'] == most_points:
            sim_results[team]['most_points'] += 1 / n_most_points

        if sim_data[team]['total_wins'] == most_wins:
            sim_results[team]['most_wins'] += 1 / n_most_wins

        # playoffs
        if team in qf_teams:
            sim_results[team]['playoffs'] += 1

        if team in finals_teams:
            sim_results[team]['finals'] += 1

        if team == third:
            sim_results[team]['third'] += 1

        if team == champion:
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
columns_order = ['simulation', 'team', 'rank', 'matchup_wins', 'tophalf_wins', 'total_wins', 'total_points', 'most_points', 'most_wins', 'top_scores', 'playoffs', 'third', 'finals', 'champion']
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
            'top_scores': 0,
            'most_wins': 0,
            'most_points': 0,
            'playoffs': 0,
            'third': 0,
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
        team_totals[team]['top_scores'] += team_sim[team]['top_scores']
        team_totals[team]['most_wins'] += team_sim[team]['most_wins']
        team_totals[team]['most_points'] += team_sim[team]['most_points']
        team_totals[team]['playoffs'] += team_sim[team]['playoffs']
        team_totals[team]['third'] += team_sim[team]['third']
        team_totals[team]['finals'] += team_sim[team]['finals']
        team_totals[team]['champion'] += team_sim[team]['champion']

sim_df = pd.DataFrame(team_totals).transpose() / n_sims
sim_df = sim_df.reset_index().rename(columns={'index': 'team'})
sim_df['season'] = constants.SEASON
sim_df['week'] = params.current_week
sim_df['id'] = sim_df.season.astype(str) + '_' + sim_df.week.astype(str).str.zfill(2) + '_' + sim_df.team

# update db's
season_sim_table = 'season_sim'
print(f'writing to {season_sim_table} table')
season_sim_cols = constants.SEASON_SIM_COLUMNS
for idx, row in sim_df.iterrows():
    print(f'commited {idx+1}/{len(sim_df)}', end='\r')
    sim_vals = (row.id, row.season, row.week, row.team, row.matchup_wins, row.tophalf_wins,
                row.total_wins, row.total_points, row.most_wins, row.most_points,
                row.top_scores, row.playoffs, row.third, row.finals, row.champion)
    db = Database(data=sim_df, table=season_sim_table, columns=season_sim_cols, values=sim_vals)
    db.commit_row()

if params.current_week <= params.regular_season_end+1:
    sim_wins_table = 'season_sim_wins'
    print(f'writing to {sim_wins_table} table')
    sim_wins_cols = 'id, season, week, team, wins, p'
    for idx, row in wins_prob_df.iterrows():
        print(f'commited {idx+1}/{len(wins_prob_df)}', end='\r')
        sim_vals = (row.id, row.season, row.week, row.team, row.wins, row.p)
        db = Database(data=wins_prob_df, table=sim_wins_table, columns=sim_wins_cols, values=sim_vals)
        # db.commit_row()

    sim_ranks_table = 'season_sim_ranks'
    print(f'writing to {sim_ranks_table} table')
    sim_ranks_cols = 'id, season, week, team, ranks, p'
    for idx, row in ranks_prob_df.iterrows():
        print(f'commited {idx+1}/{len(ranks_prob_df)}', end='\r')
        sim_vals = (row.id, row.season, row.week, row.team, row['rank'], row.p)
        db = Database(data=ranks_prob_df, table=sim_ranks_table, columns=sim_ranks_cols, values=sim_vals)
        # db.commit_row()
