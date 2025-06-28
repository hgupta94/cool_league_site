from scripts.api.DataLoader import DataLoader
from scripts.utils.constants import POSITION_MAP, NFL_TEAM_MAP

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.colors as colors
import requests
import copy
import random
import math
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
STARTERS = [1, 2, 3, 1, 1]
FLEX_POSITIONS = ['RB', 'WR']
N_FLEX = 1
N_PLAYOFFS = 6


def flatten_list(lst: list) -> list:
    """
    Flattens a list of lists into a single list
    Only works for 2D lists
    """
    return [
        x
        for xs in lst
        for x in xs
    ]


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


# def get_player_scores(season: int):
#     data = DataLoader(season)
#     players = data.players_info()
#
#     players_dict = {}
#     for week in range(1, 19):
#         week_data = data.load_week(week=week)
#     for player in players['players']:
#         full_name = player['player']['fullName']
#         team = NFL_TEAM_MAP[player['player']['proTeamId']]
#         if team == 'None':
#             continue
#
#         total_points = 0
#         for stat in player['player']['stats']:
#             if (stat['seasonId'] == season) and (stat['statSourceId'] == 1) and (stat['statSplitTypeId'] == 0):
#                 projection_total = stat['appliedTotal']
#                 projection_ppg = stat['appliedAverage']
#         players_dict[player['id']] = {
#             'name': full_name,
#             'position': position,
#             'team': team,
#             'bye': bye,
#             'rank_ov': pl_rank_ov,
#             'projection_total': projection_total,
#             'ppg': projection_ppg
#         }
#     players_sorted = dict(sorted(players_dict.items(), key=lambda x: x[1]['projection_total'], reverse=True))
#
#     rank_pos = {
#         'QB': 1,
#         'RB': 1,
#         'WR': 1,
#         'TE': 1,
#         'DST': 1
#     }
#     for _, player in players_sorted.items():
#         # get position ranks
#         player['rank_pos'] = rank_pos[player['position']]
#         rank_pos[player['position']] += 1
#     return {k: v for k, v in players_sorted.items() if v['ppg'] > 1}



def calculate_prices(
        players_data: dict,
        budget: int = 200,
        min_bid: int = 1,
        n_teams: int = 10,
        n_bench: int = 6,
        positions: list[str] = ['QB', 'RB', 'WR', 'TE', 'DST'],
        flex_positions: list[str] = ['RB', 'WR'],
        n_flex: int = 1,
        starters: list[int] = [1, 2, 3, 1, 1]
):
    backups = [0.5/n_bench, 2.5/n_bench, 2.5/n_bench, 0.5/n_bench, 0]  # number of bench spots occupied by position
    total_dollars = budget * n_teams
    pos_spend = {'QB': 0.0892,
                 'RB': 0.3820,
                 'WR': 0.4586,
                 'TE': 0.0632,
                 'DST': 0.0070}

    # get replacement player projected points
    replacement_pts_starters = {p: 0 for p in POSITIONS}
    replacement_pts_bench = {p: 0 for p in POSITIONS}
    for p, s, b in zip(positions, starters, backups):
        # calculate number of players drafted by position
        if p in flex_positions:
            n_starters_drafted = (s + (n_flex / len(flex_positions))) * n_teams
            n_bench_drafted = n_bench * b * n_teams
            n_total_drafted = n_starters_drafted + n_bench_drafted
            replacement_rank_starters = n_starters_drafted + 1
        else:
            n_total_drafted = (s * n_teams) + (n_bench * b * n_teams)
            replacement_rank_starters = s * n_teams + 1
        replacement_rank_bench = n_total_drafted + 1
        replacement_starters_fpts = [
             v['projection_total'] for _, v
             in players_data.items()
             if (v['position'] == p)
             and (v['rank_pos'] == replacement_rank_starters)
        ][0]
        replacement_pts_starters[p] = replacement_starters_fpts
        replacement_bench_fpts = [
             v['projection_total'] for _, v
             in players_data.items()
             if (v['position'] == p)
             and (v['rank_pos'] == replacement_rank_bench)
        ][0]
        replacement_pts_bench[p] = replacement_bench_fpts

    # calculate if player is a starter, bench, or undrafted
    for _, player in players_data.items():
        player['player_type'] = (
            'starter' if player['projection_total'] > replacement_pts_starters[player['position']]
            else 'bench' if player['projection_total'] > replacement_pts_bench[player['position']]
            else 'undrafted'
        )

        # value over replacement
        player['vor_st'] = 0 if (player['projection_total'] - replacement_pts_starters[player['position']]) < 0 else (player['projection_total'] - replacement_pts_starters[player['position']])
        player['vor_bn'] = 0 if (player['projection_total'] - replacement_pts_bench[player['position']]) < 0 else (player['projection_total'] - replacement_pts_bench[player['position']])
        player['vor'] = player['vor_st'] + player['vor_bn']


    for _, player in players_data.items():
        dpv = (  # dollar per vor
                (budget * n_teams) / sum(v['vor'] for k, v in players_data.items() if v['player_type'] == 'starter' and v['position'] == player['position'])
        )
        player['value'] = (player['vor'] * dpv * pos_spend[player['position']]) + min_bid


    for _, player in players_data.items():
        player['price'] = player['value'] / (sum(v['value'] for k, v in players_data.items()) / total_dollars)

    remove_keys = ['vor_st', 'vor_bn']
    for k in remove_keys:
        for _, p in players_data.items():
            p.pop(k, None)
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


