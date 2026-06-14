import os
from dotenv import load_dotenv
import datetime as dt


load_dotenv()
DB_USER = os.getenv('DB_USER_LOCAL')
DB_PASS = os.getenv('DB_PASS_LOCAL')
DB_HOST = os.getenv('DB_HOST_LOCAL')
DB_NAME = os.getenv('DB_NAME_LOCAL')
PA_PASS = os.getenv('PA_PASS')

# SSH DB credentials
DB_USER_SSH = os.getenv('DB_USER_SSH')
DB_PASS_SSH = os.getenv('DB_PASS_SSH')
DB_HOST_SSH = os.getenv('DB_HOST_SSH')  # SSH host
DB_NAME_SSH = os.getenv('DB_NAME_SSH')
# MySQL host for SSH tunnel (e.g., hgupta.mysql.pythonanywhere-services.com)
DB_MYSQL_HOST_SSH = os.getenv('DB_MYSQL_HOST_SSH')

BUYIN = 150
TOTAL_PAYOUT = BUYIN * 10
WEEKLY_PAYOUT = 5 * 14
PAYOUTS = {
    'weekly_top_score': 5,
    'first'      : (TOTAL_PAYOUT - WEEKLY_PAYOUT) * 0.500,
    'second'     : (TOTAL_PAYOUT - WEEKLY_PAYOUT) * 0.250,
    'third'      : (TOTAL_PAYOUT - WEEKLY_PAYOUT) * 0.100,
    'most_points': (TOTAL_PAYOUT - WEEKLY_PAYOUT) * 0.075,
    'most_wins'  : (TOTAL_PAYOUT - WEEKLY_PAYOUT) * 0.075,
}

CLINCHED = -99
ELIMINATED = 99
CLINCHED_DISP = 'c'
ELIMINATED_DISP = 'x'

