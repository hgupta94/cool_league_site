from scripts.api.DataLoader import DataLoader
from scripts.api.Teams import Teams
from scripts.api.Rosters import Rosters
from scripts.utils import constants as const
from scripts.utils import utils as ut

import re
import difflib
import scipy.stats as st
import random
import numpy as np
import pandas as pd
pd.options.mode.chained_assignment = None


def match_player_to_espn(the_player: str,
                         players: list) -> int | None:
    player_lookup = [f"{p['player']['fullName']}|{const.NFL_TEAM_MAP[p['player']['proTeamId']]}" for p in players]

    calc = [difflib.SequenceMatcher(None, the_player, m).ratio() for m in player_lookup]
    if max(calc) > 0.8:
        match_idx = calc.index(max(calc))

        return players[match_idx]['id']
    else:
        return None


def get_week_projections(week) -> pd.DataFrame:
    """Return current week's projections for all positions"""
    data = DataLoader()
    players = data.players()['players']

    positions = ['qb', 'rb', 'wr', 'te', 'dst']

    projections = pd.DataFrame()
    for pos in positions:
        # print(pos)
        url = f"https://www.fantasypros.com/nfl/projections/{pos}.php?scoring=HALF&week={week}"
        # url = f"https://www.fantasypros.com/nfl/rankings/half-point-ppr-{pos}.php?scoring=HALF&week={week}"
        df = pd.read_html(url)[0]

        # drop multi index column
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel()

        df['POSITION'] = pos.upper()
        try:
            df = df[['Player', 'FPTS', 'REC', 'POSITION']]
        except:
            df = df[['Player', 'FPTS', 'POSITION']]
            df['REC'] = 0

        # remove team from player name
        if pos != 'dst':
            df['TEAM'] = df.Player.str[-3:].str.strip()
            df['Player'] = df['Player'].str[:-3]
            df['Player'] = df['Player'].str.rstrip()

        if pos == 'dst':
            df['Player'] = df['Player'].str.split().str[-1] + ' DST'
            df['TEAM'] = ''

        projections = pd.concat([projections, df])

    projections['season'] = const.SEASON
    projections['week'] = week
    projections.columns = [c.lower() for c in projections.columns]

    qb_mask = (projections.position == 'QB') & (projections.fpts > 10)
    rb_mask = (projections.position == 'RB') & (projections.fpts > 5)
    wr_mask = (projections.position == 'WR') & (projections.fpts > 5)
    te_mask = (projections.position == 'TE') & (projections.fpts > 3)
    dst_mask = (projections.position == 'DST') & (projections.fpts > 3)
    projections = projections[qb_mask | rb_mask | wr_mask | te_mask | dst_mask]
    projections['match_on'] = projections.player + '|' + projections.team
    projections['id'] = (projections.player.str.replace(r'[^a-zA-Z]', '', regex=True)
                         + '_' + projections.season.astype(str)
                         + '_' + projections.week.astype(str).str.zfill(2))
    projections['espn_id'] = projections.apply(lambda x: match_player_to_espn(x['match_on'], players), axis=1)

    return projections[~projections.espn_id.isnull()]


def query_projections_db(season: int,
                         week: int) -> pd.DataFrame:
    cols = ['id', 'season', 'week', 'name', 'espn_id', 'position', 'receeptions', 'projection', 'created']
    with ut.mysql_connection() as conn:
        c = conn.cursor()
        query = f'''
        SELECT *
        FROM projections
        WHERE season={season} and week={week};
        '''
        c.execute(query)
        result = c.fetchall()
        df = pd.DataFrame(result)
        df.columns = cols
    return df[['name', 'espn_id', 'projection']].set_index('espn_id').to_dict(orient='index')


def get_best_lineup(week_data: DataLoader,
                    rosters: Rosters,
                    projections: pd.DataFrame,
                    week: int,
                    team_id: int) -> dict:
    slots = const.SLOTCODES
    positions = const.POSITION_MAP
    slot_limits = rosters.slot_limits
    team = [t for t in week_data['teams'] if t['id'] == team_id][0]
    roster = {}
    for plr in team['roster']['entries']:
        # general player data
        plr_id = plr['playerId']
        plr_name = plr['playerPoolEntry']['player']['fullName']
        slot_id = plr['lineupSlotId']
        lineup_slot = slots[slot_id]
        psns = plr['playerPoolEntry']['player']['eligibleSlots']
        for p in psns:
            # get NFL position
            try:
                psn = positions[p]
                psn_id = p
            except KeyError:
                continue

        # get actual and projected
        # TODO: need to know what this looks like when player hasn't played yet
        # TODO: what happens if player is not in projections db?
        act = 0
        proj = 0
        for stat in plr['playerPoolEntry']['player']['stats']:
            if stat['scoringPeriodId'] == week:
                if stat['statSourceId'] == 0:
                    pass
                    # act = stat['appliedTotal']
                try:
                    proj = projections[plr_id]['projection']
                except KeyError:
                    if stat['statSourceId'] == 1:
                        proj = stat['appliedTotal']

        roster[plr_id] = {
            'player_name': plr_name,
            'slot_id': slot_id,
            'lineup_slot': lineup_slot,
            'position_id': psn_id,
            'position': psn,
            'points': act,
            'projection': proj
        }

    # get best projected lineup
    selected = []
    for plid, pos in positions.items():
        pos_limit = slot_limits[plid]
        pos_player_pool = {k: v for k, v in roster.items() if v['position'] == pos}
        selector = sorted(pos_player_pool,
                          key=lambda x: pos_player_pool[x]['projection'],
                          reverse=True)[0:pos_limit]  # highest projected player(s)
        selected.append(selector)  # remove player from available pool
    selected_flat = ut.flatten_list(selected)

    # get flex player
    flex_pool = {k: v for k, v in roster.items() if k not in selected_flat and v['position_id'] in [2, 4, 6]}
    flex_selector = sorted(flex_pool, key=lambda x: flex_pool[x]['projection'], reverse=True)[0:1][0]

    # best projected lineup
    selected_flat.append(flex_selector)
    lineup = {k: v
              for k, v
              in roster.items()
              if k in selected_flat}
    return lineup


