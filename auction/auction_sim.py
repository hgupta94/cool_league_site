from scripts.api.dataloader import DataLoader
from scripts.api.settings import LeagueSettings, RosterSettings, TeamSettings
from scripts.utils.constants import NFL_TEAM_MAP_ESPN, DEFAULT_POSITION_MAP_ESPN

import requests
import copy
import random
import math
import time
import pickle

from sklearn.mixture import GaussianMixture as gm
import scipy.stats as stats
import pandas as pd
import numpy as np

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.colors as colors


dataloader = DataLoader(year=2025)
settings = dataloader.settings()
ls = LeagueSettings(dataloader=dataloader)
rs = RosterSettings(dataloader=dataloader)
ts = TeamSettings(dataloader=dataloader)

STARTER_ALLOCATION= 0.8
BUDGET= settings['settings']['draftSettings']['auctionBudget'] or 200
MIN_BID= 1
N_TEAMS= ls.league_size
N_BENCH= next(v for k, v in rs.roster_limits.items() if k == 20)
POSITIONS= rs.positions
STARTERS= {k: v for k, v in rs.lineup_position_limits.items() if k < 20}
FLEX_POSITIONS= [2, 4, 6]
N_FLEX= rs.lineup_position_limits[23]
N_PLAYOFFS= ls.playoff_teams
AVAIL_SPEND = (BUDGET - (sum(STARTERS.values()) + N_BENCH + N_FLEX)) * N_TEAMS

auction_settings = {
    'STARTER_ALLOCATION': STARTER_ALLOCATION,
    'BUDGET': BUDGET,
    'AVAIL_SPEND': AVAIL_SPEND,
    'MIN_BID': MIN_BID,
    'N_TEAMS': N_TEAMS,
    'N_BENCH': N_BENCH,
    'POSITIONS': POSITIONS,
    'STARTERS': STARTERS,
    'FLEX_POSITIONS': FLEX_POSITIONS,
    'N_FLEX': N_FLEX,
    'N_PLAYOFFS': N_PLAYOFFS
}


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


def _get_byes(season: int = ls.season):
    url = f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{season}?view=proTeamSchedules_wl'
    r = requests.get(url)
    d = r.json()

    byes_dict = {}
    for tm in d['settings']['proTeams']:
        byes_dict[tm['abbrev'].upper()] = tm['byeWeek']

    return byes_dict


def load_espn_data(dataloader: DataLoader):
    season = ls.season
    players = dataloader.players_info()
    byes = _get_byes(season=season)

    players_dict = {}
    rank_ov = 1
    for player in players['players']:
        full_name = player['player']['fullName']
        team = NFL_TEAM_MAP_ESPN[player['player']['proTeamId']]
        if team == 'None':
            continue
        bye = byes[team]
        pl_rank_ov = rank_ov
        rank_ov +=1
        
        try:
            position = DEFAULT_POSITION_MAP_ESPN[player['player']['defaultPositionId']]
        except KeyError:
            continue

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
    for _, plr in players_sorted.items():
        # get position ranks
        plr['rank_pos'] = rank_pos[plr['position']]
        rank_pos[plr['position']] += 1
    return {k: v for k, v in players_sorted.items() if v['ppg'] > 1}


