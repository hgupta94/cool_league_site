from scripts.api.DataLoader import DataLoader
from scripts.api.Teams import Teams
from scripts.api.Settings import Params
from scripts.api.Rosters import Rosters
from scripts.utils import (utils as ut, constants as const)
from scripts.simulations.projections import (query_projections_db, simulate_week)
from scripts.home.power_ranks import power_rank
from scripts.home.standings import get_standings
from scripts.home.update_standings_db import commit_standings
from scripts.simulations.functions import get_week_projections
from scripts.scenarios.scenarios import (get_h2h, schedule_switcher)
from scripts.scenarios.update_scenarios_db import (commit_h2h,
                                                   commit_ss)
from scripts.efficiency.efficiencies import get_optimal_points

import pandas as pd
import numpy as np


season = const.SEASON
league_id = const.LEAGUE_ID
swid = const.SWID
espn_s2 = const.ESPN_S2

# Home Page
prs = []
for s in range(2018, const.SEASON):
    print(s)
    d = ut.load_data(league_id=league_id, swid=swid, espn_s2=espn_s2, season=s)
    params = ut.get_params(d)

    for w in range(1, params['regular_season_end']+1):
        # power ranks
        if w == 1:
            curr_pr = power_rank(params, w)
            curr_ranks_pr = {t: params['league_size'] - list(curr_pr.keys()).index(t) for t in list(curr_pr.keys())}
            final_pr_dict = \
                {
                    t: [s,
                        w,
                        curr_pr[t]*100,
                        0,
                        curr_ranks_pr[t],
                        0]
                    for t in params['teams']
                }
            prs.append(final_pr_dict)
        if w > 1:
            # calculat score and rank differences
            prev_pr = power_rank(params, w-1)
            curr_pr = power_rank(params, w)

            prev_ranks_pr = {t: params['league_size'] - list(prev_pr.keys()).index(t) for t in list(prev_pr.keys())}
            curr_ranks_pr = {t: params['league_size'] - list(curr_pr.keys()).index(t) for t in list(curr_pr.keys())}

            score_diff = {t: curr_pr[t]-prev_pr[t] for t in params['teams']}
            ranks_diff = {t: curr_ranks_pr[t]-prev_ranks_pr[t] for t in params['teams']}

            final_pr_dict = \
                {
                    t: [s,
                        w,
                        curr_pr[t]*100,
                        score_diff[t]*100,
                        curr_ranks_pr[t],
                        -ranks_diff[t]]
                    for t in params['teams']
                }
            prs.append(final_pr_dict)

pr_df = pd.DataFrame()
for i in prs:
    pr_df = pd.concat([pr_df, pd.DataFrame.from_dict(i, orient='index')])
pr_df = pr_df.reset_index()
pr_df.columns = ['team', 'season', 'week', 'score', 'score_change', 'rank', 'rank_change']

teams = params['teams']
team_map = params['team_map']
flatten_first = {}
flatten_display = {}
for k, v in team_map.items():
    flatten_first[k] = v['name']['first']
    flatten_display[k] = v['name']['display']
pr_df['team'] = pr_df.team.map(flatten_first)
pr_df = pr_df.sort_values(['season', 'week', 'rank'])


# Simulations Page
# Week Sims
from scripts.api.DataLoader import DataLoader
from scripts.api.Teams import Teams
from scripts.api.Settings import Params
from scripts.api.Rosters import Rosters
from scripts.utils import (utils as ut, constants as const)
from scripts.simulations.projections import (query_projections_db, simulate_week, calculate_odds)
from time import perf_counter

season, week = 2023, 6
data = DataLoader(year=season)
week_data = data.load_week(week=week)
rosters = Rosters(year=season)
teams = Teams(data)
projections = query_projections_db(season, week)
matchups = [m for m in teams.matchups['schedule'] if m['matchupPeriodId'] == week]
n_sims = 10000

start = perf_counter()
sim_scores, sim_wins, sim_tophalf, sim_highest, sim_lowest = simulate_week(week_data=week_data,
                                                                           teams=teams,
                                                                           rosters=rosters,
                                                                           projections=projections,
                                                                           matchups=matchups,
                                                                           week=week,
                                                                           n_sims=n_sims)
end = perf_counter()

