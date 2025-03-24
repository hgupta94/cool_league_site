from scripts.utils import constants
import requests


def get_bye_weeks():
    nfl_team_ids = constants.NFL_TEAM_MAP
    test = {}
    for nfl_id, abbrev in nfl_team_ids.items():
        url = f'https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{nfl_id}/schedule'
        r = requests.get(url)
        d = r.json()
        test[nfl_id] = {'abbreviation': abbrev, 'bye_week': d['byeWeek']}
    return test


url = f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/' \
      f'{2024}' \
      f'/segments/0/leagues/' \
      f'{1382012}' \
      f'?view=kona_playercard'
r = requests.get(url,
                 cookies={
                     'SWID': constants.SWID,
                     'espn_s2': constants.ESPN_S2
                 })
d = r.json()