from scripts.api.dataloader import DataLoader
from scripts.api.settings import LeagueSettings, RosterSettings, TeamSettings
from scripts.api.models.schedule import Matchup
from scripts.utils.constants import NFL_TEAM_MAP_ESPN, DEFAULT_POSITION_MAP_ESPN

import requests
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
matchups = Matchup.get_season_matchups(params=ls)

# build dict of player scores
# {id: {week: (proj, score)}}
player_scores = []
for week in range(1, 18):
    dl = DataLoader(year=2025, week=week)
    players = dl.players_info()['players']
    for p in players:
        row = [2025, week, p['id']]
        stats = p['player']['stats']
        for stat in stats:
            if stat['seasonId'] == 2025 and stat['scoringPeriodId'] == week and stat['statSourceId'] == 0:
                # actual score
                row.append(stat['appliedTotal'])
            if stat['seasonId'] == 2025 and stat['scoringPeriodId'] == week and stat['statSourceId'] == 1:
                # projected score
                row.append(stat['appliedTotal'])
        player_scores.append(row)
df = pd.DataFrame(player_scores, columns=['season', 'week', 'player_id', 'proj', 'score']).fillna(0.0)
player_scores = df.groupby("player_id").apply(lambda g: dict(zip(g["week"], zip(g['proj'], g["score"])))).to_dict()


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
        n_total_drafted = draft_by_pos[pos] * n_teams * (sum(rs.lineup_position_limits.values()))
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
        posid = position_to_id[player['position']]
        player['position_id'] = posid
        player['price'] = (player['vor'] ** exp[position_to_id[player['position']]]) / pos_vor_adj[posid] * pos_dollars[posid] + 1

    return dict(sorted(players_data.items(), key=lambda x: x[1]['price'], reverse=True))


# simulate auction draft
def remove_player_from_pool(player_data: dict,
                            player_id: int):
    player_data.pop(player_id)