def appetites(can_draft, max_slots, draft_state, position, pick, draft_data):
    """
    Calculate each team's 'appetite' to draft the current player.
    position scarcity: player's value compared to rest of players in tier
    position scarcity: # players at position a team has compared to the league. fewer players vs league => higher scarcity
    roster scarcity: # of total players team has compared to league
    """
    # players_data = player_pool.copy()
    # position = nom_position
    tm_appetites = {}
    total_appetite = 0
    for o in can_draft:
        aggression = draft_state[o]['aggression']# / (sum(v['aggression'] for k,v in draft_state.items()) / 10)

        tm_position_val = max_slots[position] / (draft_state[o][position] + 1)
        lg_position_val = (
                                (max_slots[position] * (N_TEAMS - 1))  # league position slots, except current team
                                / (sum(v[position] for k, v in draft_state.items() if k != o) + 1)  # total players drafted at position, except for current team
                        ) / (N_TEAMS - 1)  # average of league, except current team
        lineup_slot_scarcity = tm_position_val / lg_position_val

        try:
            pick_scarcity = pick - draft_data[o][-1]['pick']
        except IndexError:
            pick_scarcity = pick

        tm_roster_val = 15 - draft_state[o]['slots_left']
        lg_roster_val = (
                                (pick - tm_roster_val)  # total picks made, except current team
                        ) / (N_TEAMS - 1)  # average of league, except current team
        roster_scarcity = lg_roster_val / (tm_roster_val + 1)

        tm_appetite = ((lineup_slot_scarcity * roster_scarcity) + (pick_scarcity/10)) / aggression
        tm_appetites[o] = tm_appetite
        total_appetite += tm_appetite

    return {k: (v/total_appetite) for k, v in tm_appetites.items()}


def inflation(remaining_prices: list,
              total_spent: int,
              budget: int,
              n_teams: int):
    return ((budget * n_teams) - total_spent) / sum(remaining_prices)


def sim_injury(mean_games: dict,
               position: str):
    """
    :param position: position of the player
    :param mean_games: dictionary of mean games missed by position
    :return: the number of games missed by the player
    mean games missed by position comes from this study (adjusted by 1 to account for championship game in week 17):
        https://www.profootballlogic.com/articles/nfl-injury-rate-analysis/
    """
    position = position.upper()
    if position != 'DST':
        lower, upper, scale = 0, 18, mean_games[position]
        x = stats.truncexpon(b=(upper - lower) / scale, loc=lower, scale=scale)
        games_missed = math.floor(x.rvs(1)[0])

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
        # wt_min = weights[position]['mean'] - weights[position]['sd']
        # wt_max = weights[position]['mean'] + weights[position]['sd']
        return random.normalvariate(mu=weights[position]['mean'], sigma=weights[position]['sd'])
    else:
        return 1


def get_replacement_player_id(position):
    if position.upper() in POSITIONS:
        return next(iter({k: v for k, v in price_data.items() if v['position'] == position.upper() and v['player_type'] == 'undrafted'}))
    if position.upper() == 'FLEX':
        return next(iter({k: v for k, v in price_data.items() if v['position'] in FLEX_POSITIONS and v['player_type'] == 'undrafted'}))
    else:
        raise ValueError(f'{position.upper()} not valid. Position should be in {POSITIONS}')


