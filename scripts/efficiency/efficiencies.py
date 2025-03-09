from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params
from scripts.utils import utils as ut
from scripts.utils import constants as const

import pandas as pd


def get_optimal_points(season, week):
    d = DataLoader(year=season)
    data = d.load_week(week=week)
    params = Params(d)
    settings = d.settings()
    
    slots = const.SLOTCODES
    positions = const.ESPN_POSITION_MAP
    slot_limits = settings['settings']['rosterSettings']['lineupSlotCounts']
    slot_limits = {k: v for k, v in slot_limits.items() if v > 0}
    df = pd.DataFrame(columns=['id', 'season', 'week', 'team_id', 'team',
                               'actual_score', 'actual_projected',
                               'best_projected_actual', 'best_projected_proj',
                               'best_lineup_actual', 'best_lineup_proj'])

    for team in data['teams']:
        roster = {}
        owr_id = team['primaryOwner']
        owr_name = params.team_map[owr_id]['name']['display']
        for plr in team['roster']['entries']:
            # loop thru each player to get relevant data
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
                        # actual points that week
                        points = stat['appliedTotal']
                        # projected points that week
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
        for _, values in roster.items():
            if values['slot_id'] not in [20, 21]:
                act_pts_act += values['points']  # actual lineup actual points
                act_pts_proj += values['proj']  # actual lineup projected points

        # get best projected lineup
        proj_pts_proj = 0
        proj_pts_act = 0
        to_remove_proj = []
        for plid, pos in positions.items():
            limit = slot_limits[str(plid)]  # position limit
            tm_player_pool = {k: v for k, v in roster.items() if v['position'] == pos}
            selector = sorted(tm_player_pool, key=lambda x: tm_player_pool[x]['proj'], reverse=True)[0:limit]  # highest projected player/s
            to_remove_proj.append(selector)  # to remove player from available pool
            the_players = {k: v for k, v in tm_player_pool.items() if k in selector}  # selected player/s in current position
            for plid, vals in the_players.items():
                proj_pts_proj += vals['proj']  # best projected lineup projected points
                proj_pts_act += vals['points']  # best projected lineup actual points

        to_remove_proj_flat = ut.flatten_list(to_remove_proj)  # flatten list
    
        # get flex player
        flex_pool = {k: v for k, v in roster.items() if k not in to_remove_proj_flat and v['position_id'] in [2, 4, 6]}
        flex_selector = sorted(flex_pool, key=lambda x: flex_pool[x]['proj'], reverse=True)[0:1][0]
        the_flex = flex_pool[flex_selector]
        proj_pts_proj += the_flex['proj']
        proj_pts_act += the_flex['points']

        # best projected lineup
        to_remove_proj_flat.append(flex_selector)
        lineup_proj = {k: v for k, v in roster.items() if k in to_remove_proj_flat}
    
    
        # get optimal lineup
        opt_pts_proj = 0
        opt_pts_act = 0
        to_remove_opt = []
        for plid, pos in positions.items():
            limit = slot_limits[str(plid)]
            player_pool = {k: v for k, v in roster.items() if v['position'] == pos}
            selector = sorted(player_pool, key=lambda x: player_pool[x]['points'], reverse=True)[0:limit]
            to_remove_opt.append(selector)
            the_players = {k: v for k, v in player_pool.items() if k in selector}
            for _, vals in the_players.items():
                opt_pts_proj += vals['proj']
                opt_pts_act += vals['points']

        to_remove_opt_flat = ut.flatten_list(to_remove_opt)  # flatten list
    
        # get flex player
        flex_pool = {k: v for k, v in roster.items() if k not in to_remove_opt_flat and v['position_id'] in [2, 4, 6]}
        flex_selector = sorted(flex_pool, key=lambda x: flex_pool[x]['points'], reverse=True)[0:1][0]
        the_flex = flex_pool[flex_selector]
        opt_pts_proj += the_flex['proj']  # optimal lineup projected points
        opt_pts_act += the_flex['points']  # optimal lineup actual points

        # optimal lineup
        to_remove_opt_flat.append(flex_selector)
        lineup_opt = {k: v for k, v in roster.items() if k in to_remove_opt_flat}

        # create dataframe
        tm_id = f'{season}_{str(week).zfill(2)}_{owr_name}'
        row = [tm_id, season, week,
               owr_id, owr_name,
               round(act_pts_act, 2), round(act_pts_proj, 2),
               round(proj_pts_act, 2), round(proj_pts_proj, 2),
               round(opt_pts_act, 2), round(opt_pts_proj, 2)]
        df.loc[len(df)] = row

    keep = ['id', 'season', 'week', 'team',
            'actual_score', 'actual_projected',
            'best_projected_actual', 'best_projected_proj',
            'best_lineup_actual', 'best_lineup_proj']
    return df[keep]
