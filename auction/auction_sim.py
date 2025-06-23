from scripts.api.DataLoader import DataLoader
from scripts.utils.constants import POSITION_MAP, NFL_TEAM_MAP

import matplotlib.pyplot as plt

import requests
import copy
import random
from sklearn.mixture import GaussianMixture as gm
import scipy.stats as stats
import pandas as pd
import numpy as np
import time
import pickle


STARTER_ALLOCATION = 0.8
BUDGET = 200
MIN_BID = 1
N_TEAMS = 10
N_BENCH = 6
POSITIONS = ['QB', 'RB', 'WR', 'TE', 'DST']
FLEX_POSITIONS = ['RB', 'WR']
N_FLEX = 1
STARTERS = [1, 2, 3, 1, 1]


def get_byes(season):
    url = f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{season}?view=proTeamSchedules_wl'
    r = requests.get(url)
    d = r.json()

    byes_dict = {}
    for tm in d['settings']['proTeams']:
        byes_dict[tm['abbrev'].upper()] = tm['byeWeek']

    return byes_dict


def load_espn_data(season: int,
                   byes: dict):
    data = DataLoader(season)
    players = data.players_info()

    players_dict = {}
    rank_ov = 1
    for player in players['players']:
        full_name = player['player']['fullName']
        team = NFL_TEAM_MAP[player['player']['proTeamId']]
        if team == 'None':
            continue
        bye = byes[team]
        pl_rank_ov = rank_ov
        rank_ov +=1

        for pos in player['player']['eligibleSlots']:
            if pos in POSITION_MAP.keys():
                position = POSITION_MAP[pos]

        projection_total = 0
        projection_ppg = 0
        for stat in player['player']['stats']:
            if (stat['seasonId'] == season) and (stat['statSourceId'] == 1) and (stat['statSplitTypeId'] == 0):
                projection_total = stat['appliedTotal']
                projection_ppg = stat['appliedAverage']
        players_dict[player['id']] = {
            'name': full_name,
            'position': position,
            'team': team,
            'bye': bye,
            'rank_ov': pl_rank_ov,
            'projection_total': projection_total,
            'ppg': projection_ppg
        }
    players_sorted = dict(sorted(players_dict.items(), key=lambda x: x[1]['projection_total'], reverse=True))

    rank_pos = {
        'QB': 1,
        'RB': 1,
        'WR': 1,
        'TE': 1,
        'DST': 1
    }
    for _, player in players_sorted.items():
        # get position ranks
        player['rank_pos'] = rank_pos[player['position']]
        rank_pos[player['position']] += 1
    return {k: v for k, v in players_sorted.items() if v['ppg'] > 1}


