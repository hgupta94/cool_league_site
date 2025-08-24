import io
import base64

from scripts.api.Settings import Params
from scripts.api.Rosters import Rosters
from scripts.api.Teams import Teams

from scripts.utils.database import Database
from scripts.utils import utils
from scripts.utils import constants

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from adjustText import adjust_text
import matplotlib
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
matplotlib.use('Agg')


def get_optimal_points(params: Params,
                       teams: Teams,
                       rosters: Rosters,
                       week_data: dict,
                       season: int,
                       week: int):
    slots = rosters.slotcodes
    starters = {k: v for k, v in rosters.slot_limits.items() if k not in [20, 21, 23]}
    positions = {k: v for k, v in slots.items() if k in starters.keys()}
    slot_limits = rosters.slot_limits
    df = pd.DataFrame(columns=['id', 'season', 'week', 'team_id', 'team',
                               'actual_score', 'actual_projected',
                               'best_projected_actual', 'best_projected_proj',
                               'best_lineup_actual', 'best_lineup_proj'])

    for team in week_data['teams']:
        roster = {}
        owr_id = teams.teamid_to_primowner[team['id']]
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
        for posid, pos in positions.items():
            limit = slot_limits[posid]  # position limit
            tm_player_pool = {k: v for k, v in roster.items() if v['position'] == pos}
            selector = sorted(tm_player_pool, key=lambda x: tm_player_pool[x]['proj'], reverse=True)[0:limit]  # highest projected player/s
            to_remove_proj.append(selector)  # to remove player from available pool
            the_players = {k: v for k, v in tm_player_pool.items() if k in selector}  # selected player/s in current position
            for posid, vals in the_players.items():
                proj_pts_proj += vals['proj']  # best projected lineup projected points
                proj_pts_act += vals['points']  # best projected lineup actual points
        to_remove_proj_flat = utils.flatten_list(to_remove_proj)  # flatten list
    
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
            limit = slot_limits[plid]
            player_pool = {k: v for k, v in roster.items() if v['position'] == pos}
            selector = sorted(player_pool, key=lambda x: player_pool[x]['points'], reverse=True)[0:limit]
            to_remove_opt.append(selector)
            the_players = {k: v for k, v in player_pool.items() if k in selector}
            for _, vals in the_players.items():
                opt_pts_proj += vals['proj']
                opt_pts_act += vals['points']

        to_remove_opt_flat = utils.flatten_list(to_remove_opt)  # flatten list
    
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


def plot_efficiency(database: Database,
                    season: int,
                    week: int,
                    x: str,
                    y: str,
                    xlab: str,
                    ylab: str,
                    title: str):
    with database() as conn:
        query = f'''
        SELECT *
        FROM efficiency
        WHERE season={season} AND week<={week}
        '''
        eff = pd.read_sql(query, con=conn)

    cols = eff.select_dtypes(include=['float']).columns.tolist()
    df = eff.groupby('team')[cols].sum() / week
    df['act_opt_perc'] = df[x] / df[y]
    df['diff_from_opt'] = df.actual_lineup_score - df.optimal_lineup_score
    df['act_bestproj_perc'] = df.actual_lineup_score / df.best_projected_lineup_score

    # plot
    teams = df.index.to_list()
    perc = [f'{round(p * 100)}%' for p in df.act_opt_perc.to_list()]
    x = df.diff_from_opt.to_list()
    y = df.optimal_lineup_score.to_list()

    colors = ['black', 'darkcyan', 'brown', 'chocolate', 'dodgerblue', 'crimson',
              'forestgreen', 'slateblue', 'blueviolet', 'olivedrab', 'lightseagreen', 'grey']
    colors = colors[:len(x)]
    fig, ax = plt.subplots()
    fig.patch.set_facecolor('#f5f5f5')
    ax.set_facecolor('#f5f5f5')
    [i.set_linewidth(1.25) for i in ax.spines.values()]  # set border width
    ax.scatter(x, y, c=colors)
    ax.get_xlim()
    ax.get_ylim()

    # add team names and percentages
    texts = []
    for i, txt in enumerate(zip(teams, perc)):
        the_txt = f'{txt[0]} ({txt[1]})'
        texts.append(plt.text(x[i], y[i], the_txt, color=colors[i]))
    plt.axvline(x=np.median(x), color='grey', linestyle='--', alpha=0.3)
    plt.axhline(y=np.median(y), color='grey', linestyle='--', alpha=0.3)
    adjust_text(texts, autoalign='xy',
                expand_points=(2, 2))

    plt.xlabel(xlab)
    plt.ylabel(ylab)
    plt.setp(ax.spines.values(), color='lightgrey')
    # plt.figtext(0.99, 0.5, "Right Margin Text", va="center", rotation="vertical", ha="right")
    # plt.savefig('www/plots/efficiency_plot.png')

    # Convert plot to PNG image
    png_img = io.BytesIO()
    FigureCanvas(fig).print_png(png_img)

    # Encode PNG image to base64 string
    png_str = "data:image/png;base64,"
    png_str += base64.b64encode(png_img.getvalue()).decode('utf8')
    return png_str
