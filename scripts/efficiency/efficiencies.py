import pandas as pd
import requests
from scripts.utils import (utils as ut,
                           constants as const)


def load_weekly_data(season, week, league_id, swid, espn_s2):
    url = f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/' \
          f'{int(season)}' \
          f'/segments/0/leagues/' \
          f'{int(league_id)}' \
          f'?view=mMatchupScore&view=mMatchup&view=mTeam&view=mSettings'
    r = requests.get(url,
                     cookies={
                         'SWID': swid,
                         'espn_s2': espn_s2
                     },
                     params={
                         'scoringPeriodId': week,
                         'matchupPeriodId': week
                     })
    d = r.json()

    return d


def get_optimal_points(season, week):
    d = load_weekly_data(season, week, const.LEAGUE_ID, const.SWID, const.ESPN_S2)
    params = ut.get_params(d)
    
    slots = const.SLOTCODES
    positions = const.ESPN_POSITION_MAP
    slot_limits = d['settings']['rosterSettings']['lineupSlotCounts']
    df = pd.DataFrame(columns=['season', 'week',
                               'team_id', 'team_name',
                               'actual_score', 'actual_projected',
                               'best_projected_actual', 'best_projected_proj',
                               'best_lineup_actual', 'best_lineup_proj'])
    for team in d['teams']:
        roster = {}
        owr_id = team['primaryOwner']
        owr_name = params['team_map'][owr_id]['name']['display']
        for plr in team['roster']['entries']:
            plr_id = plr['playerId']
            plr_name = plr['playerPoolEntry']['player']['fullName']
            slot_id = plr['lineupSlotId']
            slot = slots[slot_id]
            psns = plr['playerPoolEntry']['player']['eligibleSlots']
            for p in psns:
                try:
                    psn = positions[p]
                    psn_id = p
                except KeyError:
                    pass

            points = 0
            for stat in plr['playerPoolEntry']['player']['stats']:
                if stat['scoringPeriodId'] == week:
                    if stat['statSourceId'] == 0:
                        points = stat['appliedTotal']
                    if stat['statSourceId'] == 1:
                        proj = stat['appliedTotal']

            roster[plr_id] = {'player_name': plr_name,
                              'slot_id': slot_id,
                              'slot': slot,
                              'position_id': psn_id,
                              'position': psn,
                              'points': points,
                              'proj': proj}

        # get actual points
        act_pts_act = 0
        act_pts_proj = 0
        for plr, values in roster.items():
            if values['slot_id'] not in [20, 21]:
                act_pts_act += values['points']
                act_pts_proj += values['proj']
    
    
        # get best projected lineup
        proj_pts_proj = 0
        proj_pts_act = 0
        to_remove = []
        for id, pos in positions.items():
            limit = slot_limits[str(id)]
            player_pool = {k: v for k, v in roster.items() if v['position'] == pos}
            selector = sorted(player_pool, key=lambda x: player_pool[x]['proj'], reverse=True)[0:limit]
            to_remove.append(selector)
            the_players = {k: v for k, v in player_pool.items() if k in selector}
            for id, vals in the_players.items():
                proj_pts_proj += vals['proj']
                proj_pts_act += vals['points']
    
        # flatten list
        to_remove = [
            x
            for xs in to_remove
            for x in xs
        ]
    
        # get flex player
        flex_pool = {k: v for k, v in roster.items() if k not in to_remove and v['position_id'] in [2, 4, 6]}
        flex_selector = sorted(flex_pool, key=lambda x: flex_pool[x]['proj'], reverse=True)[0:1][0]
        the_flex = flex_pool[flex_selector]
        proj_pts_proj += the_flex['proj']
        proj_pts_act += the_flex['points']
    
    
        # get optimal lineup
        opt_pts_proj = 0
        opt_pts_act = 0
        to_remove = []
        for id, pos in positions.items():
            limit = slot_limits[str(id)]
            player_pool = {k: v for k, v in roster.items() if v['position'] == pos}
            selector = sorted(player_pool, key=lambda x: player_pool[x]['points'], reverse=True)[0:limit]
            to_remove.append(selector)
            the_players = {k: v for k, v in player_pool.items() if k in selector}
            for id, vals in the_players.items():
                opt_pts_proj += vals['proj']
                opt_pts_act += vals['points']
    
        # flatten list
        to_remove = [
            x
            for xs in to_remove
            for x in xs
        ]
    
        # get flex player
        flex_pool = {k: v for k, v in roster.items() if k not in to_remove and v['position_id'] in [2, 4, 6]}
        flex_selector = sorted(flex_pool, key=lambda x: flex_pool[x]['points'], reverse=True)[0:1][0]
        the_flex = flex_pool[flex_selector]
        opt_pts_proj += the_flex['proj']
        opt_pts_act += the_flex['points']
        row = [const.SEASON, week,
               owr_id, owr_name,
               round(act_pts_act, 2), round(act_pts_proj, 2),
               round(proj_pts_act, 2), round(proj_pts_proj, 2),
               round(opt_pts_act, 2), round(opt_pts_proj, 2)]

        df.loc[len(df)] = row

    return df


# df = pd.DataFrame()
# for wk in range(1, 15):
#     print(wk)
#     test = get_optimal_points(season=2018, week=wk)
#     df = pd.concat([df, test])