def calculate_prices(
        players_data: dict,
        starter_allocation: float = 0.8,
        budget: int = 200,
        min_bid: int = 1,
        n_teams: int = 10,
        n_bench: int = 6,
        positions: list[str] = ['QB', 'RB', 'WR', 'TE', 'DST'],
        flex_positions: list[str] = ['RB', 'WR'],
        n_flex: int = 1,
        starters: list[int] = [1, 2, 3, 1, 1]
):
    backups = [0.5/n_bench, 2.5/n_bench, 2.5/n_bench, 0.5/n_bench, 0]  # percent of bench spots occupied by position
    bench_allocation = round(1 - starter_allocation, 2)  # percent of budget allocated to bench
    total_dollars = budget * n_teams
    roster_size = sum(starters) + n_bench + n_flex
    available_spend = (total_dollars - (roster_size * min_bid * n_teams))  # each player costs a min of $1 leaving ($200 - roster_size) extra to spend per team

    # get replacement player projected points
    replacement_pts_starters = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'DST': 0}
    replacement_pts_bench = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'DST': 0}
    for pos in zip(positions, starters, backups):
        # calculate number of players drafted by position
        if pos[0] in flex_positions:
            n_total_drafted = (
                    ((pos[1] + (n_flex / len(flex_positions))) * n_teams)
                    + (n_bench * pos[2] * n_teams)
            )
            n_starters_drafted = (pos[1] + 0.5) * n_teams
            replacement_rank_starters = n_starters_drafted + 1
        else:
            n_total_drafted = (pos[1] * n_teams) + (n_bench * pos[2] * n_teams)
            replacement_rank_starters = pos[1] * n_teams + 1
        replacement_rank_bench = n_total_drafted + 1
        replacement_starters_fpts = [
             v['projection_total'] for k, v
             in players_data.items()
             if (v['position'] == pos[0])
             and (v['rank_pos'] == replacement_rank_starters)
        ][0]
        replacement_pts_starters[pos[0]] = replacement_starters_fpts
        replacement_bench_fpts = [
             v['projection_total'] for k, v
             in players_data.items()
             if (v['position'] == pos[0])
             and (v['rank_pos'] == replacement_rank_bench)
        ][0]
        replacement_pts_bench[pos[0]] = replacement_bench_fpts

    # player_vor_dict = {}
    for _, player in players_data.items():
        player['player_type'] = (
            'starter' if player['projection_total'] > replacement_pts_starters[player['position']]
            else 'bench' if player['projection_total'] > replacement_pts_bench[player['position']]
            else 'undrafted'
        )

        # value over replacement
        player['vor_st'] = 0 if (player['projection_total'] - replacement_pts_starters[player['position']]) < 0 else (player['projection_total'] - replacement_pts_starters[player['position']])
        player['vor_bn'] = 0 if (player['projection_total'] - replacement_pts_bench[player['position']]) < 0 or (player['position'] == 'DST') else (player['projection_total'] - replacement_pts_bench[player['position']])
        player['vor_tot'] = player['vor_st'] + player['vor_bn']

    # dollar per vor
    starter_dpv = (
            (available_spend * starter_allocation) / sum(v['vor_tot'] for k, v in players_data.items() if v['player_type'] == 'starter')
            + (available_spend * bench_allocation) / sum(v['vor_tot'] for k, v in players_data.items() if v['player_type'] == 'bench')
    )
    bench_dpv = (available_spend * bench_allocation) / sum(v['vor_tot'] for k, v in players_data.items() if v['player_type'] == 'bench')

    for _, player in players_data.items():
        player['value'] = player['vor_st'] * starter_dpv + player['vor_bn'] * bench_dpv + min_bid

    for _, player in players_data.items():
        player['price'] = player['value'] / (sum(v['value'] for k, v in players_data.items()) / total_dollars)

    return dict(sorted(players_data.items(), key=lambda x: x[1]['value'], reverse=True))


# simulate auction draft
def remove_player_from_pool(player_data: dict,
                            player_id: int):
    player_data.pop(player_id)


def nominate_player(players_data: dict,
                    positions: list[str],
                    n: int = 10):
    player_pool = {k: v for k, v in players_data.items() if v['position'] in positions}
    players = {k: player_pool[k] for k in list(player_pool)[:n]}
    probs = [v['value'] / sum(v['value'] for k, v in players.items()) for k, v in players.items()]
    return random.choices(list(players), probs)[0]


def appetites(players_data, can_draft, max_slots, draft_state, position):
    """
    Calculate each team's 'appetite' to draft the current player.
    position scarcity: player's value compared to rest of players in tier
    position scarcity: # players at position a team has compared to the league. fewer players vs league => higher scarcity
    roster scarcity: # of total players team has compared to league
    """
    # players_data = player_prices.copy()
    # position = nom_position
    appetites = {}
    total_appetite = 0
    position_scarcity = players_data[nom_id]['vor_tot'] / (sum(v['vor_tot'] for k, v in players_data.items() if (v['tier'] == players_data[nom_id]['tier']))+1) / 0.5
    for o in owners:
        if o in can_draft:
            aggression = draft_state[o]['aggression'] / sum(v['aggression'] for k,v in draft_state.items()) * position_scarcity

            tm_position_val = max_slots[position] / (draft_state[o][position] + 1)
            lg_position_val = (
                                    (max_slots[position] * (N_TEAMS - 1))  # league position slots, except current team
                                    / (sum(v[position] for k, v in draft_state.items() if k != o) + 1)  # total players drafted at position, except for current team
                            ) / (N_TEAMS - 1)  # average of league, except current team
            lineup_slot_scarcity = tm_position_val / lg_position_val

            try:
                pick_scarcity = pick - draft_picks[o][-1]['pick']
            except IndexError:
                pick_scarcity = pick - 1

            tm_roster_val = 15 - draft_state[o]['slots_left']
            lg_roster_val = (
                                    (pick - tm_roster_val)  # total picks made, except current team
                            ) / (N_TEAMS - 1)  # average of league, except current team
            roster_scarcity = lg_roster_val / (tm_roster_val + 1)

            tm_appetite = (lineup_slot_scarcity / (aggression + 1)) * (roster_scarcity + (pick_scarcity/10))
            appetites[o] = tm_appetite
            total_appetite += tm_appetite

    return {k: (v/total_appetite) for k, v in appetites.items()}