def nominate_player(data: dict,
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
    player_pool = {k: v for k, v in data.items() if id_pos_map[v['position']] in positions}
    plyrs = {k: player_pool[k] for k in list(player_pool)[:n]}
    probs = [v['vor'] / sum(v['vor'] for k, v in plyrs.items()) for k, v in plyrs.items()]
    return random.choices(list(plyrs), probs)[0]


def appetite(team, max_slots, draft_state, position_id, draft_data, budget: int = BUDGET, total_slots: int = 15):
    """
    Calculate each team's 'appetite' to draft the current player.
    position scarcity: player's value compared to rest of players in tier
    position scarcity: # players at position a team has compared to the league. fewer players vs league => higher scarcity
    roster scarcity: # of total players team has compared to league
    """
    if draft_data[team]['slots_left']:
        willingness = random.uniform(0.8, 1.2)

        base = budget / total_slots
        team_dps = draft_data[team]['funds_left'] / draft_data[team]['slots_left']
        roster_scarcity = team_dps / base

        # prioritize adding player to starter over bench
        tm_position_val = max_slots[position_id] / (draft_state[team][position_id] + 1)
        lg_position_val = (
                                (max_slots[position_id] * (N_TEAMS - 1))  # league position slots, except current team
                                / (sum(v[position_id] for k, v in draft_state.items() if k != team) + 1)  # total players drafted at position, except for current team
                        ) / (N_TEAMS - 1)  # average of league, except current team
        lineup_slot_scarcity = tm_position_val / lg_position_val

        tm_appetite = willingness * math.log(lineup_slot_scarcity+1) * roster_scarcity
        return tm_appetite
    return 0.0


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


def calculate_team_bid(team, nom_price, nom_position_id, draft_state, strategies, appetites, n_teams: int = N_TEAMS):
    """
    Appetite determines max willingness to overpay.
    """
    aggression = draft_state[team]['aggression']
    strat_mult = strategies[draft_state[team]['strategy']][nom_position_id]

    tm_app = appetites[team]
    total_app = sum(v for k, v in appetites.items() if draft_state[k]['slots_left'] > 0)
    appetite_share = tm_app / total_app if total_app > 0 else 1 / n_teams

    # Center appetite around the mean (1/n_teams)
    # Below mean → below 1.0x multiplier, above mean → above 1.0x
    mean_appetite_share = 1.0 / n_teams
    centered_appetite = appetite_share - mean_appetite_share

    # Scale centered appetite into max overpay ratio
    # Extreme appetite swings ±4x the mean; compress into [0.85, 1.40] range
    max_willing_ratio = 1.0 + np.clip(centered_appetite * 5.0, -0.15, 1.0)

    max_willing_to_pay = nom_price * aggression * strat_mult * max_willing_ratio
    bid_shade = np.random.uniform(0.70, 1.0)
    tm_bid = max_willing_to_pay * bid_shade

    tm_bid = min(tm_bid, draft_state[team]['max_bid'])
    return max(tm_bid, MIN_BID)


def inflation(remaining_prices: list,
              total_spent: int,
              budget: int,
              n_teams: int):
    if remaining_prices:
        return ((budget * n_teams) - total_spent) / sum(remaining_prices)
    else:
        return 1


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


def get_replacement_player_id(position, week, player_pool, price_data, player_scores):
    if position in POSITIONS:
        return next(iter({k: v for k, v in price_data.items() if v['price'] <= 1 and position == v['position_id']}))
    if position == 23:
        return next(iter({k: v for k, v in price_data.items() if v['price'] <= 1 and v['position_id'] in FLEX_POSITIONS}))
    else:
        raise ValueError(f'{position} not valid. Position should be in {POSITIONS}')


def get_replacement_player_id_act(position, week, price_data, player_scores):
    if position in POSITIONS:
        pool = list({k: v for k, v in price_data.items() if v['price'] <= 1 and position == v['position_id']})
        pid = sorted(
            ((k, v[week]) for k, v in player_scores.items() if k in pool and week in v),
            key=lambda item: item[1][0],  # first value in (proj, score)
            reverse=True  # highest proj first
        )[0][0]
        return pid
    if position == 23:
        pool = list({k: v for k, v in price_data.items() if v['price'] <= 1 and v['position_id'] in FLEX_POSITIONS})
        pid = sorted(
            ((k, v[week]) for k, v in player_scores.items() if k in pool and week in v),
            key=lambda item: item[1][0],  # first value in (proj, score)
            reverse=True  # highest proj first
        )[0][0]
        return pid
    else:
        raise ValueError(f'{position} not valid. Position should be in {POSITIONS}')


def get_lineup_proj(roster: list[dict], week):
    starters = []
    active_players = [i for i in roster if (week != i['bye']) and (week not in i['games_missed'])]
    for pos, st in rs.lineup_position_limits.items():
        if pos != 23:
            pos_players = sorted([p for p in roster if p['position_id'] == pos], key=lambda x: x['ppg'], reverse=True)
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


def get_lineup_act(roster: list[dict], price_data, player_scores: dict, week: int):
    starters = []
    # add actual score to players
    for p in roster:
        p['proj'] = player_scores[p['player_id']][week][0]
        p['act'] = player_scores[p['player_id']][week][1]

    for pos, st in rs.lineup_position_limits.items():
        if pos in {0, 2, 4, 6, 16}:  # qb rb wr te dst
            pos_players = sorted([p for p in roster if p['position_id'] == pos], key=lambda x: x['proj'], reverse=True)
            if pos_players:
                starters.extend(pos_players[0:st])

            # check if replacement player(s) are needed
            players_needed = st - len(pos_players)
            if players_needed:
                flex = get_replacement_player_id_act(position=pos, week=week, price_data=price_data, player_scores=player_scores)
                price_data[flex]['player_id'] = flex
                price_data[flex]['act'] = player_scores[flex][week][1]
                starters.extend(price_data[flex] for _ in range(players_needed))
        elif pos == 23:
            # get flex starter(s)
            starter_ids = [x['player_id'] for x in starters]  # remove starters from flex consideration
            flex_players = []
            for fl_pos in FLEX_POSITIONS:
                fl = (
                    [fl for fl in roster if fl['position_id'] == fl_pos and fl['player_id'] not in starter_ids]
                )
                if fl:
                    flex_players.extend(fl)
            if flex_players:
                # if there are enough flex players
                flex_sorted = sorted(flex_players, key=lambda x: x['proj'], reverse=True)
                starters.extend(flex_sorted[0:st])
            else:
                flex = get_replacement_player_id_act(position=pos, week=week, price_data=price_data, player_scores=player_scores)
                price_data[flex]['player_id'] = flex
                price_data[flex]['act'] = player_scores[flex][week][1]
                starters.extend(price_data[flex] for _ in range(st))
                # starters.extend([price_data[get_replacement_player_id_act(position=23, week=week, price_data=price_data, player_scores=player_scores)] for _ in range(N_FLEX)])
    if len(starters) == 9:
        return starters
    else:
        return None



##### LOAD DATA #####
season = 2025
players_data = load_espn_data(dataloader)
price_data = {k: v for k, v in calculate_prices(players_data=players_data, auction_settings=auction_settings).items()}
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
    owners = [1, 2, 4, 5, 6, 8, 9, 10, 11, 12]
    total_slots = sum(STARTERS.values()) + N_FLEX + N_BENCH
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
        'rb_heavy': {0: 1.0, 2: 1.1, 4: 0.9, 6: 1.0, 16: 1.0},
        'zero_rb': {0: 1.0, 2: 0.9, 4: 1.1, 6: 1.0, 16: 1.0}
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
        player_pool = {pid: p.copy() for pid, p in price_data.items() if p['price'] > 1}  # reset player pool
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
                o: appetite(team=o, max_slots=STARTERS, draft_state=draft_state, position_id=nom_position_id, draft_data=draft_state)
                for o in owners
            }

            bids = []
            for team in owners:
                if draft_state[team]['slots_left'] > 0:
                    init_bid = calculate_team_bid(team=team, nom_price=nom_price, nom_position_id=nom_position_id, draft_state=draft_state, strategies=strategies, appetites=team_appetites)
                    tm_bid = min(draft_state[team]['max_bid'], init_bid)  # make sure team can't bid above max bid
                    for b in range(int(tm_bid), 0, -1):
                        # get the max a team can bid for a player
                        check = team_can_draft(team=team, bid=b, draft_state=draft_state, max_slots=max_slots, nom_pos_id=nom_position_id)
                        if check:
                            bids.append((team, MIN_BID if b < 1 else b))
                            break
            if not bids:
                # if no team can bid, restart bidding with new player
                remove_player_from_pool(player_pool, nom_id)
                continue

            bids.sort(key=lambda x: -x[1])
            winner, top_bid = bids[0]
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
                'position_id': nom_position_id,
                'ppg': nom_ppg,
                'vor': nom_vor,
                'price': nom_price
            })
            draft_state[winner]['funds_left'] -= final_price
            draft_state[winner]['slots_left'] -= 1
            draft_state[winner]['max_bid'] -= (final_price - 1)  # -$1 for filling current spot
            draft_state[winner][nom_position_id] += 1

            remove_player_from_pool(player_pool, nom_id)
            pick += 1

        final_results[sim]['draft_state'] = draft_state


        ### SIM SEASON ###
        # for team in draft_state:
        #     roster = draft_state[team]['picks']
        #     # calculate lineup slots - highest bid player at each position is pos1
        #     slot_init = {p: 0 for p in list(POSITIONS) + [23]}  # to check flex player
        #     roster = sorted(roster, key=lambda x: (x['vor']), reverse=True)
        #     for player in roster:
        #         pos = id_pos_map[player['position']]
        #         if slot_init[pos] < STARTERS[pos]:
        #             slot_init[pos] += 1
        #             player['slot'] = pos
        #         elif pos in FLEX_POSITIONS and slot_init[pos] == STARTERS[pos] and slot_init[23] == 0:
        #             player['slot'] = 23
        #             slot_init[23] += 1
        #         else:
        #             player['slot'] = 20
        #
        #         # simulate games missed and new ppg for current "season"
        #         player['games_missed'] = sim_injury(mean_gms_missed, player['position'])
        #         player['ppg'] = player['ppg'] * apply_weight(wts, player['position'])

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
            for team in draft_state:
                # TODO: add check for starters vs replacement player
                roster = draft_state[team]['picks']
                lineup = get_lineup_act(roster=roster, price_data=price_data, player_scores=player_scores, week=week)
                points = sum(l['act'] for l in lineup)
                # for m in matchups[week]:
                #     if team in list(m.teams):
                #         m.teams[team].points = points
                scores[team] = points
            median = float(np.median([s for s in scores.values()]))
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
        for qf_team in qf_teams:
            qf_roster = draft_state[qf_team]['picks']
            qf_lineup = get_lineup_act(roster=qf_roster, price_data=price_data, player_scores=player_scores, week=15)
            qf_points = sum(l['act'] for l in qf_lineup)
            qf_scores[qf_team] = qf_points
        qf_median = float(np.median([s for s in qf_scores.values()]))
        for team, score in qf_scores.items():
            if score > qf_median:  # team scored in the top half of league
                sf_teams.extend([team])

        # semifinals
        sf_scores = {}
        finals_teams = []
        for sf_team in sf_teams:
            sf_roster = draft_state[sf_team]['picks']
            sf_lineup = get_lineup_act(roster=sf_roster, price_data=price_data, player_scores=player_scores, week=16)
            sf_points = sum(l['act'] for l in sf_lineup)
            sf_scores[sf_team] = sf_points
        sf_median = np.median([s for s in sf_scores.values()])
        for team, score in sf_scores.items():
            if score > sf_median:  # team scored in the top half of league
                finals_teams.extend([team])
                season_results[team]['finals'] += 1

        # finals
        f_scores = {}
        champion = []
        for f_team in finals_teams:
            f_roster = draft_state[f_team]['picks']
            f_lineup = get_lineup_act(roster=f_roster, price_data=price_data, player_scores=player_scores, week=17)
            f_points = sum(l['act'] for l in f_lineup)
            f_scores[f_team] = f_points
        f_median = float(np.median([s for s in f_scores.values()]))
        for team, score in f_scores.items():
            if score > f_median:  # team scored in the top half of league
                champion.extend([team])
                season_results[team]['champ'] += 1

        final_results[sim]['results'] = season_results

    end = time.perf_counter()
    elapsed = end-start
    print(elapsed)
    print(f'{round(elapsed/60, 2)} minutes')
    return final_results