elapsed = end-start
print(f'{elapsed} seconds')
odds_wins    = calculate_odds(sim_wins, n_sims)
odds_tophalf = calculate_odds(sim_tophalf, n_sims)
odds_highest = calculate_odds(sim_highest, n_sims)
odds_lowest  = calculate_odds(sim_lowest, n_sims)




# used for efficiency chart
# tried plotting lines for percentages
# def color(r):
#     if 0.7 <= r < 0.75:
#         return 'cyan'
#     if 0.75 <= r < 0.8:
#         return 'salmon'
#     elif 0.8 <= r < 0.85:
#         return 'dodgerblue'
#     elif 0.85 <= r < 0.9:
#         return 'lightsteelblue'
#     elif 0.9 <= r <= 0.95:
#         return 'royalblue'
#     elif 0.95 <= r <= 1:
#         return 'blue'
#     else:
#         return 'grey'
#
# fig, ax = plt.subplots()
# for x in np.arange(-25, -5, 0.5):
#     for y in np.arange(105, 150, 0.5):
#         ratio = ((y + x) / y)
#         plt.scatter(x, y, c=color(ratio))
# plt.savefig('figure.png')



# Databases
season = 2023
week = 5
league_id = const.LEAGUE_ID
swid = const.SWID
espn_s2 = const.ESPN_S2

w = ut.load_weekly_data(season=season, week=week, league_id=league_id, swid=swid, espn_s2=espn_s2)
params = ut.get_params(w)


# bulk load scenarios page
with ut.mysql_connection() as conn:
    for s in range(2018, const.SEASON):
        s = 2024
        data = DataLoader(s)
        teams = Teams(data)
        params = Params(data)
        end = params.as_of_week if params.regular_season_end > params.as_of_week else params.regular_season_end
        h2h = pd.DataFrame()
        for wk in range(1, params.regular_season_end+1):
            print(s, wk)
            h2h_data = get_h2h(teams=teams, season=s, week=wk)
            h2h = pd.concat([h2h, h2h_data])

        total_wins = h2h.groupby('team').result.sum().reset_index()
        total_wins['losses'] = (((len(teams.team_ids)-1) * end) - total_wins.result)
        total_wins['record'] = total_wins.result.astype('Int64').astype(str) + '-' + total_wins.losses.astype('Int64').astype(str)
        total_wins['win_perc'] = total_wins.result / ((len(teams.team_ids)-1) * end)
        total_wins['win_perc'] = total_wins.win_perc.map('{:.3f}'.format)
        total_wins_final = total_wins[['team', 'record', 'win_perc']]

        wins_by_week = h2h.groupby(['team', 'week']).result.sum().reset_index()
        wins_by_week['losses'] = (len(teams.team_ids)-1) - wins_by_week.result
        wins_by_week['record'] = wins_by_week.result.astype('Int64').astype(str) + '-' + wins_by_week.losses.astype('Int64').astype(str)
        wins_by_week_p = wins_by_week.pivot(index='team', columns='week', values='record')
        wins_by_week_final = pd.merge(wins_by_week_p, total_wins, on='team').sort_values('result', ascending=False).drop(columns=['result', 'losses'], axis=1)

        wins_vs_opp = h2h.groupby(['team', 'opp']).result.sum().reset_index()
        wins_vs_opp['losses'] = end - wins_vs_opp.result
        wins_vs_opp['record'] = wins_vs_opp.result.astype('Int64').astype(str) + '-' + wins_vs_opp.losses.astype('Int64').astype(str)
        wins_vs_opp_p = wins_vs_opp.pivot(index='team', columns='opp', values='record')
        wins_vs_opp_final = pd.merge(wins_vs_opp_p, total_wins_final, on='team').sort_values('win_perc', ascending=False)
        col_order = [['team'], wins_vs_opp_final.team.to_list(), ['record', 'win_perc']]
        col_order = [x for xs in col_order for x in xs]
        wins_vs_opp_final = wins_vs_opp_final[col_order].set_index('team')
        for i in range(min(wins_vs_opp_final.shape)):
            # blank out diagonals where teams intersect
            wins_vs_opp_final.iloc[i, i] = ''
        wins_vs_opp_final.reset_index(inplace=True)

with ut.mysql_connection() as conn:
    for s in range(2018, const.SEASON):
        data = DataLoader(s)
        teams = Teams(data)
        df = pd.DataFrame()
        for wk in range(1, 15):
            print(s, wk)
            ss_data = schedule_switcher(teams=teams, season=s, week=wk)
            df = pd.concat([df, ss_data])

        test = df.groupby(['team', 'schedule_of']).result.sum().reset_index()