def inflation(remaining_prices: list,
              total_spent: int,
              budget: int,
              n_teams: int):
    return ((budget * n_teams) - total_spent) / sum(remaining_prices)


##### LOAD DATA #####
season = 2025
byes = get_byes(season)
price_data = calculate_prices(players_data=load_espn_data(season=season, byes=byes))
values = np.array([v['vor_tot'] for k, v in price_data.items()]).reshape(-1, 1)
gmcl = gm(n_components=10, covariance_type='full').fit(values)
gmcl.bic(values)
preds = gmcl.predict(values)
for i, (k, v) in enumerate(price_data.items()):
    price_data[k]['tier'] = preds[i]


##### SIMULATE AUCTION DRAFT #####
start = time.perf_counter()
n_sims = 100
sim = 1
all_draft_data = []
while sim <= n_sims:
    if sim % 1000 == 0:
        print(sim)
    # initiate draft data
    player_prices = copy.deepcopy(price_data)
    owners = ['Aaro', 'Adit', 'Aksh', 'Arju', 'Ayaz', 'Char', 'Faiz', 'Hirs', 'Nick', 'Varu']
    total_slots = sum(STARTERS) + N_FLEX + N_BENCH
    max_slots = {
        'QB': 2,
        'RB': 7,
        'WR': 8,
        'TE': 2,
        'DST': 1
    }  # realistic max slots, not ESPN max

    draft_picks = {o: [] for o in owners}
    draft_state = {
        o: {
            'aggression': random.choices([1,2,3], [0.2, 0.6, 0.2])[0],
            'funds_left': BUDGET,
            'slots_left': total_slots,
            'QB': 0,
            'RB': 0,
            'WR': 0,
            'TE': 0,
            'DST': 0
        } for o in owners
    }
    pick = 1
    total_spend = 0

    while pick <= (total_slots * N_TEAMS):

        # positions remaining to nominate
        positions_to_draft = []
        for o in owners:
            if draft_state[o]['slots_left'] > 0:
                for p in POSITIONS:
                    if draft_state[o][p] < max_slots[p]:
                        if p not in positions_to_draft:
                            positions_to_draft.append(p)

        # nominate a player and get stats
        nom_id = nominate_player(player_prices, positions_to_draft)
        nom_player = player_prices[nom_id]['name']
        nom_team = player_prices[nom_id]['team']
        nom_bye = player_prices[nom_id]['bye']
        nom_position = player_prices[nom_id]['position']
        nom_ppg = player_prices[nom_id]['ppg']
        nom_vor = player_prices[nom_id]['vor_tot']

        # get teams that have a slot available for player
        possible_teams = {k for k, v in draft_state.items() if v[nom_position] < max_slots[nom_position] and v['slots_left'] > 0}

        # get an initial bid amount
        team_factor = len(possible_teams) / len(owners)  # scale bid price to account for competition
        min_bid = player_prices[nom_id]['price'] * (0.2 + team_factor)
        max_bid = player_prices[nom_id]['value'] * (0.2 + team_factor)
        bid_amt = 1 if round(random.uniform(min_bid, max_bid)) <= 0 else round(random.uniform(min_bid, max_bid))

        # get which of possible teams can draft player at price and select a random team
        # team must have:
        #   $1 / roster spot remaining after drafting OR have enough funds to draft player as the last pick AND
        #   not need another position filled with final pick(s)
        can_draft = []
        while len(can_draft) == 0:
            for o in possible_teams:
                over_dppr = (draft_state[o]['funds_left'] - bid_amt) - (draft_state[o]['slots_left'] - 1) >= 0
                last_player_funds = (draft_state[o]['funds_left'] - bid_amt >= 0) and draft_state[o]['slots_left'] == 1
                needs_other_pos = len({k: v for k, v in draft_state[o].items() if k in POSITIONS and k != nom_position and v == 0}) / draft_state[o]['slots_left'] >= 1
                if (over_dppr or last_player_funds) and not needs_other_pos:
                    can_draft.append(o)

            if len(can_draft) == 0:
                bid_amt -= 1
                if bid_amt <= 0:
                    remove_player_from_pool(player_prices, nom_id)
                    break

        if nom_id not in player_prices:
            continue

        if bid_amt == 0:break
        player_appetites = appetites(player_prices, can_draft, max_slots, draft_state, nom_position)
        winning_team = random.choices(can_draft, [v for k, v in player_appetites.items()])[0]

        # update draft statuses
        # adjust remaining prices for inflation
        infl = inflation(remaining_prices = [v['price'] for k, v in player_prices.items()],
                         total_spent = total_spend,
                         budget = BUDGET,
                         n_teams = N_TEAMS)
        for k, v in player_prices.items():
            v['value'] *= infl
            v['price'] *= infl

        # update team draft dictionaries
        total_spend += bid_amt
        draft_picks[winning_team].append({
            'pick': pick,
            'winning_bid': bid_amt,
            'player_id': nom_id,
            'player': nom_player,
            'nfl_team': nom_team,
            'bye': nom_bye,
            'position': nom_position,
            'ppg': nom_ppg,
            'vor': nom_vor
        })
        draft_state[winning_team]['funds_left'] -= bid_amt
        draft_state[winning_team]['slots_left'] -= 1
        draft_state[winning_team][nom_position] += 1

        remove_player_from_pool(player_prices, nom_id)
        pick += 1

    all_draft_data.append(draft_picks)
    sim += 1