results = run_simulation(n_sims=1000)

# Convert draft data to df
draft_records = [
    {**player, 'team': team, 'sim': sim + 1}
    for sim, data in results.items()
    for team, team_state in data['draft_state'].items()
    for player in team_state['picks']
]
all_drafts = pd.DataFrame.from_records(draft_records)

# Convert results dictionary to a DataFrame
all_results = pd.DataFrame([
    {**team_data, 'team': team, 'sim': sim + 1}
    for sim, sim_data in results.items()
    for team, team_data in sim_data['results'].items()
])

# # Save all_draft_data to a Pickle file
# with open('auction/results/all_drafts_20250823.pkl', 'wb') as f:
#     pickle.dump(all_drafts, f)
# with open('auction/results/all_results_20250823.pkl', 'wb') as f:
#     pickle.dump(all_results, f)

# load saved sim data
# with open('auction/results/all_drafts_20250823.pkl', 'rb') as f:
#     all_drafts = pickle.load(f)
# with open('auction/results/all_results_20250823.pkl', 'rb') as f:
#     all_results = pickle.load(f)


# all_drafts['games_missed'] = all_drafts.games_missed.apply(lambda x: len(x))
# TODO: same for all_results


all_results.sort_values(['champ', 'points'], ascending=[False, True]).groupby('sim').points.sum().mean()
all_results.groupby('wins').champ.mean()