# ESPN API parameters
# _TODAY = dt.datetime.now()
_TODAY = dt.datetime(2025, 12, 3)
_CURRENT_YEAR = _TODAY.year
_CURRENT_MONTH = _TODAY.month
_SEASON_START = dt.datetime(2025, 9, 1)  # monday before first game
_SEASON_END = dt.datetime(2026, 1, 5)  # monday after last game
SEASON = _CURRENT_YEAR if _CURRENT_MONTH >= 9 else _CURRENT_YEAR-1
WEEK = -(-(_TODAY - _SEASON_START).days // 7)

LEAGUE_ID = os.getenv('LEAGUE_ID')
SWID = os.getenv('SWID')
ESPN_S2 = os.getenv('ESPN_S2')

# Database columns for inserts
MATCHUP_COLUMNS = 'id, season, week, team, score, opponent, opponent_score, matchup_result, tophalf_result'
POWER_RANK_COLUMNS = 'id, season, week, team, season_idx, week_idx, consistency_idx, manager_idx, luck_idx, power_score_raw, power_score_norm, power_rank, score_raw_change, score_norm_change, rank_change'
PROJECTIONS_COLUMNS = 'id, season, week, name, espn_id, position, receptions, projection, actual'
H2H_COLUMNS = 'id, season, week, team, opponent, result'
EFFICIENCY_COLUMNS = 'id, season, week, team, actual_lineup_score, actual_lineup_projected, best_projected_lineup_score, best_projected_lineup_projected, optimal_lineup_score, optimal_lineup_projected'
SCHEDULE_SWITCH_COLUMNS = 'id, season, week, team, schedule_of, result'
WEEK_SIM_COLUMNS = 'id, season, week, matchup_id, team, avg_score, p_win, p_tophalf, p_highest, p_lowest'
SEASON_SIM_COLUMNS = 'id, season, week, team, matchup_wins, tophalf_wins, total_wins, total_points, most_wins, most_points, top_scores, playoffs, third, finals, champion'
RECORDS_COLUMNS = 'id, category, record, holder, season, week'
ALLTIME_STANDINGS_COLUMNS = 'id, team, seasons, playoffs, overall_rec, win_perc, matchup_rec, tophalf_rec, points'

RECORDS_COLUMNS_FLASK = ['category', 'record', 'holder', 'season', 'week']
ALLTIME_COLUMNS_FLASK = ['team', 'seasons', 'playoffs', 'overall_rec', 'win_perc', 'matchup_rec', 'tophalf_rec', 'points']


# Gamma distribution values for simulations
    # mean: average score of rostered players since 2021
    # a: alpha (shape)
    # loc: location
GAMMA_VALUES = {
    0: {
        'mean': 18.1987,
        'shape': 3.8710,
        'loc': 0,
        'scale': 4.7013,
        'var': 85.5582,
        'cv': 0.5082,
        'max': 55
    },
    2: {
        'mean': 10.9303,
        'shape': 1.6797,
        'loc': 0,
        'scale': 6.5074,
        'var': 71.1279,
        'cv': 0.7716,
        'max': 55
    },
    4: {
        'mean': 10.6807,
        'shape': 2.0045,
        'loc': 0,
        'scale': 5.3285,
        'var': 56.9123,
        'cv': 0.7063,
        'max': 50
    },
    6: {
        'mean': 8.8227,
        'shape': 2.0571,
        'loc': 0,
        'scale': 4.2889,
        'var': 37.8405,
        'cv': 0.6972,
        'max': 40
    },
    16: {
        'mean': 7.8577,
        'shape': 2.4491,
        'loc': 0,
        'scale': 3.2084,
        'var': 25.2108,
        'cv': 0.6390,
        'max': 35
    },
}

GAMMA_VALUES_STD = {
    0: {
        'mean': 19.7267,
        'shape': 4.5630,
        'loc': 0,
        'scale': 4.3232,
        'var': 85.2819,
        'cv': 0.4681,
        'max': 45
    },
    2: {
        'mean': 10.1373,
        'shape': 1.5153,
        'loc': 0,
        'scale': 6.6898,
        'var': 67.8170,
        'cv': 0.8124,
        'max': 55
    },
    4: {
        'mean': 9.1377,
        'shape': 1.7217,
        'loc': 0,
        'scale': 5.3072,
        'var': 48.4954,
        'cv': 0.7621,
        'max': 45
    },
    6: {
        'mean': 7.1001,
        'shape': 1.5351,
        'loc': 0,
        'scale': 4.6251,
        'var': 32.8389,
        'cv': 0.8071,
        'max': 35
    },
    16: {
        'mean': 8.7302,
        'shape': 2.0546,
        'loc': 0,
        'scale': 4.2490,
        'var': 37.0946,
        'cv': 0.6976,
        'max': 35
    },
    17: {
        'mean': 8.4088,
        'shape': 3.8613,
        'loc': 0,
        'scale': 4.2178,
        'var': 18.3121,
        'cv': 0.5089,
        'max': 25
    },
}


# ESPN mappings HT: https://github.com/cwendt94/espn-api/blob/master/espn_api/football/constant.py
NFL_TEAM_MAP_ESPN = {
    # NFL team ID to team abbreviation
    # HT: https://github.com/cwendt94/espn-api/blob/master/espn_api/football/constant.py
    0:  'None',
    1:  'ATL',
    2:  'BUF',
    3:  'CHI',
    4:  'CIN',
    5:  'CLE',
    6:  'DAL',
    7:  'DEN',
    8:  'DET',
    9:  'GB',
    10: 'TEN',
    11: 'IND',
    12: 'KC',
    13: 'LV',
    14: 'LAR',
    15: 'MIA',
    16: 'MIN',
    17: 'NE',
    18: 'NO',
    19: 'NYG',
    20: 'NYJ',
    21: 'PHI',
    22: 'ARI',
    23: 'PIT',
    24: 'LAC',
    25: 'SF',
    26: 'SEA',
    27: 'TB',
    28: 'WSH',
    29: 'CAR',
    30: 'JAX',
    33: 'BAL',
    34: 'HOU'
}

POSITION_MAP_ESPN = {
    # position ID to position name
    # only for NFL positions
    0:  'QB',
    2:  'RB',
    4:  'WR',
    6:  'TE',
    8:  'DT',
    9:  'DE',
    10: 'LB',
    11: 'DL',
    12: 'CB',
    13: 'S',
    14: 'DB',
    16: 'DST',
    17: 'K',
    18: 'P',
    19: 'HC',
}

DEFAULT_POSITION_MAP_ESPN = {
    # for some reason, player's defaultPositionId doesn't follow the previous mapping
    1: 'QB',
    2: 'RB',
    3: 'WR',
    4: 'TE',
    5: 'K',
    16: 'DST'
}

SLOTCODES_ESPN = {
    # position ID to position
    # all fantasy positions
    0:  'QB',
    1:  'TQB',
    2:  'RB',
    3:  'Flex RB_WR',  # RB/WR
    4:  'WR',
    5:  'Flex WR_TE',  # WR/TE
    6:  'TE',
    7:  'OP',
    8:  'DT',
    9:  'DE',
    10: 'LB',
    11: 'DL',
    12: 'CB',
    13: 'S',
    14: 'DB',
    15: 'DP',
    16: 'DST',
    17: 'K',
    18: 'P',
    19: 'HC',
    20: 'BE',
    21: 'IR',
    22: '',
    23: 'Flex RB_WR_TE',  # RB/WR/TE
    24: 'ER',
    25: 'Rookie'
}

PLAYER_STATS_MAP_ESPN = {
    # stat ID to stat name
    # Passing
    0: {'name': 'passingAttempts', 'display': 'Passing Attempts', 'fpros': 'pass_att'},  # PA
    1: {'name': 'passingCompletions', 'display': 'Completions', 'fpros': 'pass_cmp'},  # PC
    2: {'name': 'passingIncompletions', 'display': 'Incompletions'},  # INC
    3: {'name': 'passingYards', 'display': 'Passing Yards', 'fpros': 'pass_yds'},  # PY
    4: {'name': 'passingTouchdowns', 'display': 'Passing TDs', 'fpros': 'pass_tds'},  # PTD
    # 5-14 appear for passing players
    # 5-7: 6 is half of 5 (integer divide by 2), 7 is half of 6 (integer divide by 2)
    # 8-10: 9 is half of 8 (integer divide by 2), 10 is half of 9 (integer divide by 2)
    # 11-12: 12 is half of 11 (integer divide by 2)
    # 13-14: 14 is half of 13 (integer divide by 2)
    15: 'passing40PlusYardTD',  # PTD40
    16: 'passing50PlusYardTD',  # PTD50
    17: {'name': 'passing300To399YardGame', 'fpros': 'pass_yds_300'},  # P300
    18: {'name': 'passing400PlusYardGame', 'fpros': 'pass_yds_400'},  # P400
    19: {'name': 'passing2PtConversions', 'fpros': '2pt_tds'},  # 2PC
    20: {'name': 'passingInterceptions', 'display': 'Passing INTs', 'fpros': 'pass_ints'},  # INT
    21: 'passingCompletionPercentage',
    22: 'passingYardsPerGame',  # PY - avg per game

    # Rushing
    23: {'name': 'rushingAttempts', 'display': 'Rushing Attempts', 'frpos': 'rush_att'},  # RA
    24: {'name': 'rushingYards', 'display': 'Rushing Yards', 'fpros': 'rush_yds'},  # RY
    25: {'name': 'rushingTouchdowns', 'display': 'Rushing TDs', 'fpros': 'rush_tds'},  # RTD
    26: {'name': 'rushing2PtConversions', 'fpros': '2pt_tds'},  # 2PR
    # 27-34 appear for rushing players
    # 27-29: 28 is half of 27 (integer divide by 2), 29 is half of 28 (integer divide by 2)
    # 30-32: 31 is half of 30 (integer divide by 2), 32 is half of 31 (integer divide by 2)
    # 33-34: 34 is half of 33 (integer divide by 2)
    35: 'rushing40PlusYardTD',  # RTD40
    36: 'rushing50PlusYardTD',  # RTD50
    37: {'name': 'rushing100To199YardGame', 'fpros': 'rush_yds_100'},  # RY100
    38: {'name': 'rushing200PlusYardGame', 'fpros': 'rush_yds_200'},  # RY200
    39: 'rushingYardsPerAttempt',
    40: 'rushingYardsPerGame',  # RY - avg per game

    # Receiving
    41: {'name': 'receivingReceptions', 'display': 'Receptions', 'fpros': 'rec_rec'},  # REC
    42: {'name': 'receivingYards', 'display': 'Receiving Yards', 'fpros': 'rec_yds'},  # REY
    43: {'name': 'receivingTouchdowns', 'display': 'Receiving TDs', 'fpros': 'rec_tds'},  # RETD
    44: {'name': 'receiving2PtConversions', 'display': 'Receiving 2PC', 'fpros': '2pt_tds'},  # 2PRE
    45: 'receiving40PlusYardTD',  # RETD40
    46: 'receiving50PlusYardTD',  # RETD50
    # 47-52 appear for receiving players
    # 47-49: 48 is half of 47 (integer divide by 2), 49 is half of 48 (integer divide by 2)
    # 50-52: 51 is half of 50 (integer divide by 2), 52 is half of 51 (integer divide by 2)
    53: {'name': 'receivingReceptions', 'display': 'Receptions'},  # REC - TODO: figure out what the difference is between 53 and 41
    # 54-55 appear for receiving players
    # 54-55: 55 is half of 54 (integer divide by 2)
    56: 'receiving100To199YardGame',  # REY100
    57: 'receiving200PlusYardGame',  # REY200
    58: {'name': 'receivingTargets', 'display': 'Targets'},  # RET
    59: 'receivingYardsAfterCatch',
    60: 'receivingYardsPerReception',
    61: 'receivingYardsPerGame',  # REY - avg per game
    62: {'name': '2PtConversions', 'display': 'Two Point Conversions'},
    63: {'name': 'fumbleRecoveredForTD', 'display': 'Fumble Recovery Touchdown'},  # FTD
    64: 'passingTimesSacked',  # SK

    # Turnovers
    68: {'name': 'fumbles', 'display': 'Fumbles'},  # FUM
    72: {'name': 'lostFumbles', 'display': 'Fumbles Lost'},  # FUML
    73: {'name': 'turnovers', 'display': 'Turnovers'},

    # Kicking
    74: 'madeFieldGoalsFrom50Plus',  # FG50 (does not map directly to FG50 as FG50 does not include 60+)
    75: 'attemptedFieldGoalsFrom50Plus',  # FGA50 (does not map directly to FGA50 as FG50 does not include 60+)
    76: 'missedFieldGoalsFrom50Plus',  # FGM50 (does not map directly to FGM50 as FG50 does not include 60+)
    77: 'madeFieldGoalsFrom40To49',  # FG40
    78: 'attemptedFieldGoalsFrom40To49',  # FGA40
    79: 'missedFieldGoalsFrom40To49',  # FGM40
    80: 'madeFieldGoalsFromUnder40',  # FG0
    81: 'attemptedFieldGoalsFromUnder40',  # FGA0
    82: 'missedFieldGoalsFromUnder40',  # FGM0
    83: 'madeFieldGoals',  # FG
    84: 'attemptedFieldGoals',  # FGA
    85: 'missedFieldGoals',  # FGM
    86: 'madeExtraPoints',  # PAT
    87: 'attemptedExtraPoints',  # PATA
    88: 'missedExtraPoints',  # PATM

    # Defense
    89: 'defensive0PointsAllowed',  # PA0
    90: 'defensive1To6PointsAllowed',  # PA1
    91: 'defensive7To13PointsAllowed',  # PA7
    92: 'defensive14To17PointsAllowed',  # PA14
    93: 'defensiveBlockedKickForTouchdowns',  # BLKKRTD
    94: {'name': 'defensiveTouchdowns', 'display': 'Touchdowns', 'frpos': 'def_td'},  # Does not include defensive blocked kick for touchdowns (BLKKRTD)
    95: {'name': 'defensiveInterceptions', 'display': 'Interceptions', 'fpros': 'def_int'},  # INT
    96: {'name': 'defensiveFumbles', 'display': 'Fumbles Recovered', 'frpos': 'def_fr'},  # FR
    97: 'defensiveBlockedKicks',  # BLKK
    98: {'name': 'defensiveSafeties', 'display': 'Safeties', 'fpros': 'def_safety'},  # SF
    99: {'name': 'defensiveSacks', 'display': 'Sacks', 'fpros': 'def_sack'},  # SK
    # 100: This appears to be defensiveSacks * 2
    101: 'kickoffReturnTouchdowns',  # KRTD
    102: 'puntReturnTouchdowns',  # PRTD
    103: 'interceptionReturnTouchdowns',  # INTTD
    104: 'fumbleReturnTouchdowns',  # FRTD
    105: {'name': 'DSTTouchdowns', 'display': 'Total Touchdowns', 'fpros': 'def_td'},  # Includes defensive blocked kick for touchdowns (BLKKRTD) and kickoff/punt return touchdowns
    106: {'name': 'defensiveForcedFumbles', 'display': 'Forced Fumbles', 'frpos': 'def_ff'},  # FF
    107: 'defensiveAssistedTackles',  # TKA
    108: 'defensiveSoloTackles',  # TKS
    109: 'defensiveTotalTackles',  # TK
    113: 'defensivePassesDefensed',  # PD

    # Kick/Punt Returns
    114: 'kickoffReturnYards',  # KR
    115: 'puntReturnYards',  # PR
    118: 'puntsReturned',  # PTR

    # Team Defense Points Allowed
    120: {'name': 'defensivePointsAllowed', 'display': 'Points Allowed', 'fpros': 'def_pa'},  # PA
    121: 'defensive18To21PointsAllowed',  # PA18
    122: 'defensive22To27PointsAllowed',  # PA22
    123: 'defensive28To34PointsAllowed',  # PA28
    124: 'defensive35To45PointsAllowed',  # PA35
    125: 'defensive45PlusPointsAllowed',  # PA46

    # Team Defense Yards Allowed
    127: {'name': 'defensiveYardsAllowed', 'display': 'Yards Allowed', 'fpros': 'def_ytda'},  # YA
    128: 'defensiveLessThan100YardsAllowed',  # YA100
    129: 'defensive100To199YardsAllowed',  # YA199
    130: 'defensive200To299YardsAllowed',  # YA299
    131: 'defensive300To349YardsAllowed',  # YA349
    132: 'defensive350To399YardsAllowed',  # YA399
    133: 'defensive400To449YardsAllowed',  # YA449
    134: 'defensive450To499YardsAllowed',  # YA499
    135: 'defensive500To549YardsAllowed',  # YA549
    136: 'defensive550PlusYardsAllowed',  # YA550

    # Punting
    138: 'netPunts',  # PT
    139: 'puntYards',  # PTY
    140: 'puntsInsideThe10',  # PT10
    141: 'puntsInsideThe20',  # PT20
    142: 'blockedPunts',  # PTB
    145: 'puntTouchbacks',  # PTTB
    146: 'puntFairCatches',  # PTFC
    147: 'puntAverage',
    148: 'puntAverage44.0+',  # PTA44
    149: 'puntAverage42.0-43.9',  # PTA42
    150: 'puntAverage40.0-41.9',  # PTA40
    151: 'puntAverage38.0-39.9',  # PTA38
    152: 'puntAverage36.0-37.9',  # PTA36
    153: 'puntAverage34.0-35.9',  # PTA34
    154: 'puntAverage33.9AndUnder',  # PTA33

    # Head Coach
    155: 'teamWin',  # TW
    156: 'teamLoss',  # TL
    157: 'teamTie',  # TIE
    158: 'pointsScored',  # PTS
    160: 'pointsMargin',
    161: '25+pointWinMargin',  # WM25
    162: '20-24pointWinMargin',  # WM20
    163: '15-19pointWinMargin',  # WM15
    164: '10-14pointWinMargin',  # WM10
    165: '5-9pointWinMargin',  # WM5
    166: '1-4pointWinMargin',  # WM1
    167: '1-4pointLossMargin',  # LM1
    168: '5-9pointLossMargin',  # LM5
    169: '10-14pointLossMargin',  # LM10
    170: '15-19pointLossMargin',  # LM15
    171: '20-24pointLossMargin',  # LM20
    172: '25+pointLossMargin',  # LM25
    174: 'winPercentage',  # Value goes from 0-1

    187: 'defensivePointsAllowed',  # TODO: figure out what the difference is between 187 and 120

    # Field Goal extra
    201: 'madeFieldGoalsFrom60Plus',  # FG60
    202: 'attemptedFieldGoalsFrom60Plus',  # FGA60
    203: 'missedFieldGoalsFrom60Plus',  # FGM60

    205: 'defensive2PtReturns',  # 2PTRET
    206: 'defensive2PtReturns'  # 2PTRET - TODO: figure out what the difference is between 206 and 205
}

SETTINGS_SCORING_FORMAT_MAP_ESPN = {
    0: { 'abbr': 'PA', 'label': 'Each Pass Attempted', 'fpros': 'pass_att' },
    1: { 'abbr': 'PC', 'label': 'Each Pass Completed', 'fpros': 'pass_cmp' },
    2: { 'abbr': 'INC', 'label': 'Each Incomplete Pass' },
    3: { 'abbr': 'PY', 'label': 'Passing Yards', 'fpros': 'pass_yds' },
    4: { 'abbr': 'PTD', 'label': 'TD Pass', 'fpros': 'pass_tds' },
    5: { 'abbr': 'PY5', 'label': 'Every 5 passing yards' },
    6: { 'abbr': 'PY10', 'label': 'Every 10 passing yards' },
    7: { 'abbr': 'PY20', 'label': 'Every 20 passing yards' },
    8: { 'abbr': 'PY25', 'label': 'Every 25 passing yards' },
    9: { 'abbr': 'PY50', 'label': 'Every 50 passing yards' },
    10: { 'abbr': 'PY100', 'label': 'Every 100 passing yards' },
    11: { 'abbr': 'PC5', 'label': 'Every 5 pass completions' },
    12: { 'abbr': 'PC10', 'label': 'Every 10 pass completions' },
    13: { 'abbr': 'IP5', 'label': 'Every 5 pass incompletions' },
    14: { 'abbr': 'IP10', 'label': 'Every 10 pass incompletions' },
    15: { 'abbr': 'PTD40', 'label': '40+ yard TD pass bonus' },
    16: { 'abbr': 'PTD50', 'label': '50+ yard TD pass bonus' },
    17: { 'abbr': 'P300', 'label': '300-399 yard passing game', 'fpros': 'pass_yds_300' },
    18: { 'abbr': 'P400', 'label': '400+ yard passing game', 'fpros': 'pass_yds_400' },
    19: { 'abbr': '2PC', 'label': '2pt Passing Conversion', 'fpros': '2pt_tds' },
    20: { 'abbr': 'INTT', 'label': 'Interceptions Thrown', 'fpros': 'pass_ints' },
    21: { 'abbr': 'CPCT', 'label': 'Passing Completion Pct' },
    22: { 'abbr': 'PYPG', 'label': 'Passing Yards Per Game' },
    23: { 'abbr': 'RA', 'label': 'Rushing Attempts', 'fpros': 'rush_att' },
    24: { 'abbr': 'RY', 'label': 'Rushing Yards', 'fpros': 'rush_yds' },
    25: { 'abbr': 'RTD', 'label': 'TD Rush', 'fpros': 'rush_tds' },
    26: { 'abbr': '2PR', 'label': '2pt Rushing Conversion', 'fpros': '2pt_tds' },
    27: { 'abbr': 'RY5', 'label': 'Every 5 rushing yards' },
    28: { 'abbr': 'RY10', 'label': 'Every 10 rushing yards' },
    29: { 'abbr': 'RY20', 'label': 'Every 20 rushing yards' },
    30: { 'abbr': 'RY25', 'label': 'Every 25 rushing yards' },
    31: { 'abbr': 'RY50', 'label': 'Every 50 rushing yards' },
    32: { 'abbr': 'R100', 'label': 'Every 100 rushing yards' },
    33: { 'abbr': 'RA5', 'label': 'Every 5 rush attempts' },
    34: { 'abbr': 'RA10', 'label': 'Every 10 rush attempts' },
    35: { 'abbr': 'RTD40', 'label': '40+ yard TD rush bonus' },
    36: { 'abbr': 'RTD50', 'label': '50+ yard TD rush bonus' },
    37: { 'abbr': 'RY100', 'label': '100-199 yard rushing game', 'fpros': 'rush_yds_100' },
    38: { 'abbr': 'RY200', 'label': '200+ yard rushing game', 'fpros': 'rush_yds_200' },
    39: { 'abbr': 'RYPA', 'label': 'Rushing Yards Per Attempt' },
    40: { 'abbr': 'RYPG', 'label': 'Rushing Yards Per Game' },
    41: { 'abbr': 'RECS', 'label': 'Receptions', 'fpros': 'rec_rec' },
    42: { 'abbr': 'REY', 'label': 'Receiving Yards', 'fpros': 'rec_yds' },
    43: { 'abbr': 'RETD', 'label': 'TD Reception', 'fpros': 'rec_tds' },
    44: { 'abbr': '2PRE', 'label': '2pt Receiving Conversion', 'fpros': '2pt_tds' },
    45: { 'abbr': 'RETD40', 'label': '40+ yard TD rec bonus' },
    46: { 'abbr': 'RETD50', 'label': '50+ yard TD rec bonus' },
    47: { 'abbr': 'REY5', 'label': 'Every 5 receiving yards' },
    48: { 'abbr': 'REY10', 'label': 'Every 10 receiving yards' },
    49: { 'abbr': 'REY20', 'label': 'Every 20 receiving yards' },
    50: { 'abbr': 'REY25', 'label': 'Every 25 receiving yards' },
    51: { 'abbr': 'REY50', 'label': 'Every 50 receiving yards' },
    52: { 'abbr': 'RE100', 'label': 'Every 100 receiving yards' },
    53: { 'abbr': 'REC', 'label': 'Each reception' },
    54: { 'abbr': 'REC5', 'label': 'Every 5 receptions'},
    55: { 'abbr': 'REC10', 'label': 'Every 10 receptions' },
    56: { 'abbr': 'REY100', 'label': '100-199 yard receiving game', 'fpros': 'rec_yds_100' },
    57: { 'abbr': 'REY200', 'label': '200+ yard receiving game', 'fpros': 'rec_yds_200' },
    58: { 'abbr': 'RET', 'label': 'Receiving Target' },
    59: { 'abbr': 'YAC', 'label': 'Receiving Yards After Catch' },
    60: { 'abbr': 'YPC', 'label': 'Receiving Yards Per Catch' },
    61: { 'abbr': 'REYPG', 'label': 'Receiving Yards Per Game' },
    62: { 'abbr': 'PTL', 'label': 'Total 2pt Conversions', 'fpros': '2pt_tds' },
    63: { 'abbr': 'FTD', 'label': 'Fumble Recovered for TD' },
    64: { 'abbr': 'SKD', 'label': 'Sacked' },
    65: { 'abbr': 'PFUM', 'label': 'Passing Fumbles' },
    66: { 'abbr': 'RFUM', 'label': 'Rushing Fumbles' },
    67: { 'abbr': 'REFUM', 'label': 'Receiving Fumbles' },
    68: { 'abbr': 'FUM', 'label': 'Total Fumbles' },
    69: { 'abbr': 'PFUML', 'label': 'Passing Fumbles Lost' },
    70: { 'abbr': 'RFUML', 'label': 'Rushing Fumbles Lost' },
    71: { 'abbr': 'REFUML', 'label': 'Receiving Fumbles Lost' },
    72: { 'abbr': 'FUML', 'label': 'Total Fumbles Lost', 'fpros': 'fumbles' },
    73: { 'abbr': 'TT', 'label': 'Total Turnovers' },
    74: { 'abbr': 'FG50P', 'label': 'FG Made (50+ yards)' },
    75: { 'abbr': 'FGA50P', 'label': 'FG Attempted (50+ yards)' },
    76: { 'abbr': 'FGM50P', 'label': 'FG Missed (50+ yards)' },
    77: { 'abbr': 'FG40', 'label': 'FG Made (40-49 yards)' },
    78: { 'abbr': 'FGA40', 'label': 'FG Attempted (40-49 yards)' },
    79: { 'abbr': 'FGM40', 'label': 'FG Missed (40-49 yards)' },
    80: { 'abbr': 'FG0', 'label': 'FG Made (0-39 yards)' },
    81: { 'abbr': 'FGA0', 'label': 'FG Attempted (0-39 yards)' },
    82: { 'abbr': 'FGM0', 'label': 'FG Missed (0-39 yards)' },
    83: { 'abbr': 'FG', 'label': 'Total FG Made' },
    84: { 'abbr': 'FGA', 'label': 'Total FG Attempted' },
    85: { 'abbr': 'FGM', 'label': 'Total FG Missed' },
    86: { 'abbr': 'PAT', 'label': 'Each PAT Made' },
    87: { 'abbr': 'PATA', 'label': 'Each PAT Attempted' },
    88: { 'abbr': 'PATM', 'label': 'Each PAT Missed' },
    89: { 'abbr': 'PA0', 'label': '0 points allowed' },
    90: { 'abbr': 'PA1', 'label': '1-6 points allowed' },
    91: { 'abbr': 'PA7', 'label': '7-13 points allowed' },
    92: { 'abbr': 'PA14', 'label': '14-17 points allowed' },
    93: { 'abbr': 'BLKKRTD', 'label': 'Blocked Punt or FG return for TD' },
    94: { 'abbr': 'DEFRETTD', 'label': 'Fumble or INT Return for TD' },
    95: { 'abbr': 'INT', 'label': 'Each Interception', 'fpros': 'def_int' },
    96: { 'abbr': 'FR', 'label': 'Each Fumble Recovered', 'fpros': 'def_fr' },
    97: { 'abbr': 'BLKK', 'label': 'Blocked Punt, PAT or FG' },
    98: { 'abbr': 'SF', 'label': 'Each Safety', 'frpos': 'def_safety' },
    99: { 'abbr': 'SK', 'label': 'Each Sack', 'fpros': 'def_sack' },
    100: { 'abbr': 'HALFSK', 'label': '1/2 Sack' },
    101: { 'abbr': 'KRTD', 'label': 'Kickoff Return TD' },
    102: { 'abbr': 'PRTD', 'label': 'Punt Return TD' },
    103: { 'abbr': 'INTTD', 'label': 'Interception Return TD' },
    104: { 'abbr': 'FRTD', 'label': 'Fumble Return TD' },
    105: { 'abbr': 'TRTD', 'label': 'Total Return TD', 'fpros': 'def_retd' },
    106: { 'abbr': 'FF', 'label': 'Each Fumble Forced', 'fpros': 'def_ff' },
    107: { 'abbr': 'TKA', 'label': 'Assisted Tackles' },
    108: { 'abbr': 'TKS', 'label': 'Solo Tackles' },
    109: { 'abbr': 'TK', 'label': 'Total Tackles' },
    110: { 'abbr': 'TK3', 'label': 'Every 3 Total Tackles' },
    111: { 'abbr': 'TK5', 'label': 'Every 5 Total Tackles' },
    112: { 'abbr': 'STF', 'label': 'Stuffs' },
    113: { 'abbr': 'PD', 'label': 'Passes Defensed' },
    114: { 'abbr': 'KR', 'label': 'Kickoff Return Yards' },
    115: { 'abbr': 'PR', 'label': 'Punt Return Yards' },
    116: { 'abbr': 'KR10', 'label': 'Every 10 kickoff return yards' },
    117: { 'abbr': 'KR25', 'label': 'Every 25 kickoff return yards' },
    118: { 'abbr': 'PR10', 'label': 'Every 10 punt return yards' },
    119: { 'abbr': 'PR25', 'label': 'Every 25 punt return yards' },
    120: { 'abbr': 'PTSA', 'label': 'Points Allowed', 'fpros': 'def_pa' },
    121: { 'abbr': 'PA18', 'label': '18-21 points allowed' },
    122: { 'abbr': 'PA22', 'label': '22-27 points allowed' },
    123: { 'abbr': 'PA28', 'label': '28-34 points allowed' },
    124: { 'abbr': 'PA35', 'label': '35-45 points allowed' },
    125: { 'abbr': 'PA46', 'label': '46+ points allowed' },
    126: { 'abbr': 'PAPG', 'label': 'Points Allowed Per Game' },
    127: { 'abbr': 'YA', 'label': 'Yards Allowed', 'fpros': 'def_tyda' },
    128: { 'abbr': 'YA100', 'label': 'Less than 100 total yards allowed' },
    129: { 'abbr': 'YA199', 'label': '100-199 total yards allowed' },
    130: { 'abbr': 'YA299', 'label': '200-299 total yards allowed' },
    131: { 'abbr': 'YA349', 'label': '300-349 total yards allowed' },
    132: { 'abbr': 'YA399', 'label': '350-399 total yards allowed' },
    133: { 'abbr': 'YA449', 'label': '400-449 total yards allowed' },
    134: { 'abbr': 'YA499', 'label': '450-499 total yards allowed' },
    135: { 'abbr': 'YA549', 'label': '500-549 total yards allowed' },
    136: { 'abbr': 'YA550', 'label': '550+ total yards allowed' },
    137: { 'abbr': 'YAPG', 'label': 'Yards Allowed Per Game' },
    138: { 'abbr': 'PT', 'label': 'Net Punts' },
    139: { 'abbr': 'PTY', 'label': 'Punt Yards' },
    140: { 'abbr': 'PT10', 'label': 'Punts Inside the 10' },
    141: { 'abbr': 'PT20', 'label': 'Punts Inside the 20' },
    142: { 'abbr': 'PTB', 'label': 'Blocked Punts' },
    143: { 'abbr': 'PTR', 'label': 'Punts Returned' },
    144: { 'abbr': 'PTRY', 'label': 'Punt Return Yards' },
    145: { 'abbr': 'PTTB', 'label': 'Touchbacks' },
    146: { 'abbr': 'PTFC', 'label': 'Fair Catches' },
    147: { 'abbr': 'PTAVG', 'label': 'Punt Average' },
    148: { 'abbr': 'PTA44', 'label': 'Punt Average 44.0+' },
    149: { 'abbr': 'PTA42', 'label': 'Punt Average 42.0-43.9' },
    150: { 'abbr': 'PTA40', 'label': 'Punt Average 40.0-41.9' },
    151: { 'abbr': 'PTA38', 'label': 'Punt Average 38.0-39.9' },
    152: { 'abbr': 'PTA36', 'label': 'Punt Average 36.0-37.9' },
    153: { 'abbr': 'PTA34', 'label': 'Punt Average 34.0-35.9' },
    154: { 'abbr': 'PTA33', 'label': 'Punt Average 33.9 or less' },
    155: { 'abbr': 'TW', 'label': 'Team Win' },
    156: { 'abbr': 'TL', 'label': 'Team Loss' },
    157: { 'abbr': 'TIE', 'label': 'Team Tie' },
    158: { 'abbr': 'PTS', 'label': 'Points Scored' },
    159: { 'abbr': 'PPG', 'label': 'Points Scored Per Game' },
    160: { 'abbr': 'MGN', 'label': 'Margin of Victory' },
    161: { 'abbr': 'WM25', 'label': '25+ point Win Margin' },
    162: { 'abbr': 'WM20', 'label': '20-24 point Win Margin' },
    163: { 'abbr': 'WM15', 'label': '15-19 point Win Margin' },
    164: { 'abbr': 'WM10', 'label': '10-14 point Win Margin' },
    165: { 'abbr': 'WM5', 'label': '5-9 point Win Margin' },
    166: { 'abbr': 'WM1', 'label': '1-4 point Win Margin' },
    167: { 'abbr': 'LM1', 'label': '1-4 point Loss Margin' },
    168: { 'abbr': 'LM5', 'label': '5-9 point Loss Margin' },
    169: { 'abbr': 'LM10', 'label': '10-14 point Loss Margin' },
    170: { 'abbr': 'LM15', 'label': '15-19 point Loss Margin' },
    171: { 'abbr': 'LM20', 'label': '20-24 point Loss Margin' },
    172: { 'abbr': 'LM25', 'label': '25+ point Loss Margin' },
    173: { 'abbr': 'MGNPG', 'label': 'Margin of Victory Per Game' },
    174: { 'abbr': 'WINPCT', 'label': 'Winning Pct' },
    175: { 'abbr': 'PTD0', 'label': '0-9 yd TD pass bonus' },
    176: { 'abbr': 'PTD10', 'label': '10-19 yd TD pass bonus' },
    177: { 'abbr': 'PTD20', 'label': '20-29 yd TD pass bonus' },
    178: { 'abbr': 'PTD30', 'label': '30-39 yd TD pass bonus' },
    179: { 'abbr': 'RTD0', 'label': '0-9 yd TD rush bonus' },
    180: { 'abbr': 'RTD10', 'label': '10-19 yd TD rush bonus' },
    181: { 'abbr': 'RTD20', 'label': '20-29 yd TD rush bonus' },
    182: { 'abbr': 'RTD30', 'label': '30-39 yd TD rush bonus' },
    183: { 'abbr': 'RETD0', 'label': '0-9 yd TD rec bonus' },
    184: { 'abbr': 'RETD10', 'label': '10-19 yd TD rec bonus' },
    185: { 'abbr': 'RETD20', 'label': '20-29 yd TD rec bonus' },
    186: { 'abbr': 'RETD30', 'label': '30-39 yd TD rec bonus' },
    187: { 'abbr': 'DPTSA', 'label': 'D/ST Points Allowed' },
    188: { 'abbr': 'DPA0', 'label': 'D/ST 0 points allowed' },
    189: { 'abbr': 'DPA1', 'label': 'D/ST 1-6 points allowed' },
    190: { 'abbr': 'DPA7', 'label': 'D/ST 7-13 points allowed' },
    191: { 'abbr': 'DPA14', 'label': 'D/ST 14-17 points allowed' },
    192: { 'abbr': 'DPA18', 'label': 'D/ST 18-21 points allowed' },
    193: { 'abbr': 'DPA22', 'label': 'D/ST 22-27 points allowed' },
    194: { 'abbr': 'DPA28', 'label': 'D/ST 28-34 points allowed' },
    195: { 'abbr': 'DPA35', 'label': 'D/ST 35-45 points allowed' },
    196: { 'abbr': 'DPA46', 'label': 'D/ST 46+ points allowed' },
    197: { 'abbr': 'DPAPG', 'label': 'D/ST Points Allowed Per Game' },
    198: { 'abbr': 'FG50', 'label': 'FG Made (50-59 yards)' },
    199: { 'abbr': 'FGA50', 'label': 'FG Attempted (50-59 yards)' },
    200: { 'abbr': 'FGM50', 'label': 'FG Missed (50-59 yards)' },
    201: { 'abbr': 'FG60', 'label': 'FG Made (60+ yards)' },
    202: { 'abbr': 'FGA60', 'label': 'FG Attempted (60+ yards)' },
    203: { 'abbr': 'FGM60', 'label': 'FG Missed (60+ yards)' },
    204: { 'abbr': 'O2PRET', 'label': 'Offensive 2pt Return' },
    205: { 'abbr': 'D2PRET', 'label': 'Defensive 2pt Return' },
    206: { 'abbr': '2PRET', 'label': '2pt Return' },
    207: { 'abbr': 'O1PSF', 'label': 'Offensive 1pt Safety' },
    208: { 'abbr': 'D1PSF', 'label': 'Defensive 1pt Safety' },
    209: { 'abbr': '1PSF', 'label': '1pt Safety' },
    210: { 'abbr': 'GP', 'label': 'Games Played' },
    211: { 'abbr': 'PFD', 'label': 'Passing First Down' },
    212: { 'abbr': 'RFD', 'label': 'Rushing First Down' },
    213: { 'abbr': 'REFD', 'label': 'Receiving First Down' },
    214: { 'abbr': 'FGY', 'label': 'FG Made Yards' },
    215: { 'abbr': 'FGMY', 'label': 'FG Missed Yards' },
    216: { 'abbr': 'FGAY', 'label': 'FG Attempt Yards' },
    217: { 'abbr': 'FGY5', 'label': 'Every 5 FG Made yards' },
    218: { 'abbr': 'FGY10', 'label': 'Every 10 FG Made yards' },
    219: { 'abbr': 'FGY20', 'label': 'Every 20 FG Made yards' },
    220: { 'abbr': 'FGY25', 'label': 'Every 25 FG Made yards' },
    221: { 'abbr': 'FGY50', 'label': 'Every 50 FG Made yards' },
    222: { 'abbr': 'FGY100', 'label': 'Every 100 FG Made yards' },
    223: { 'abbr': 'FGMY5', 'label': 'Every 5 FG Missed yards' },
    224: { 'abbr': 'FGMY10', 'label': 'Every 10 FG Missed yards' },
    225: { 'abbr': 'FGMY20', 'label': 'Every 20 FG Missed yards' },
    226: { 'abbr': 'FGMY25', 'label': 'Every 25 FG Missed yards' },
    227: { 'abbr': 'FGMY50', 'label': 'Every 50 FG Missed yards' },
    228: { 'abbr': 'FGMY100', 'label': 'Every 100 FG Missed yards' },
    229: { 'abbr': 'FGAY5', 'label': 'Every 5 FG Attempt yards' },
    230: { 'abbr': 'FGAY10', 'label': 'Every 10 FG Attempt yards' },
    231: { 'abbr': 'FGAY20', 'label': 'Every 20 FG Attempt yards' },
    232: { 'abbr': 'FGAY25', 'label': 'Every 25 FG Attempt yards' },
    233: { 'abbr': 'FGAY50', 'label': 'Every 50 FG Attempt yards' },
    234: { 'abbr': 'FGAY100', 'label': 'Every 100 FG Attempt yards' }
}


TEAM_IDS = {
    # add new teams here
    '{04E660A8-5B4E-4B6C-AD79-AF6820D2904A}': {
        'active': True,
        'name': {
            'first': 'Aditya',
            'last': 'Parikh',
            'display': 'Adit'
        }
    },

    '{107907DD-E9E2-426A-81C1-33FB7AA6983B}': {
        'active': False,
        'name': {'first': 'Sharan',
                 'last': 'Gottumukkala',
                 'display': 'Shar'
        }
    },

    '{127A0B03-FD89-4462-AE01-840A18124086}': {
        'active': True,
        'name': {
            'first': 'Ayaz',
            'last': 'Ghesani',
            'display': 'Ayaz'
        }
    },

    '{15FA7955-FCA6-4E11-8D73-9EB30DD67D0B}': {
        'active': False,
        'name': {
            'first': 'Vikram',
            'last': 'Kesavabhotla',
            'display': 'Vikr'
        }
    },

    '{2EA590DD-55F5-41CF-A29F-AC67B612265A}': {
        'active': True,
        'name': {
            'first': 'Varun',
            'last': 'Viswanathan',
            'display': 'Varu'
        }
    },

    '{377D02F0-6C7C-4333-9D4B-DAB9EDD9A44D}': {
        'active': True,
        'name': {
            'first': 'Akshat',
            'last': 'Rajan',
            'display': 'Aksh'
        }
    },

    '{89D51209-9763-4BC1-9512-0997634BC139}': {
        'active': False,
        'name': {
            'first': 'Faizan',
            'last': 'Khan',
            'display': 'Faiz'
        }
    },

    '{C152DDDA-D6A5-4B19-B4C8-3B60D3A5784F}': {
        'active': False,
        'name': {
            'first': 'Harsh',
            'last': 'Randhawa',
            'display': 'Hars'
        }
    },

    '{DFDE661C-852D-422F-99C9-0D06AD1B9B2D}': {
        'active': True,
        'name': {
            'first': 'Charles',
            'last': 'Cai',
            'display': 'Char'
        }
    },

    '{E01C2393-2E6F-420B-9C23-932E6F720B61}': {
        'active': True,
        'name': {
            'first': 'Hirsh',
            'last': 'Gupta',
            'display': 'Hirs'
        }
    },

    '{EB1CD420-9D9A-4649-873A-1A97DEFB5542}': {
        'active': True,
        'name': {
            'first': 'Nick',
            'last': 'Shekar',
            'display': 'Nick'
        }
    },

    '{FB094EC3-E4D2-4E81-AAA6-1D776B8259C7}': {
        'active': True,
        'name': {
            'first': 'Aaron',
            'last': 'Srikantha',
            'display': 'Aaro'
        }
    },

    '{95160076-FE63-41C0-9600-76FE63B1C0DD}': {
        'active': True,
        'name': {
            'first': 'Arjun',
            'last': 'Bains',
            'display': 'Arju'
        }
    },

    '{52EF6954-9BFF-4A41-9617-1ECD3F5EEBAF}': {
        'active': True,
        'name': {
            'first': 'Aiden',
            'last': 'Ghesani',
            'display': 'Aide'
        }
    },

    '{32DFE3C4-263C-4F21-A13A-710BDE67C258}': {
        'active': False,
        'name': {
            'first': 'Suraj',
            'last': 'Nyalakonda',
            'display': 'Sura'
        }
    },

    '{A97F7F21-227B-428E-BF7F-21227B028EF9}': {
        'active': False,
        'name': {
            'first': 'Rahul',
            'last': 'U',
            'display': 'Rahu'
        }
    }
}