def calculate_prices(
        players_data: dict,
        auction_settings: dict,
):
    budget = auction_settings['BUDGET']
    min_bid = auction_settings['MIN_BID']
    avail_spend = auction_settings['AVAIL_SPEND']
    n_teams = auction_settings['N_TEAMS']
    n_bench = auction_settings['N_BENCH']
    positions = tuple(auction_settings['POSITIONS'])
    starters = auction_settings['STARTERS']
    flex_positions = auction_settings['FLEX_POSITIONS']
    n_flex = auction_settings['N_FLEX']

    total_dollars = budget * n_teams
    flex = {
        0: 0,
        2: 0.6005,
        4: 0.0314,
        6: 0.3681,
        16: 0
    }
    backups = {
        0: n_bench * 0.1,
        2: n_bench * .375,
        4: n_bench * .375,
        6: n_bench * 0.1,
        16: n_bench * 0.05,
    }
    spend_by_pos = {  # avg of 2022-2025 drafts
        0:  0.0777,
        2:  0.4113,
        4:  0.4400,
        6:  0.0636,
        16: 0.0074
    }
    draft_by_pos = {  # % of roster spots 2022-2025
        0:  0.1032,
        2:  0.3381,
        4:  0.3952,
        6:  0.0937,
        16: 0.0698
    }
    exp = {
        0: 1.25,
        2: 1.5,
        4: 1.5,
        6: 1.25,
        16: 1
    }

    # get replacement player projected points
    band = 3
    replacement_pts = {p: 0 for p in positions}
    for pos in positions:
        # calculate number of players drafted by position
        n_total_drafted = draft_by_pos[pos] * n_teams * (sum(rs.lineup_position_limits.values()) - 1)
        replacement_rank = int(n_total_drafted) + 1  # ceiling
        replacement_fpts = sum(
             v['projection_total'] for _, v
             in players_data.items()
             if (v['position'] == auction_settings['POSITIONS'][pos])
             and (v['rank_pos'] in list(range(replacement_rank, replacement_rank + band)))
        ) / band
        replacement_pts[pos] = replacement_fpts

    # calculate if player is a starter, bench, or undrafted
    position_to_id = {
        str(name).upper().strip(): pid
        for pid, name in auction_settings['POSITIONS'].items()
    }
    for _, player in players_data.items():
        pos = position_to_id[player['position']]
        player['vor'] = max(0.0, player['projection_total'] - replacement_pts[pos])

    total_vor = sum(v['vor'] for _, v in players_data.items())
    pos_vor = {}
    pos_vor_adj = {}
    pos_share = {}
    pos_dollars = {}
    for pos in positions:
        x = {k: v for k, v in players_data.items() if position_to_id[v['position']] == pos}
        vor = sum(xx['vor'] for xx in x.values())
        vor_adj = sum(xx['vor'] ** exp[pos] for xx in x.values())
        pos_vor[pos] = vor
        pos_vor_adj[pos] = vor_adj
        pos_share[pos] = vor / total_vor
        pos_dollars[pos] = vor / total_vor * avail_spend

    for _, player in players_data.items():
        pos = position_to_id[player['position']]
        player['price'] = (player['vor'] ** exp[position_to_id[player['position']]]) / pos_vor_adj[pos] * pos_dollars[pos] + 1

    return dict(sorted(players_data.items(), key=lambda x: x[1]['price'], reverse=True))


# simulate auction draft
def remove_player_from_pool(player_data: dict,
                            player_id: int):
    player_data.pop(player_id)


def nominate_player(players_data: dict,
                    positions: list[str],
                    n: int = 10):
    id_pos_map = {
        0: 'QB',
        2: 'RB',
        4: 'WR',
        6: 'TE',
        16: 'DST',
        'QB': 0,
        'RB': 2,
        'WR': 4,
        'TE': 6,
        'DST': 16,
    }
    player_pool = {k: v for k, v in players_data.items() if id_pos_map[v['position']] in positions}
    players = {k: player_pool[k] for k in list(player_pool)[:n]}
    probs = [v['vor'] / sum(v['vor'] for k, v in players.items()) for k, v in players.items()]
    return random.choices(list(players), probs)[0]


