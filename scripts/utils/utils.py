from scripts.utils import constants as const
import sshtunnel
import pandas as pd
import numpy as np
import requests
import json
import difflib
import mysql.connector
pd.options.mode.chained_assignment = None


def load_data(league_id: str | int,
              season: str | int,
              swid: str,
              espn_s2: str) -> dict:
    """Pull ESPN API data for a particular season (current API version only goes back to 2018)"""

    url = f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/' \
          f'{int(season)}' \
          f'/segments/0/leagues/' \
          f'{int(league_id)}' \
          f'?view=mMatchupScore&view=mTeam&view=mSettings'
    r = requests.get(url,
                     cookies={
                         'SWID': swid,
                         'espn_s2': espn_s2
                     },
                     params={
                         'view': 'mMatchup'
                     })
    d = r.json()

    return d


def get_params(d: dict) -> dict:
    """Returns general league information used throughout the analysis"""

    league_size = d['settings']['size']
    roster_size = sum(d['settings']['rosterSettings']['lineupSlotCounts'].values())
    regular_season_end = d['settings']['scheduleSettings']['matchupPeriodCount']
    current_week = d['scoringPeriodId'] - 1
    matchup_week = d['scoringPeriodId']
    playoff_teams = d['settings']['scheduleSettings']['playoffTeamCount']
    playoff_matchup_length = d['settings']['scheduleSettings']['playoffMatchupPeriodLength']
    has_bonus_win = 1 if d['settings']['scoringSettings'].get('scoringEnhancementType') else 0
    has_ppr = [s['points'] for s in d['settings']['scoringSettings']['scoringItems'] if s['statId'] == 53]
    ppr_type = 0 if not has_ppr else has_ppr[0]
    weeks_left = 0 if current_week > regular_season_end else regular_season_end - current_week

    # roster construction
    # need to figure out rest of position codes
    lineup_slots = d['settings']['rosterSettings']['lineupSlotCounts']
    lineup_slots_df = pd.DataFrame.\
        from_dict(lineup_slots, orient='index')\
        .rename(columns={0: 'limit'})
    lineup_slots_df['posID'] = lineup_slots_df.index.astype('int')
    lineup_slots_df = lineup_slots_df[lineup_slots_df.limit > 0]
    lineup_slots_df['pos'] = lineup_slots_df.replace({'posID': const.SLOTCODES}).posID

    # Mapping primary owner ID to team ID
    primowner_to_teamid = {}
    teamid_to_primowner = {}
    for team in d['teams']:
        o_id = team['primaryOwner']
        t_id = team['id']
        primowner_to_teamid[o_id] = t_id
        teamid_to_primowner[t_id] = o_id

    # Get weekly matchups
    matchups_df = pd.DataFrame()
    for game in d['schedule']:
        if game['matchupPeriodId'] > regular_season_end:
            continue
        else:
            week = game['matchupPeriodId']
            team1 = teamid_to_primowner[game['home']['teamId']]
            score1 = game['home']['totalPoints']
            team2 = teamid_to_primowner[game['away']['teamId']]
            score2 = game['away']['totalPoints']
            matchups = pd.DataFrame([[week, team1, score1, team2, score2]],
                                    columns=['week', 'team1_id', 'score1', 'team2_id', 'score2'])
            matchups_df = pd.concat([matchups_df, matchups])
    
    # convert matchups to scores df
    matchups_df['team1_result'] = np.where(matchups_df['score1'] > matchups_df['score2'], 1.0, 0.0)
    matchups_df['team2_result'] = np.where(matchups_df['score2'] > matchups_df['score1'], 1.0, 0.0)
    mask = (matchups_df.score1 == matchups_df.score2)\
           & (matchups_df.score1 > 0)\
           & (matchups_df.score2 > 0)  # Account for ties
    matchups_df.loc[mask, ['team1_result', 'team2_result']] = 0.5

    # convert dataframe to long format so each row is a team week, not matchup
    home = matchups_df.iloc[:, [0, 1, 2, 5]].rename(columns={
        'team1_id': 'team',
        'score1': 'score',
        'team1_result': 'result'
    })
    home['id'] = home['team'].astype(str) + home['week'].astype(str)
    away = matchups_df.iloc[:, [0, 3, 4, 6]].rename(columns={
        'team2_id': 'team',
        'score2': 'score',
        'team2_result': 'result'
    })
    away['id'] = away['team'].astype(str) + away['week'].astype(str)
    scores_df = pd.concat([home, away]).sort_values(['week', 'id']).drop('id', axis=1).reset_index(drop=True)

    # position = lineup_slots_df.pos.str.lower().drop(labels=['20','21']).tolist()
    position = lineup_slots_df.pos.str.lower().to_list()
    position = np.setdiff1d(position, ['bench', 'ir']).tolist()
    teams = list(primowner_to_teamid.keys())

    # FAAB budget remaining
    faab_budget = d['settings']['acquisitionSettings']['acquisitionBudget']
    faab_remaining = {}
    for tm in d['teams']:
        teamid = tm['id']
        remaining = faab_budget - tm['transactionCounter']['acquisitionBudgetSpent']
        faab_remaining[teamid] = remaining

    params = {
        'current_week': current_week,
        'faab_budget': faab_budget,
        'faab_remaining': faab_remaining,
        'has_bonus_win': has_bonus_win,
        'league_size': league_size,
        'lineup_slots_df': lineup_slots_df,
        'matchup_df': matchups_df,
        'scores_df': scores_df,
        'matchup_week': matchup_week,
        'playoff_matchup_length': playoff_matchup_length,
        'playoff_teams': playoff_teams,
        'positions': position,
        'ppr_type': ppr_type,
        'primaryOwner_to_teamId': primowner_to_teamid,
        'regular_season_end': regular_season_end,
        'roster_size': roster_size,
        'slotcodes': const.SLOTCODES,
        'team_map': const.TEAM_IDS,
        'teams': teams,
        'weeks_left': weeks_left
    }

    return params


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