def simulate_lineup(lineup: dict) -> float:
    gamma_map = const.GAMMA_VALUES
    proj_points = 0
    for _, plr in lineup.items():
        vals = gamma_map[plr['position']]
        loc = vals['loc'] + (plr['projection'] - vals['mean'])
        sim = st.gamma.rvs(a=vals['a'], loc=loc, scale=vals['scale'], size=1).item()
        # TODO: figure out a way to use a player's variance to adjust scale
        # sim = abs(random.gammavariate(alpha=vals['a'], beta=vals['scale']) + loc)
        proj_points += sim
        # print(plr['player_name'], round(sim,2))
    # print(proj_points-base)
    return proj_points


def simulate_matchup(week_data: DataLoader,
                     rosters: Rosters,
                     week: int,
                     matchups: list,
                     projections: pd.DataFrame) -> list[dict]:
    matchup_sim = []
    for idx, m in enumerate(matchups):
        gmid = idx + 1

        tm1 = m['away']['teamId']
        lineup1 = get_best_lineup(week_data=week_data, rosters=rosters, projections=projections, week=week, team_id=tm1)
        sim1 = simulate_lineup(lineup1)

        tm2 = m['home']['teamId']
        lineup2 = get_best_lineup(week_data=week_data, rosters=rosters, projections=projections, week=week, team_id=tm2)
        sim2 = simulate_lineup(lineup2)

        # redo sim if they are somehow equal
        if sim1 == sim2:
            print('redoing sim')
            sim1 = simulate_lineup(lineup1)
            sim2 = simulate_lineup(lineup2)

        matchup_sim.append({
            'game_id': gmid,
            'team': tm1,
            'score': sim1,
            'result': 1 if sim1 > sim2 else 0
        })

        matchup_sim.append({
            'game_id': gmid,
            'team': tm2,
            'score': sim2,
            'result': 1 if sim2 > sim1 else 0
        })

    return matchup_sim


def simulate_week(week_data: DataLoader,
                  teams: Teams,
                  rosters: Rosters,
                  matchups: list,
                  projections: pd.DataFrame,
                  week: int,
                  n_sims: int = 10) -> list:
    n_scores = {key: 0 for key in teams.team_ids}
    n_wins = {key: 0 for key in teams.team_ids}
    n_tophalf = {key: 0 for key in teams.team_ids}
    n_highest = {key: 0 for key in teams.team_ids}
    n_lowest = {key: 0 for key in teams.team_ids}
    for sim in range(n_sims):
        random.seed(random.randrange(n_sims))
        matchup_sim = simulate_matchup(week_data=week_data,
                                       rosters=rosters,
                                       week=week,
                                       matchups=matchups,
                                       projections=projections)
        for tm in matchup_sim:
            n_scores[tm['team']] += tm['score']
            if tm['result'] == 1:
                n_wins[tm['team']] += 1

        for_tophalf = sorted(matchup_sim, key=lambda d: d['score'], reverse=True)[:int((len(teams.team_ids)/2))]
        for tm in for_tophalf:
            n_tophalf[tm['team']] += 1

        n_highest[max(matchup_sim, key=lambda x: x['score'])['team']] += 1
        n_lowest[min(matchup_sim, key=lambda x: x['score'])['team']] += 1

    return [n_scores, n_wins, n_tophalf, n_highest, n_lowest]


def calculate_odds(sim_result: dict,
                   n_sims: int) -> dict:
    odds_dict = {}
    for k, v in sim_result.items():
        ip = v / n_sims
        if ip / (1 - ip) >= 1:
            odds = (-1 * ip / (1 - ip)) * 100
            odds_dict[k] = f'{max(-10000, round(odds / 5) * 5)}'
        else:
            odds = (1 * (1 - ip) / ip) * 100
            odds_dict[k] = f'+{min(10000, round(odds / 5) * 5)}'
    return odds_dict


