def get_lineup(roster: list[dict], week):
    starters = []
    active_players = [i for i in roster if (week != i['bye']) and (week not in i['games_missed'])]
    for pos, st in zip(POSITIONS + ['FLEX'], STARTERS + [1]):
        if pos != 'FLEX':
            pos_players = sorted([p for p in active_players if p['position'] == pos], key=lambda x: x['ppg'], reverse=True)
            if len(pos_players) >= st:
                starters.append(pos_players[0:st])
            else:
                # check if replacement player(s) are needed
                players_needed = st - len(pos_players)
                starters.append([price_data[get_replacement_player_id(pos)] for _ in range(players_needed)])
        else:
            # get flex starter(s)
            starter_ids = [x['player_id'] for x
                           in flatten_list(starters)
                           if 'player_id' in x]  # ignore these players from flex consideration
            flex_players = []
            for fl_pos in FLEX_POSITIONS:
                fl = (
                    [fl for fl in active_players if fl['position'] == fl_pos and fl['player_id'] not in starter_ids]
                )
                if fl:
                    flex_players.append(fl)
            if len(flatten_list(flex_players)) > 0:
                # if there are enough flex players, choose random player
                flex_sorted = sorted(flatten_list(flex_players), key=lambda x: x['ppg'], reverse=True)
                starters.append(random.choices(flex_sorted, [v['ppg'] if v['ppg'] > 0 else 0.1 for v in flex_sorted], k=1))
            else:
                starters.append([price_data[get_replacement_player_id(position='FLEX')] for _ in range(N_FLEX)])
    return flatten_list(starters)



##### LOAD DATA #####
season = 2025
byes = get_byes(season)
price_data = calculate_prices(players_data=load_espn_data(season=season, byes=byes))
values = np.array([v['vor'] for k, v in price_data.items()]).reshape(-1, 1)
gmcl = gm(n_components=10, covariance_type='full').fit(values)
gmcl.bic(values)
preds = gmcl.predict(values)
for i, (k, v) in enumerate(price_data.items()):
    price_data[k]['tier'] = preds[i]

mean_gms_missed = {'QB': 2.1, 'RB': 2.9, 'WR': 2.2, 'TE': 1.6}
wts = {'QB': {'mean': 0.9667, 'sd': 0.1666}, #'sd': 0.1690},
       'RB': {'mean': 1.0407, 'sd': 0.1666}, #'sd': 0.3855},
       'WR': {'mean': 1.0267, 'sd': 0.1666}, #'sd': 0.2586},
       'TE': {'mean': 0.9795, 'sd': 0.1666}} #'sd': 0.2370}}