end = time.perf_counter()
elapsed = end-start


##### SIMULATE SEASON
def sim_injury(mean_games: dict,
               position: str):
    """
    :param position: position of the player
    :param mean_games: dictionary of mean games missed by position
    :return: the number of games missed by the player
    mean games missed by position comes from this study (adjusted by 1):
        https://www.profootballlogic.com/articles/nfl-injury-rate-analysis/
    """
    position = position.upper()
    if position != 'DST':
        lower, upper, scale = 0, 18, mean_games[position]
        x = stats.truncexpon(b=(upper - lower) / scale, loc=lower, scale=scale)
        games_missed = int(np.floor(x.rvs(1)[0]))

        if games_missed == 0:
            return []
        else:
            return list(np.sort(random.sample(range(1, upper), games_missed)))
    else:
        return []


def apply_weight(weights, position):
    """
    Applies weight to a player's score to simulate over/under performance compared to projections
    :param weights: mean and standard deviation of position to draw a weight and apply to total points scored
    :param position: the players position
    :return: randomly selected weight following a normal distribution, or 1 for DST.
    """
    position = position.upper()
    if position != 'DST':
        wt_mean = weights[position]['mean']
        wt_sd = weights[position]['sd']
        return random.normalvariate(mu=wt_mean, sigma=wt_sd)
    else:
        return 1


# load saved sim data
# with open('all_draft_data.pkl', 'rb') as f:
#     all_draft_data = pickle.load(f)


mean_gms_missed = {'QB': 2.1, 'RB': 2.9, 'WR': 2.2, 'TE': 1.6}
wts = {'QB': {'mean': 0.9667, 'sd': 0.1690},
       'RB': {'mean': 1.0407, 'sd': 0.3855},
       'WR': {'mean': 1.0267, 'sd': 0.2586},
       'TE': {'mean': 0.9795, 'sd': 0.2370}}

sim_injury(mean_gms_missed, 'rb')
apply_weight(wts, 'rb')


week = 9
for sim in range(n_sims):
    draft = all_draft_data[sim]
    for team, roster in draft.items():
        for player in roster:
            player['games_missed'] = sim_injury(mean_gms_missed, player['position'])
            player['ppg_wt'] = player['ppg'] * apply_weight(wts, player['position'])
            player['sd'] = player['ppg_wt'] * 0.2 if player['position'] == 'QB' else player['ppg_wt'] * 0.4
        test = [i for i in roster if week != i['bye'] and week not in i['games_missed']]












# Save all_draft_data to a Pickle file
# with open('all_draft_data.pkl', 'wb') as f:
#     pickle.dump(all_draft_data, f)






def scatter_plot(player, sims, x='pick', y='winning_bid'):
    df = sims.copy()
    df_plyr = df[df.player == player]
    plt.figure(figsize=(7, 7))
    plt.axvline(x=df_plyr[x].mean(), c='grey', dashes=(2, 2, 2, 2))
    plt.axhline(y=df_plyr[y].median(), c='grey', dashes=(2, 2, 2, 2))
    plt.scatter(df_plyr[x], df_plyr[y], s=5)
    plt.title(player)
    plt.xlabel(x)
    plt.ylabel(y)
    plt.show()
