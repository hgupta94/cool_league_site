from scripts.utils import constants as const
import requests
import json


class DataLoader:
    """Load a view from ESPN's API"""

    def __init__(self,
                 year: int = const.SEASON,
                 league_id: int = const.LEAGUE_ID,
                 swid: str = const.SWID,
                 espn_s2: str = const.ESPN_S2,
                 week: int = None):
        self.year = year
        self.league_id = league_id
        self.swid = swid
        self.espn_s2 = espn_s2
        self.week = week

    def _loader(self, view: str):
        # construct url, headers, and parameters
        url = f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/' \
              f'{int(self.year)}' \
              f'/segments/0/leagues/' \
              f'{int(self.league_id)}' \
              f'?view={view}'
        headers = None

        if view == 'kona_player_info':
            filters = {
                'players': {
                    'limit': 1000,
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

        params = {
            'scoringPeriodId': self.week,
            'matchupPeriodId': self.week
        }

        r = requests.get(url,
                         cookies={
                             'SWID': self.swid,
                             'espn_s2': self.espn_s2
                         },
                         headers=headers,
                         params=params)

        d = r.json()

        return d

    def load_week(self, week):
        url = f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/' \
              f'{int(self.year)}' \
              f'/segments/0/leagues/' \
              f'{int(self.league_id)}'
        r = requests.get(url + '?view=mMatchup&view=mMatchupScore',
                         params={'scoringPeriodId': week, 'matchupPeriodId': week},
                         cookies={'SWID': self.swid, 'espn_s2': self.espn_s2})

        return r.json()
        # return self._loader(view='mMatchupScore&view=mMatchup&view=mTeam&view=mSettings')

    def settings(self):
        return self._loader(view='mSettings')

    def draft(self):
        return self._loader(view='mDraftDetail')

    def teams(self):
        return self._loader(view='mTeam')

    def scores(self):
        data = self._loader(view='mMatchupScore')
        if self.week:
            return {'schedule': [x for x in data['schedule'] if x["matchupPeriodId"] == self.week]}
        else:
            return {'schedule': data['schedule']}

    def matchups(self):
        data = self._loader(view='mMatchup')
        if self.week:
            return {'schedule': [x for x in data['schedule'] if x["matchupPeriodId"] <= self.week]}
        else:
            return {'schedule': data['schedule']}

    def nav(self):
        return self._loader(view='mNav')

    def players_info(self):
        return self._loader(view='kona_player_info')

    def players_wl(self):
        return self._loader(view='players_wl')

    def players_card(self):
        return self._loader(view='kona_playercard')

    def transactions(self):
        return self._loader(view='mTransactions2')

    def status(self):
        return self._loader(view='mStatus')

    def game_state(self):
        return self._loader(view='kona_game_state')

    def nfl_schedule(self):
        return self._loader(view='proTeamSchedules_wl')

    def league_comms(self):
        return self._loader(view='kona_league_communication')
