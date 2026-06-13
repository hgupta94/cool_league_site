from scripts.simulations.simulations import Simulation
from scripts.api.models.player import ParseContext, PlayerView
from scripts.api.dataloader import DataLoader
from scripts.api.fantasy_pros import FantasyPros
from scripts.utils.constants import SEASON, WEEK, SEASON_SIM_COLUMNS
from scripts.utils.database import Database
from scripts.api.settings import LeagueSettings
from scripts.api.models.team import Team

import time

import pandas as pd
import json


# with open(r'/Users/hirshgupta/PycharmProjects/cool_league_site/tables/fp_espn_lookup.json', 'r') as f:
#     mapping = json.load(f)


def load_season_sims(dataloader: DataLoader, fpros: FantasyPros, n_sims: int = 100_000):
    ctx = ParseContext(view=PlayerView.WEEK)
    params = LeagueSettings(dataloader=dataloader)
    teams_obj = dataloader.teams()
    rosters_obj = dataloader.rosters()
    teams = Team.get_teams(dataloader=dataloader, fpros=fpros, obj=teams_obj, roster_obj=rosters_obj, ctx=ctx)

    db = Database()
    q = f'''
        SELECT team, COUNT(*) AS n FROM (
            SELECT
                week,
                team,
                SUM(result) AS r
            FROM h2h
            WHERE season={params.season}
                AND week < {params.current_week}
            GROUP BY team, week
            HAVING r={len(teams)-1}
        ) t
        GROUP BY team;
    '''
    top_scores = db.query(query=q)

    results = db.retrieve_data(how='season', table='matchups', season=params.season, week=params.as_of_week)
    results = results[['team', 'score', 'matchup_result', 'tophalf_result']].groupby('team').sum().reset_index()
    results['total_wins'] = results.matchup_result + results.tophalf_result
    results.columns = ['team', 'total_points', 'matchup_wins', 'tophalf_wins', 'total_wins']
    if WEEK > 1:
        results = pd.merge(results, top_scores, on='team', how='outer').rename(columns={'n': 'top_scores'}).fillna(0)
    results_dict = {int(row.team): row.drop(labels=['team']).to_dict() for i, row in results.iterrows()}

    sims = Simulation(dataloader, fpros=fpros)

    start = time.perf_counter()
    sim_results = sims.simulate_full_season(results=results_dict, n_sims=n_sims)
    end = time.perf_counter()
    print((end - start) / 60)

    flattened_results = []
    for sim_index, result in enumerate(sim_results):
        for team, stats in result.items():
            stats['team'] = team
            stats['simulation'] = sim_index
            flattened_results.append(stats)

    # Convert to a DataFrame
    sim_results_df = pd.DataFrame(flattened_results).sort_values('team')
    columns_order = ['simulation', 'team', 'seed', 'matchup_wins', 'tophalf_wins', 'total_wins', 'total_points', 'most_points', 'most_wins', 'top_scores', 'playoffs', 'third', 'finals', 'champion']
    sim_results_df = sim_results_df[columns_order]

    # get wins table
    rows = []
    for tid in teams:
        temp = sim_results_df[sim_results_df.team == tid]
        for wins in range(0, (2*params.regular_season_end)+1):
            prob = len(temp[temp.total_wins == wins]) / n_sims
            if prob > 0:
                rows.append([tid, wins, prob])
    wins_prob_df = pd.DataFrame(rows, columns=['team', 'wins', 'p'])
    wins_prob_df['season'] = SEASON
    wins_prob_df['week'] = params.current_week
    wins_prob_df['id'] = wins_prob_df.season.astype(str) + '_' + wins_prob_df.week.astype(str).str.zfill(2) + '_' + wins_prob_df.wins.astype(str).str.zfill(2) + '_' + wins_prob_df.team.astype(str).str.zfill(2)


    # get ranks table
    ranks_prob_df = sim_results_df.groupby(['team', 'seed']).simulation.count().reset_index().rename(columns={'simulation':'p'})
    ranks_prob_df['p'] = ranks_prob_df.p / n_sims
    ranks_prob_df['season'] = SEASON
    ranks_prob_df['week'] = params.current_week
    ranks_prob_df['id'] = ranks_prob_df.season.astype(str) + '_' + ranks_prob_df.week.astype(str).str.zfill(2) + '_' + ranks_prob_df['seed'].astype(str).str.zfill(2) + '_' + ranks_prob_df.team.astype(str).str.zfill(2)


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
            for o in teams
        }

    for team in teams:
        for a in sim_results:
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
    sim_df['season'] = SEASON
    sim_df['week'] = params.current_week
    sim_df['id'] = sim_df.season.astype(str) + '_' + sim_df.week.astype(str).str.zfill(2) + '_' + sim_df.team.astype(str).str.zfill(2)


    # update db's
    db = Database()

    sim_df = sim_df[SEASON_SIM_COLUMNS.split(', ')]
    db.batch_insert(
        table='season_sim',
        columns=SEASON_SIM_COLUMNS,
        rows=[tuple(row) for _, row in sim_df.iterrows()],
        upsert=True
    )

    if params.current_week <= params.regular_season_end + 1:
        # no need to update these in the postseason
        wins_prob_df = wins_prob_df[['id', 'season', 'week', 'team', 'wins', 'p']]
        db.batch_insert(
            table='season_sim_wins',
            columns='id, season, week, team, wins, p',
            rows=[tuple(row) for _, row in wins_prob_df.iterrows()],
            upsert=True
        )

        ranks_prob_df = ranks_prob_df[['id', 'season', 'week', 'team', 'seed', 'p']]
        db.batch_insert(
            table='season_sim_ranks',
            columns='id, season, week, team, ranks, p',
            rows=[tuple(row) for _, row in ranks_prob_df.iterrows()],
            upsert=True
        )

if __name__ == '__main__':
    dataloader = DataLoader(week=WEEK)
    fpros = FantasyPros(dataloader=dataloader)
    load_season_sims(dataloader=dataloader, fpros=fpros)