def appetite(team, max_slots, draft_state, position_id, pick, draft_data):
    """
    Calculate each team's 'appetite' to draft the current player.
    position scarcity: player's value compared to rest of players in tier
    position scarcity: # players at position a team has compared to the league. fewer players vs league => higher scarcity
    roster scarcity: # of total players team has compared to league
    """
    n_picks = (sum(STARTERS.values()) + N_BENCH + N_FLEX) * N_TEAMS
    aggression = draft_state[team]['aggression']

    tm_position_val = max_slots[position_id] / (draft_state[team][position_id] + 1)
    lg_position_val = (
                            (max_slots[position_id] * (N_TEAMS - 1))  # league position slots, except current team
                            / (sum(v[position_id] for k, v in draft_state.items() if k != team) + 1)  # total players drafted at position, except for current team
                    ) / (N_TEAMS - 1)  # average of league, except current team
    lineup_slot_scarcity = tm_position_val / lg_position_val

    # percentage of draft team has been passive
    if draft_data[team]['picks']:
        pick_scarcity = (pick - draft_data[team]['picks'][-1]['pick']) / n_picks
    else:
        pick_scarcity = pick / n_picks

    tm_roster_val = 15 - draft_state[team]['slots_left']
    lg_roster_val = (
                        (pick - tm_roster_val)  # total picks made, except current team
                    ) / (N_TEAMS - 1)  # average of league, except current team
    roster_scarcity = lg_roster_val / (tm_roster_val + 1)

    tm_appetite = lineup_slot_scarcity * roster_scarcity * pick_scarcity * aggression
    return tm_appetite


def team_can_draft(team: str, bid: float, draft_state: dict, max_slots: dict, nom_pos_id: int):
    # check if a team can draft the nominated player at their bid amount
    # the team must have:
    #   >=$1 per player spot remaining (dppr) after drafting OR have enough funds to draft player as the last pick (not go negative)
    #   AND not need another position filled with final pick(s)
    has_slots = draft_state[team][nom_pos_id] < max_slots[nom_pos_id] and draft_state[team]['slots_left'] > 0
    over_dppr = (draft_state[team]['funds_left'] - bid) - (draft_state[team]['slots_left'] - 1) >= 0
    last_player_funds = (draft_state[team]['funds_left'] - bid >= 0) and draft_state[team]['slots_left'] == 1
    needs_other_pos = len(
        {k: v for k, v in draft_state[team].items() if k in tuple(POSITIONS) and k != nom_pos_id and v == 0}) / \
                      draft_state[team]['slots_left'] >= 1
    if has_slots and (over_dppr or last_player_funds) and not needs_other_pos:
        return True
    return False


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
players_data = load_espn_data(dataloader)
price_data = {k: v for k, v in calculate_prices(players_data=players_data, auction_settings=auction_settings).items() if v['price'] > 1}
values = np.array([v['vor'] for k, v in price_data.items()]).reshape(-1, 1)
gmcl = gm(n_components=10, covariance_type='full').fit(values)
gmcl.bic(values)
preds = gmcl.predict(values)
for i, (k, v) in enumerate(price_data.items()):
    price_data[k]['tier'] = int(preds[i])

mean_gms_missed = {'QB': 2.1, 'RB': 2.9, 'WR': 2.2, 'TE': 1.6}
wts = {0: {'mean': 0.9667, 'sd': 0.1666}, #'sd': 0.1690},
       2: {'mean': 1.0407, 'sd': 0.1666}, #'sd': 0.3855},
       4: {'mean': 1.0267, 'sd': 0.1666}, #'sd': 0.2586},
       6: {'mean': 0.9795, 'sd': 0.1666}} #'sd': 0.2370}}


