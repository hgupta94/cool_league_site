from scripts.utils import constants as const
import sshtunnel
import pandas as pd
import numpy as np
import requests
import json
import difflib
import mysql.connector
pd.options.mode.chained_assignment = None


def flatten_list(lst: list) -> list:
    return [
        x
        for xs in lst
        for x in xs
    ]


def get_espn_players(season: str | int):
    global pos_id
    url = f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/' \
          f'{int(season)}' \
          f'/segments/0/leaguedefaults/1?view=kona_player_info'

    filters = {
        'players': {
            'limit': 500,
            'sortDraftRanks': {
                'sortPriority': 100,
                'sortAsc': True,
                'value': 'PPR'
            }
        }
    }

    headers = {
        'x-fantasy-filter': json.dumps(filters)
    }

    r = requests.get(url,
                     params={
                         'view': 'players_wl'
                     },
                     headers=headers)
    d = r.json()

    player_df = pd.DataFrame(columns=['player_id', 'player', 'team_id', 'team', 'position_id', 'position'])
    for player in d['players']:
        player_id = player['id']
        player_name = player['player']['fullName']
        team_id = player['player']['proTeamId']
        team_abbrev = const.ESPN_TEAM_MAP[team_id]

        # position
        for pos in player['player']['eligibleSlots']:
            if pos in const.ESPN_POSITION_MAP.keys():
                pos_id = pos
                pos_name = const.ESPN_POSITION_MAP[pos_id]

        player_df.loc[len(player_df)] = [player_id, player_name, team_id, team_abbrev, pos_id, pos_name]

    return player_df


def match_players_to_espn(df: pd.DataFrame,
                          df_pos_col: str,
                          players: pd.DataFrame,
                          drop_cols: list):
    matched_df = pd.DataFrame()
    for idx, row in df.iterrows():
        player = f"{row['Player']}|{row['TEAM']}"

        try:
            matches = (players.player + '|' + players.team).to_list()
            str_dist = [difflib.SequenceMatcher(None, player, m).ratio() for m in matches]

            # lower threshold to match all DSTs
            if row[df_pos_col].lower() == 'dst' or row[df_pos_col].lower == 'd/st':
                ind = [idx for idx, value in enumerate(str_dist) if value >= 0.7][0]
            else:
                ind = [idx for idx, value in enumerate(str_dist) if value >= 0.9][0]

            the_row = pd.concat([players.iloc[[ind]].reset_index(drop=True),
                                 df[df.Player == row['Player']].reset_index(drop=True)], axis=1)
            matched_df = pd.concat([matched_df, the_row]).drop(drop_cols, axis=1)

        except IndexError:
            pass

    return matched_df


def ssh_tunnel():
    """Creates an SSH tunnel obejct to connect to MySQL"""

    tunnel = sshtunnel.SSHTunnelForwarder(
            const.SSH_HOST,
            ssh_username=const.USERNAME,
            ssh_password=const.SSH_PASS,
            remote_bind_address=(const.DB_HOST, 3306)
    )

    return tunnel


def mysql_connection():
    """Creates a MySQL connection obejct"""

    conn = mysql.connector.connect(
        host=const.DB_HOST,
        user=const.USERNAME,
        password=const.DB_PASS,
        database=const.DB
    )

    return conn
