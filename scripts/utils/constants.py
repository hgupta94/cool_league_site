# ESPN API parameters
SEASON = 2024
LEAGUE_ID = 1382012
SWID = "{E01C2393-2E6F-420B-9C23-932E6F720B61}"
ESPN_S2 = "AEAVE3tAjA%2B4WQ04t%2FOYl15Ye5f640g8AHGEycf002gEwr1Q640iAvRF%2BRYFiNw5T8GSED%2FIG9HYOx7iwYegtyVzOeY%2BDhSYCOJrCGevkDgBrhG5EhXMnmiO2GpeTbrmtHmFZAsao0nYaxiKRvfYNEVuxrCHWYewD3tKFa923lw3NC8v5qjjtljN%2BkwFXSkj91k2wxBjrdaL5Pp1Y77%2FDzQza4%2BpyJq225y4AUPNB%2FCKOXYF7DTZ5B%2BbuHfyUKImvLaNJUTpwVXR74dk2VUMD9St"

# MySQL parameters
# SSH_HOST = 'ssh.pythonanywhere.com'
# SSH_PASS = '!)2EJ2*PbzwWVUY'
# USERNAME = 'hgupta'
# DB_PASS = 'chillffl'
# DB_HOST = 'hgupta.mysql.pythonanywhere-services.com'
# DB = 'hgupta$chill'
USERNAME = 'root'
DB_PASS = 'Yucca090616!'
DB_HOST = '127.0.0.1'
DB = 'chill'

# ESPN mappings
ESPN_TEAM_MAP = {
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

ESPN_POSITION_MAP = {
    0:  'QB',
    2:  'RB',
    4:  'WR',
    6:  'TE',
    16: 'DST'
}

SLOTCODES = {
    0:  'QB',
    # 1:  'TQB',
    2:  'RB',
    3:  'Flex',
    4:  'WR',
    # 5: 'WR/TE',
    6: 'TE',
    # 7: 'OP',
    # 8: 'DT',
    # 9: 'DE',
    # 10: 'LB',
    # 11: 'DL',
    # 12: 'CB',
    # 13: 'S',
    # 14: 'DB',
    # 15: 'DP',
    16: 'DST',
    17: 'K',
    # 18: 'P',
    # 19: 'HC',
    20: 'BE',
    21: 'IR',
    22: '',
    23: 'Flex'  # RB/WR/TE
    # 24: 'ER',
    # 25: 'Rookie'
}

TEAM_IDS = {
    # add new teams here
    '{04E660A8-5B4E-4B6C-AD79-AF6820D2904A}': {
        'name': {
            'first': 'Aditya',
            'last': 'Parikh',
            'display': 'Adit'
        }
    },
    '{107907DD-E9E2-426A-81C1-33FB7AA6983B}': {
        'name': {'first': 'Sharan',
                 'last': 'Gottumukkala',
                 'display': 'Shar'
        }
    },

    '{127A0B03-FD89-4462-AE01-840A18124086}': {
        'name': {
            'first': 'Ayaz',
            'last': 'Ghesani',
            'display': 'Ayaz'
        }
    },

    '{15FA7955-FCA6-4E11-8D73-9EB30DD67D0B}': {
        'name': {
            'first': 'Vikram',
            'last': 'Kesavabhotla',
            'display': 'Vikr'
        }
    },

    '{2EA590DD-55F5-41CF-A29F-AC67B612265A}': {
        'name': {
            'first': 'Varun',
            'last': 'Viswanathan',
            'display': 'Varu'
        }
    },

    '{377D02F0-6C7C-4333-9D4B-DAB9EDD9A44D}': {
        'name': {
            'first': 'Akshat',
            'last': 'Rajan',
            'display': 'Aksh'
        }
    },

    '{89D51209-9763-4BC1-9512-0997634BC139}': {
        'name': {
            'first': 'Faizan',
            'last': 'Khan',
            'display': 'Faiz'
        }
    },

    '{C152DDDA-D6A5-4B19-B4C8-3B60D3A5784F}': {
        'name': {
            'first': 'Harsh',
            'last': 'Randhawa',
            'display': 'Hars'
        }
    },

    '{DFDE661C-852D-422F-99C9-0D06AD1B9B2D}': {
        'name': {
            'first': 'Charles',
            'last': 'Cai',
            'display': 'Char'
        }
    },

    '{E01C2393-2E6F-420B-9C23-932E6F720B61}': {
        'name': {
            'first': 'Hirsh',
            'last': 'Gupta',
            'display': 'Hirs'
        }
    },

    '{EB1CD420-9D9A-4649-873A-1A97DEFB5542}': {
        'name': {
            'first': 'Nick',
            'last': 'Shekar',
            'display': 'Nick'
        }
    },

    '{FB094EC3-E4D2-4E81-AAA6-1D776B8259C7}': {
        'name': {
            'first': 'Aaron',
            'last': 'Srikantha',
            'display': 'Aaro'
        }
    },

    '{95160076-FE63-41C0-9600-76FE63B1C0DD}': {
        'name': {
            'first': 'Arjun',
            'last': 'Bains',
            'display': 'Arju'
        }
    }
}

# standings column mapping
STANDINGS_COL_MAP_2018_2020 = {
    'team': 'Team',
    'm_record': 'Record',
    'win_perc': 'Win%',
    'total_pf': 'Points',
    'wb4': 'WB-4'
}

STANDINGS_COL_MAP_2021_CURR = {
    'team': 'Team',
    'ov_record': 'Overall',
    'win_perc': 'Win%',
    'm_record': 'Matchup',
    'thw_record': 'THW',
    'total_pf': 'Points',
    'wb2': 'WB-Bye',
    'wb5': 'WB-5',
    'pb6': 'PB-6'
}