df_wide = test.pivot(index='team', columns='schedule_of', values='result')


# get all member IDs
league_id = const.LEAGUE_ID
swid = const.SWID
espn_s2 = const.ESPN_S2
seasons = range(2018, 2024)
df = pd.DataFrame(columns=['id', 'fname', 'lnam'])
for s in seasons:
    d = ut.load_data(league_id=league_id, swid=swid, espn_s2=espn_s2, season=s)
    for i in [[game['id'], game['firstName'], game['lastName']] for game in d['members']]:
        df.loc[len(df)] = i

df = pd.DataFrame(columns=['id', 'owner_id'])
for s in seasons:
    d = ut.load_data(league_id=league_id, swid=swid, espn_s2=espn_s2, season=s)
    for i in [[game['id'], game['primaryOwner']] for game in d['teams']]:
        df.loc[len(df)] = i

df = df.drop_duplicates()





# get player actual scores by position, week
final_df = pd.DataFrame()
slots = const.SLOTCODES
positions = const.POSITION_MAP
for s in range(2021, 2025):
    d = DataLoader(year=s)
    params = Params(d)
    rosters = Rosters(year=s)
    slot_limits = rosters.slot_limits
    ssn_df = pd.DataFrame()
    for wk in range(1, 15):
        print(s, wk)
        week_data = d.load_week(week=wk)
        wk_df = pd.DataFrame()
        for team in week_data['teams']:
            tm_list = []
            owr_id = team['primaryOwner']
            owr_name = params.team_map[owr_id]['name']['display']
            for plr in team['roster']['entries']:
                # loop thru each player to get relevant data
                plr_id = plr['playerId']
                plr_name = plr['playerPoolEntry']['player']['fullName']
                slot_id = plr['lineupSlotId']
                slot = slots[slot_id]
                psns = plr['playerPoolEntry']['player']['eligibleSlots']
                injury = plr['injuryStatus']
                for p in psns:
                    try:
                        psn = positions[p]
                        psn_id = p
                    except KeyError:
                        pass

                points = 0
                for stat in plr['playerPoolEntry']['player']['stats']:
                    if stat['scoringPeriodId'] == wk:
                        if stat['statSourceId'] == 0:
                            # actual points that week
                            points = stat['appliedTotal']

                tm_list.append([s, wk, owr_name, plr_name, psn, slot, points, injury])
            temp = pd.DataFrame(tm_list)
            wk_df = pd.concat([wk_df, temp])
        ssn_df = pd.concat([ssn_df, wk_df])
    final_df = pd.concat([final_df, ssn_df])
final_df.columns = ['season', 'week', 'team', 'player', 'position', 'slot', 'points', 'injury']

final_df_non0 = final_df[~(final_df.slot.isin(['BE', 'IR', 'K',])) & (final_df.position != 'K') & (final_df.points > 1)]

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import scipy.stats as st


for pos in ['QB', 'RB', 'WR', 'TE', 'DST']:
    # fit scores using a gamma distribution
    # pos = 'QB'
    df = final_df_non0[final_df_non0.position == pos]
    dist = getattr(st, 'gamma')
    param = dist.fit(df.points)

    x = df.points
    print(pos, round(x.mean(), 4), param)
    proj = 8
    a = const.GAMMA_VALUES[pos]['a']
    loc = const.GAMMA_VALUES[pos]['loc'] + (proj-x.mean())
    scale = const.GAMMA_VALUES[pos]['scale']
    samples = st.gamma.rvs(a=a, loc=loc, scale=scale, size=1000)
    pdf = st.gamma.pdf(x, a=a, loc=loc, scale=scale)

    fig, ax = plt.subplots()
    ax = df.points.hist(bins=20, density=True, label='Points Scored')  # plot points scored
    plt.hist(samples, bins=20, density=True, alpha=0.6, label='Gamma Random Samples')  # plot samples
    plt.plot(x, pdf, 'ro', alpha=0.2, label='Gamma Dist. PDF')  # overlay the PDF for comparison
    plt.title(f'{pos} -- Points, Random Samples (n=1000), and Gamma PDF')
    plt.xlabel('Points Scored')
    plt.ylabel('Density')
    plt.legend()
    plt.grid(True)
    fig.savefig(f'tests/plots/{pos}.png')