##### START SIMULATION #####
def run_simulation(n_sims):
    owners = ['Aaro', 'Adit', 'Aksh', 'Arju', 'Ayaz', 'Char', 'Faiz', 'Hirs', 'Nick', 'Varu']
    total_slots = sum(STARTERS.values()) + N_FLEX + N_BENCH
    # starters = {p: s for p, s in zip(POSITIONS, STARTERS)}
    id_pos_map = {
        0: 'QB',
        2: 'RB',
        4: 'WR',
        6: 'TE',
        16: 'DST',
        'QB': 0,
        'RB': 2,
        'WR': 4,
        'TE': 6,
        'DST': 16,
    }
    strategies = {
        'balanced': {0: 1.0, 2: 1.0, 4: 1.0, 6: 1.0, 16: 1.0},
        'rb_heavy': {0: 0.95, 2: 1.15, 4: 0.95, 6: 0.95, 16: 1.0},
        'zero_rb': {0: 1.05, 2: 0.80, 4: 1.1, 6: 1.05, 16: 1.0}
    }
    max_slots = {  # realistic max number of players, not ESPN max
        0: 2,
        2: 7,
        4: 8,
        6: 2,
        16: 2
    }
    final_results = {  # initialize final output data
        s: {
            'draft_state': {},
            'results': {}
        } for s in range(n_sims)
    }
    start = time.perf_counter()
    for sim in range(n_sims):
        print(sim, end='\r')

        # initialize draft data for current sim
        player_pool = {pid: p.copy() for pid, p in price_data.items()}  # reset player pool
        draft_state = {
            o: {
                'aggression': random.uniform(0.8, 1.2),
                'strategy': random.choices(list(strategies.keys()), weights=[0.4, 0.4, 0.2])[0],
                'funds_left': BUDGET,
                'slots_left': total_slots,
                'max_bid': BUDGET - (total_slots - 1),
                'picks': [],
                0: 0,
                2: 0,
                4: 0,
                6: 0,
                16: 0
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
            nom_position_id = id_pos_map[nom_position]
            nom_ppg = player_pool[nom_id]['ppg']
            nom_vor = player_pool[nom_id]['vor']
            nom_price = player_pool[nom_id]['price']

            if nom_id not in player_pool:
                # if nominated player was dropped during loop, restart bidding with new player
                continue

            team_appetites = {
                o: appetite(team=o, max_slots=max_slots, draft_state=draft_state, position_id=nom_position_id, pick=pick, draft_data=draft_state)
                for o in owners
            }
            total_appetite = sum(team_appetites.values())
            bids = []
            for team in owners:
                if draft_state[team]['slots_left'] > 0:
                    strat_mult = strategies[draft_state[team]['strategy']][nom_position_id]
                    tm_bid = min(draft_state[team]['max_bid'], nom_price * strat_mult * ((team_appetites[team] / total_appetite) * N_TEAMS))
                    check = team_can_draft(team=team, bid=tm_bid, draft_state=draft_state, max_slots=max_slots, nom_pos_id=nom_position_id)
                    if check:
                        bids.append((team, MIN_BID if tm_bid < 1 else tm_bid))
            if not bids:
                # if no team can bid, restart bidding with new player
                remove_player_from_pool(player_pool, nom_id)
                continue

            winner, top_bid = sorted(bids, key=lambda x: -x[1])[0]
            second_bid = 0
            if len(bids) > 1:
                second_bid = bids[1][1]
            final_price = min(int(top_bid), max(int(second_bid) + 1, MIN_BID))  # winner only spends $1 more than second highest bid

            # update draft statuses
            # adjust remaining prices for inflation
            total_spend += final_price
            infl = inflation(remaining_prices = [v['price'] for k, v in player_pool.items() if k != nom_id],
                             total_spent = total_spend,
                             budget = BUDGET,
                             n_teams = N_TEAMS)
            print(pick, infl)
            for k, v in player_pool.items():
                v['price'] *= infl

            draft_state[winner]['picks'].append({  # assign player to winning team
                'pick': pick,
                'winning_bid': final_price,
                'player_id': nom_id,
                'player_name': nom_player,
                'nfl_team': nom_team,
                'bye': nom_bye,
                'position': nom_position,
                'ppg': nom_ppg,
                'vor': nom_vor
            })
            draft_state[winner]['funds_left'] -= final_price
            draft_state[winner]['slots_left'] -= 1
            draft_state[winner]['max_bid'] -= (final_price - 1)  # -$1 for filling current spot
            draft_state[winner][nom_position_id] += 1

            remove_player_from_pool(player_pool, nom_id)
            pick += 1

        final_results[sim]['draft_state'] = draft_state


        ### SIM SEASON ###
        # for team, roster in draft_picks.items():
        #     # calculate lineup slots - highest bid player at each position is pos1
        #     slot_init = {p: 0 for p in POSITIONS + ['FLEX']}  # to check flex player
        #     roster = sorted(roster, key=lambda x: (x['winning_bid'], x['vor']), reverse=True)
        #     for player in roster:
        #         pos = player['position']
        #         if slot_init[pos] < starters[pos]:
        #             slot_init[pos] += 1
        #             player['slot'] = pos
        #         elif pos in FLEX_POSITIONS and slot_init[pos] == starters[pos] and slot_init['FLEX'] == 0:
        #             player['slot'] = 'FLEX'
        #             slot_init['FLEX'] += 1
        #         else:
        #             player['slot'] = 'BENCH'
        #
        #         # simulate games missed and new ppg for current "season"
        #         player['games_missed'] = sim_injury(mean_gms_missed, player['position'])
        #         player['ppg'] = player['ppg'] * apply_weight(wts, player['position'])
        #
        # season_results = {
        #     o: {
        #         'wins': 0,
        #         'points': 0,
        #         'playoffs': 0,
        #         'finals': 0,
        #         'champ': 0
        #     }
        #     for o in owners
        # }
        # for week in range(1, 15):  # weeks 1 to end of regular season
        #     scores = {}
        #     for team, roster in draft_picks.items():
        #         # TODO: add check for starters vs replacement player
        #         lineup = get_lineup(roster=roster, week=week)
        #         lineup = [dict(l, **{'sd': l['ppg'] * 0.15 if l['position'] == 'QB' else l['ppg'] * 0.3}) for l in lineup]
        #         points = sum(random.normalvariate(s['ppg'], s['sd']) for s in lineup)
        #         scores[team] = points
        #     median = np.median([s for s in scores.values()])
        #     for team, score in scores.items():
        #         season_results[team]['points'] += score
        #         if score > median:  # team scored in the top half of league
        #             season_results[team]['wins'] += 1
        #
        # # SIM PLAYOFFS #
        # # quarterfinals
        # p_teams = [t[0] for t in sorted(season_results.items(), key=lambda x: (x[1]['wins'], x[1]['points']), reverse=True)][0:N_PLAYOFFS]
        # for t in p_teams:
        #     season_results[t]['playoffs'] += 1
        # sf_teams = p_teams[0:2]  # top two teams get by and move onto semifinals
        # qf_teams = [t for t in p_teams if t not in sf_teams]
        # qf_scores = {}
        # for team, roster in {k: v for k, v in draft_picks.items() if k in qf_teams}.items():
        #     qf_lineup = get_lineup(roster=roster, week=15)
        #     qf_lineup = [dict(l, **{'sd': l['ppg'] * 0.2 if l['position'] == 'QB' else l['ppg'] * 0.4}) for l in qf_lineup]
        #     qf_points = sum(random.normalvariate(s['ppg'], s['sd']) for s in qf_lineup)
        #     qf_scores[team] = qf_points
        # qf_median = np.median([s for s in qf_scores.values()])
        # for team, score in qf_scores.items():
        #     if score > qf_median:  # team scored in the top half of league
        #         sf_teams.extend([team])
        #
        # # semifinals
        # sf_scores = {}
        # finals_teams = []
        # for team, roster in {k: v for k, v in draft_picks.items() if k in sf_teams}.items():
        #     sf_lineup = get_lineup(roster=roster, week=16)
        #     sf_lineup = [dict(l, **{'sd': l['ppg'] * 0.2 if l['position'] == 'QB' else l['ppg'] * 0.4}) for l in sf_lineup]
        #     sf_points = sum(random.normalvariate(s['ppg'], s['sd']) for s in sf_lineup)
        #     sf_scores[team] = sf_points
        # sf_median = np.median([s for s in sf_scores.values()])
        # for team, score in sf_scores.items():
        #     if score > sf_median:  # team scored in the top half of league
        #         finals_teams.extend([team])
        #         season_results[team]['finals'] += 1
        #
        # # finals
        # finals_scores = {}
        # champion = []
        # for team, roster in {k: v for k, v in draft_picks.items() if k in finals_teams}.items():
        #     finals_lineup = get_lineup(roster=roster, week=16)
        #     finals_lineup = [dict(l, **{'sd': l['ppg'] * 0.2 if l['position'] == 'QB' else l['ppg'] * 0.4}) for l in finals_lineup]
        #     finals_points = sum(random.normalvariate(s['ppg'], s['sd']) for s in finals_lineup)
        #     finals_scores[team] = finals_points
        # finals_median = np.median([s for s in finals_scores.values()])
        # for team, score in finals_scores.items():
        #     if score > finals_median:  # team scored in the top half of league
        #         champion.extend([team])
        #         season_results[team]['champ'] += 1
        #
        # final_results[sim]['results'] = season_results

    end = time.perf_counter()
    elapsed = end-start
    print(elapsed)
    # print(f'{round(elapsed/60, 2)} minutes')
    return final_results

results = run_simulation(n_sims=1)

# Convert draft data to df
s1 = time.perf_counter()
draft_records = [
    {**player, 'team': team, 'sim': sim + 1}
    for sim, data in results.items()
    for team, roster in data['draft_data'].items()
    for player in roster
]
all_drafts = pd.DataFrame.from_records(draft_records)
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

# Save all_draft_data to a Pickle file
with open('auction/results/all_drafts_20250823.pkl', 'wb') as f:
    pickle.dump(all_drafts, f)
with open('auction/results/all_results_20250823.pkl', 'wb') as f:
    pickle.dump(all_results, f)

# load saved sim data
# with open('auction/results/all_drafts_20250823.pkl', 'rb') as f:
#     all_drafts = pickle.load(f)
# with open('auction/results/all_results_20250823.pkl', 'rb') as f:
#     all_results = pickle.load(f)


all_drafts['games_missed'] = all_drafts.games_missed.apply(lambda x: len(x))
# TODO: same for all_results


all_results.sort_values(['champ', 'points'], ascending=[False, True]).groupby('sim').points.sum().mean()


all_results.hist('points', bins=50)
plt.show()

z = (1420 - all_results.points.mean()) / all_results.points.std()



all_drafts.games_missed.plot.hist(bins=17)
plt.show()

def scatter_plot(player, sims_df, x='pick', y='winning_bid'):
    df_plyr = sims_df[sims_df.player == player]
    plt.figure(figsize=(7, 7))
    plt.axvline(x=df_plyr[x].mean(skipna=True), c='grey', dashes=(2, 2, 2, 2))
    plt.axhline(y=df_plyr[y].median(skipna=True), c='grey', dashes=(2, 2, 2, 2))
    plt.scatter(df_plyr[x], df_plyr[y], s=5)
    plt.title(player)
    plt.xlabel(x)
    plt.ylabel(y)
    plt.show()
scatter_plot(player="Omarion Hampton", sims_df=all_drafts.copy())
cmc = all_drafts[all_drafts.player == 'Christian McCaffrey']


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
combined_results = combined_results[combined_results.TOTAL_SPEND >= 180]

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
    Y_data = np.array(df.score_diff)
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


def spend_variation(col, df: pd.DataFrame = combined_results.copy()):
    X = df[col]*200
    Y = (df.points - df.points.median()) / 14
    norm = colors.TwoSlopeNorm(vcenter=0)
    fig, ax = plt.subplots()
    ax.scatter(x=X, y=Y, s=4, c=Y, norm=norm, cmap='coolwarm')
    ax.axhline(y=0, linestyle='dashed', linewidth=1, c='#B5B5B5')
    ax.xaxis.set_major_formatter('${x:1.0f}')
    plt.title(f'Variation in PPG by {col} Spend')
    plt.xlabel('Starter Spend')
    plt.ylabel('PPG Added')
    plt.show()


plot_spend_vs_median()
spend_variation('QB')
spend_variation('RB')
spend_variation('WR')
spend_variation('TE')
spend_variation('DST')
spend_variation('STARTERS')
spend_variation('BENCH')