all_results.hist('points', bins=50)
plt.show()

z = (1420 - all_results.points.mean()) / all_results.points.std()



all_drafts.games_missed.plot.hist(bins=17)
plt.show()

def scatter_plot(player, sims_df, x='pick', y='winning_bid'):
    df_plyr = sims_df[sims_df.player_name == player]
    plt.figure(figsize=(7, 7))
    plt.axvline(x=df_plyr[x].mean(skipna=True), c='grey', dashes=(2, 2, 2, 2))
    plt.axhline(y=df_plyr[y].median(skipna=True), c='grey', dashes=(2, 2, 2, 2))
    plt.scatter(df_plyr[x], df_plyr[y], s=5)
    plt.title(player)
    plt.xlabel(x)
    plt.ylabel(y)
    plt.show()
scatter_plot(player="Bijan Robinson", sims_df=all_drafts.copy())


by_slot_type = all_drafts.groupby(['sim', 'team', 'slot']).winning_bid.sum().reset_index()
by_slot_type['p_alloc'] = by_slot_type.winning_bid / BUDGET
by_slot_type_pivot = by_slot_type.pivot(index=['sim', 'team'], columns='slot', values='p_alloc').reset_index()
by_slot_type_pivot['STARTERS'] = by_slot_type_pivot.QB +  by_slot_type_pivot.RB +  by_slot_type_pivot.WR +  by_slot_type_pivot.TE +  by_slot_type_pivot.DST +  + by_slot_type_pivot.FLEX

by_position = all_drafts.groupby(['sim', 'team', 'position']).winning_bid.sum().reset_index()
by_position['p_alloc'] = by_position.winning_bid / BUDGET
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