##### START SIMULATION #####
def run_simulation(n_sims):
    owners = ['Aaro', 'Adit', 'Aksh', 'Arju', 'Ayaz', 'Char', 'Faiz', 'Hirs', 'Nick', 'Varu']
    total_slots = sum(STARTERS) + N_FLEX + N_BENCH
    starters = {p: s for p, s in zip(POSITIONS, STARTERS)}
    max_slots = {  # realistic max number of players, not ESPN max
        'QB': 2,
        'RB': 7,
        'WR': 8,
        'TE': 2,
        'DST': 2
    }
    final_results = {  # initialize final output data
        s: {
            'draft_data': {},
            'results': {}
        } for s in range(n_sims)
    }
    start = time.perf_counter()
    for sim in range(n_sims):
        if sim % 1000 == 0:
            print(sim)

        # initialize draft data
        player_pool = copy.deepcopy(price_data)
        draft_picks = {o: [] for o in owners}
        draft_state = {
            o: {
                'aggression': random.choices([1, 2, 3], [0.2, 0.6, 0.2])[0],  # 1 = most aggressive
                'funds_left': BUDGET,
                'slots_left': total_slots,
                'max_bid': BUDGET - (total_slots - 1),
                'QB': 0,
                'RB': 0,
                'WR': 0,
                'TE': 0,
                'DST': 0
            } for o in owners
        }
        pick = 1
        total_spend = 0

        ### SIMULATE AUCTION DRAFT ###
        while pick <= (total_slots * N_TEAMS):
            # positions remaining to nominate
            # helpful when last few picks only require QB/TE/DST
            positions_to_draft = []
            for o in owners:
                if draft_state[o]['slots_left'] > 0:
                    for p in POSITIONS:
                        if draft_state[o][p] < max_slots[p]:
                            if p not in positions_to_draft:
                                positions_to_draft.append(p)

            # nominate a player and get data
            nom_id = nominate_player(player_pool, positions_to_draft)
            nom_player = player_pool[nom_id]['name']
            nom_team = player_pool[nom_id]['team']
            nom_bye = player_pool[nom_id]['bye']
            nom_position = player_pool[nom_id]['position']
            nom_ppg = player_pool[nom_id]['ppg']
            nom_vor = player_pool[nom_id]['vor']

            # get teams that have a slot available for player
            possible_teams = {k for k, v in draft_state.items() if v[nom_position] < max_slots[nom_position] and v['slots_left'] > 0}

            # get an initial bid amount
            # team_factor = len(possible_teams) / len(owners)  # scale bid price to account for competition
            min_price = player_pool[nom_id]['price'] - (0.1 * player_pool[nom_id]['price'])
            max_price = player_pool[nom_id]['value'] + (0.3 * player_pool[nom_id]['value'])
            avg_price = (player_pool[nom_id]['price'] + player_pool[nom_id]['value']) / 2
            bid_init = math.ceil(random.triangular(low=min_price, high=max_price, mode=avg_price))  # get initial price based on player data
            max_bid_amt = sorted([v['max_bid'] for k, v in draft_state.items()])[-2] + 1  # winning team can only bid up to team with the second-highest max_bid + $1
            bid_amt = 1 if bid_init < 1 else (bid_init if max_bid_amt > bid_init else max_bid_amt)

            # get which of possible teams can draft player at price and select a random team
            # the team must have:
            #   >=$1 per player spot remaining (dppr) after drafting OR have enough funds to draft player as the last pick (not go negative)
            #   AND not need another position filled with final pick(s)
            can_draft = []
            while len(can_draft) == 0:
                for o in possible_teams:
                    over_dppr = (draft_state[o]['funds_left'] - bid_amt) - (draft_state[o]['slots_left'] - 1) >= 0
                    last_player_funds = (draft_state[o]['funds_left'] - bid_amt >= 0) and draft_state[o]['slots_left'] == 1
                    needs_other_pos = len({k: v for k, v in draft_state[o].items() if k in POSITIONS and k != nom_position and v == 0}) / draft_state[o]['slots_left'] >= 1
                    if (over_dppr or last_player_funds) and not needs_other_pos:
                        can_draft.append(o)

                # if no team can draft player, reduce bid_amt by $1 and try again
                if len(can_draft) == 0:
                    bid_amt -= 1

                    # if bid_amt reaches 0, drop player and break out of while loop
                    if bid_amt <= 0:
                        remove_player_from_pool(player_pool, nom_id)
                        break

            if nom_id not in player_pool:
                # if nominated player was dropped during while loop, restart nomination
                continue

            team_appetites = appetites(can_draft, max_slots, draft_state, nom_position, pick, draft_picks)  # assign weight to remaining teams
            winning_team = random.choices(can_draft, [v for k, v in team_appetites.items()])[0]

            # update draft statuses
            # adjust remaining prices for inflation
            total_spend += bid_amt
            infl = inflation(remaining_prices = [v['price'] for k, v in player_pool.items()],
                             total_spent = total_spend,
                             budget = BUDGET,
                             n_teams = N_TEAMS)
            for k, v in player_pool.items():
                v['value'] *= infl
                v['price'] *= infl

            draft_picks[winning_team].append({  # assign player to winning team
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
            draft_state[winning_team]['max_bid'] -= (bid_amt - 1)  # -$1 for filling current spot
            draft_state[winning_team][nom_position] += 1

            remove_player_from_pool(player_pool, nom_id)
            pick += 1

        final_results[sim]['draft_data'] = draft_picks

        ### SIM SEASON ###
        for team, roster in draft_picks.items():
            # calculate lineup slots - highest bid player at each position is pos1
            slot_init = {p: 0 for p in POSITIONS + ['FLEX']}
            roster = sorted(roster, key=lambda x: (x['winning_bid'], x['vor']), reverse=True)
            for player in roster:
                pos = player['position']
                if slot_init[pos] < starters[pos]:
                    slot_init[pos] += 1
                    player['slot'] = pos # f'{pos}{slot_init[pos]}'
                elif pos in FLEX_POSITIONS and slot_init[pos] == starters[pos] and slot_init['FLEX'] == 0:
                    player['slot'] = 'FLEX'
                    slot_init['FLEX'] += 1
                else:
                    player['slot'] = 'BENCH'

                # initialize games missed and new ppg for current "season"
                player['games_missed'] = sim_injury(mean_gms_missed, player['position'])
                player['ppg'] = player['ppg'] * apply_weight(wts, player['position'])

        season_results = {
            o: {
                'wins': 0,
                'points': 0,
                'playoffs': 0,
                'finals': 0,
                'champ': 0
            }
            for o in owners
        }
        for week in range(1, 15):  # weeks 1 to end of regular season
            scores = {}
            for team, roster in draft_picks.items():
                # TODO: add check for starters vs replacement player
                lineup = get_lineup(roster=roster, week=week)
                lineup = [dict(l, **{'sd': l['ppg'] * 0.15 if l['position'] == 'QB' else l['ppg'] * 0.3}) for l in lineup]
                points = sum(random.normalvariate(s['ppg'], s['sd']) for s in lineup)
                scores[team] = points
            median = np.median([s for s in scores.values()])
            for team, score in scores.items():
                season_results[team]['points'] += score
                if score > median:  # team scored in the top half of league
                    season_results[team]['wins'] += 1

        # SIM PLAYOFFS #
        # quarterfinals
        p_teams = [t[0] for t in sorted(season_results.items(), key=lambda x: (x[1]['wins'], x[1]['points']), reverse=True)][0:N_PLAYOFFS]
        for t in p_teams:
            season_results[t]['playoffs'] += 1
        sf_teams = p_teams[0:2]  # top two teams get by and move onto semifinals
        qf_teams = [t for t in p_teams if t not in sf_teams]
        qf_scores = {}
        for team, roster in {k: v for k, v in draft_picks.items() if k in qf_teams}.items():
            qf_lineup = get_lineup(roster=roster, week=15)
            qf_lineup = [dict(l, **{'sd': l['ppg'] * 0.2 if l['position'] == 'QB' else l['ppg'] * 0.4}) for l in qf_lineup]
            qf_points = sum(random.normalvariate(s['ppg'], s['sd']) for s in qf_lineup)
            qf_scores[team] = qf_points
        qf_median = np.median([s for s in qf_scores.values()])
        for team, score in qf_scores.items():
            if score > qf_median:  # team scored in the top half of league
                sf_teams.extend([team])

        # semifinals
        sf_scores = {}
        finals_teams = []
        for team, roster in {k: v for k, v in draft_picks.items() if k in sf_teams}.items():
            sf_lineup = get_lineup(roster=roster, week=16)
            sf_lineup = [dict(l, **{'sd': l['ppg'] * 0.2 if l['position'] == 'QB' else l['ppg'] * 0.4}) for l in sf_lineup]
            sf_points = sum(random.normalvariate(s['ppg'], s['sd']) for s in sf_lineup)
            sf_scores[team] = sf_points
        sf_median = np.median([s for s in sf_scores.values()])
        for team, score in sf_scores.items():
            if score > sf_median:  # team scored in the top half of league
                finals_teams.extend([team])
                season_results[team]['finals'] += 1

        # finals
        finals_scores = {}
        champion = []
        for team, roster in {k: v for k, v in draft_picks.items() if k in finals_teams}.items():
            finals_lineup = get_lineup(roster=roster, week=16)
            finals_lineup = [dict(l, **{'sd': l['ppg'] * 0.2 if l['position'] == 'QB' else l['ppg'] * 0.4}) for l in finals_lineup]
            finals_points = sum(random.normalvariate(s['ppg'], s['sd']) for s in finals_lineup)
            finals_scores[team] = finals_points
        finals_median = np.median([s for s in finals_scores.values()])
        for team, score in finals_scores.items():
            if score > finals_median:  # team scored in the top half of league
                champion.extend([team])
                season_results[team]['champ'] += 1

        final_results[sim]['results'] = season_results

    end = time.perf_counter()
    elapsed = end-start
    print(f'{round(elapsed/60, 2)} minutes')
    return final_results

results = run_simulation(n_sims=100_000)

# Convert draft data to df
s1 = time.perf_counter()
draft_records = [
    {**player, 'team': team, 'sim': sim + 1}
    for sim, data in results.items()
    for team, roster in data['draft_data'].items()
    for player in roster
]
all_drafts = pd.DataFrame.from_records(draft_records)
all_drafts['games_missed'] = all_drafts.games_missed.apply(lambda x: len(x))
e1 = time.perf_counter()
print((e1-s1)/60, 'minutes for all_drafts')

# Convert results dictionary to a DataFrame
s2 = time.perf_counter()
all_results = pd.DataFrame([
    {**team_data, 'team': team, 'sim': sim + 1}
    for sim, sim_data in results.items()
    for team, team_data in sim_data['results'].items()
])
e2 = time.perf_counter()
print(round((e2-s2)/60, 2), 'minutes for all_results')



all_results.sort_values(['champ', 'points'], ascending=[False, True]).groupby('sim').points.sum().mean()


all_results.hist('points', bins=100)
plt.show()

z = (1420 - all_results.points.mean()) / all_results.points.std()



all_drafts.games_missed.plot.hist(bins=17)
plt.show()

# Save all_draft_data to a Pickle file
# with open('auction/all_drafts.pkl', 'wb') as f:
#     pickle.dump(all_drafts, f)
# with open('auction/all_results.pkl', 'wb') as f:
#     pickle.dump(all_results, f)

# load saved sim data
# with open('all_drafts.pkl', 'rb') as f:
#     all_drafts = pickle.load(f)
# with open('all_results.pkl', 'rb') as f:
#     all_results = pickle.load(f)


def scatter_plot(player, sims_df, x='pick', y='winning_bid'):
    df_plyr = sims_df[sims_df.player == player]
    plt.figure(figsize=(7, 7))
    plt.axvline(x=df_plyr[x].mean(), c='grey', dashes=(2, 2, 2, 2))
    plt.axhline(y=df_plyr[y].median(), c='grey', dashes=(2, 2, 2, 2))
    plt.scatter(df_plyr[x], df_plyr[y], s=5)
    plt.title(player)
    plt.xlabel(x)
    plt.ylabel(y)
    plt.show()
scatter_plot('Ja\'Marr Chase', all_drafts)


by_slot_type = all_drafts.groupby(['sim', 'team', 'slot']).winning_bid.sum().reset_index()
by_slot_type['p_alloc'] = by_slot_type.winning_bid / 200
by_slot_type_pivot = by_slot_type.pivot(index=['sim', 'team'], columns='slot', values='p_alloc').reset_index()
by_slot_type_pivot['STARTERS'] = by_slot_type_pivot.QB +  by_slot_type_pivot.RB +  by_slot_type_pivot.WR +  by_slot_type_pivot.TE +  by_slot_type_pivot.DST +  + by_slot_type_pivot.FLEX

by_position = all_drafts.groupby(['sim', 'team', 'position']).winning_bid.sum().reset_index()
by_position['p_alloc'] = by_position.winning_bid / 200
by_position_pivot = by_position.pivot(index=['sim', 'team'], columns='position', values='p_alloc').reset_index()

spend_cats = pd.merge(by_slot_type_pivot, by_position_pivot, on=['sim', 'team'], suffixes=['', '_pos'])
total_spend = all_drafts.groupby(['sim', 'team']).winning_bid.sum().reset_index().rename(columns={'winning_bid': 'TOTAL_SPEND'})
spend_cats = pd.merge(total_spend, spend_cats, on=['sim', 'team'])

combined_results = pd.merge(spend_cats, all_results, on=['sim', 'team'])


df = combined_results.set_index(['sim', 'team'])
df[['points', 'TOTAL_SPEND']].corr()
df[['wins', 'BENCH']].boxplot(by='wins')
plt.show()



bins_dict = {
    'QB': {
        'bins': [0, 5, 10, 20, 30, 40, 200],
        'format': ['<=5', '6-10', '11-20', '21-30', '31-40', '41+']
    },
    'RB': {
        'bins': [0, 40, 60, 80, 100, 200],
        'format': ['<=40', '41-60', '61-80', '81-100', '101+']
    },
    'WR': {
        'bins': [0, 40, 60, 80, 100, 200],
        'format': ['<=40', '41-60', '61-80', '81-100', '101+']
    },
    'TE': {
        'bins': [0, 5, 10, 20, 40, 200],
        'format': ['<=5', '6-10', '11-20', '21-40', '41+']
    },
    'STARTERS': {
        'bins': [0, 150, 160, 170, 180, 190, 200],
        'format': ['<=150', '151-160', '161-170', '171-180', '181-190', '191-200']
    },
    'FLEX': {
        'bins': [0, 10, 20, 30, 200],
        'format': ['<=10', '11-20', '21-30', '31+']
    }
}


def get_data(data, col):
    from functools import reduce
    col_upper = col.upper()

    df = data.copy()
    df[col+'_spend'] = pd.cut(df[col_upper]*200, bins=bins_dict[col_upper]['bins'])
    playoffs_over_avg = ((df.groupby(col+'_spend').playoffs.mean() / df.playoffs.mean()) - 1)
    finals_over_avg = ((df.groupby(col+'_spend').finals.mean() / df.finals.mean()) - 1)
    champ_over_avg = ((df.groupby(col+'_spend').champ.mean() / df.champ.mean()) - 1)
    points_over_avg = (df.groupby(col+'_spend').points.mean() - df.points.mean()) / 14

    dfs = [playoffs_over_avg, finals_over_avg, champ_over_avg, points_over_avg]
    return reduce(lambda left, right: pd.merge(left, right, left_index=True, right_index=True), dfs)


def plot_position(position: str, y_col: str):
    pos_upper = position.upper()

    title = f'{position.upper()} by PPG Added'
    data = get_data(df, position).reset_index()
    data['bins_str'] = data[position + '_spend'].astype('str')
    xlab = 'Total Spend'
    ylab = 'Change in PPG'

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.bar(data.bins_str, data[y_col])
    ax.set_axisbelow(True)
    # ax.yaxis.grid(c='lightgrey')
    plt.axhline(y=0, c='black', linewidth=0.75)
    ax.set_xticklabels(bins_dict[pos_upper]['format'], rotation=15)
    plt.yticks(np.arange(-2, 2, 0.5))
    # plt.yticks(np.arange(-0.25, 0.25, 0.1))
    # ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1))
    plt.title(title)
    plt.xlabel(xlab)
    plt.ylabel(ylab)
    # plt.savefig(file, bbox_inches='tight')
    plt.show()

plot_position(position='qb', y_col='points')
plot_position(position='rb', y_col='points')
plot_position(position='wr', y_col='points')
plot_position(position='te', y_col='points')
plot_position(position='flex', y_col='points')
plot_position(position='starters', y_col='points')
plot_position(position='bench', y_col='points')



def plot_spend_vs_median(df: pd.DataFrame = combined_results.copy()):
    df['st_vs_med'] = df.groupby('sim')['STARTERS'].transform(lambda x: x - x.median())
    df['score_diff'] = df.groupby('sim').points.transform(lambda x: x - x.mean()) / 14
    X_data = np.array(df.st_vs_med)
    Y_data = np.array(df.score_diff) / 14
    a, b, c = np.polyfit(X_data, Y_data, 2)

    X_fit = np.linspace(min(X_data), max(X_data), 1000)
    a, b, c = np.polyfit(X_data, Y_data, 2)
    f = lambda x: (a * (x ** 2)) + (b * x) + c
    Y_fit = f(X_fit)

    fig, ax = plt.subplots()
    ax.axhline(y=0, c='lightgrey', zorder=1)
    ax.plot(X_fit, Y_fit, color='r', alpha=0.5, zorder=3)
    ax.scatter(X_data, Y_data, s=4, color='lightgrey', zorder=2)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(xmax=1))
    plt.title('Team Starter Spend vs League Median')
    plt.xlabel('Difference from League Median')
    plt.ylabel('PPG Difference')
    plt.show()

plot_spend_vs_median()

def spend_variation(col, df: pd.DataFrame = combined_results.copy()):
    X = df[col]*200
    Y = (df.points - df.points.median()) / 14
    norm = colors.TwoSlopeNorm(vcenter=0)
    fig, ax = plt.subplots()
    ax.scatter(x=X, y=Y, s=4, c=Y, norm=norm, cmap='coolwarm')
    ax.axhline(y=0, linestyle='dashed', linewidth=1, c='#B5B5B5')
    ax.xaxis.set_major_formatter('${x:1.0f}')
    plt.title(F'Variation in PPG by {col} Spend')
    plt.xlabel('Starter Spend')
    plt.ylabel('PPG Added')
    plt.show()


spend_variation('QB')
spend_variation('RB')
spend_variation('WR')
spend_variation('TE')
spend_variation('DST')
spend_variation('STARTERS')
spend_variation('BENCH')
