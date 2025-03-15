from scripts.utils import constants as const
import requests
import json


class DataLoader:
    def __init__(self,
                 year=const.SEASON,
                 league_id=const.LEAGUE_ID,
                 swid=const.SWID,
                 espn_s2=const.ESPN_S2):
        self.year = year
        self.league_id = league_id
        self.swid = swid
        self.espn_s2 = espn_s2

    def _loader(self, view):
        url = f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/' \
              f'{int(self.year)}' \
              f'/segments/0/leagues/' \
              f'{int(self.league_id)}' \
              f'?view={view}'
        headers = None

        if view == 'kona_player_info':
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
                         cookies={
                             'SWID': self.swid,
                             'espn_s2': self.espn_s2
                         },
                         headers=headers)

        d = r.json()

        return d

    def load_week(self, week):
        url = f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/' \
              f'{int(self.year)}' \
              f'/segments/0/leagues/' \
              f'{int(self.league_id)}' \
              f'?view=mMatchupScore&view=mMatchup&view=mTeam&view=mSettings'
        r = requests.get(url,
                         cookies={
                             'SWID': self.swid,
                             'espn_s2': self.espn_s2
                         },
                         params={
                             'scoringPeriodId': week,
                             'matchupPeriodId': week
                         })
        d = r.json()

        return d

    def settings(self):
        return self._loader(view='mSettings')

    def draft(self):
        return self._loader(view='mDraftDetail')

    def teams(self):
        return self._loader(view='mTeam')

    def scores(self, week=None):
        data = self._loader(view='mMatchupScore')
        if week:
            return {'schedule': [x for x in data['schedule'] if x["matchupPeriodId"] == week]}
        else:
            return {'schedule': data['schedule']}

    def matchups(self, week=None):
        data = self._loader(view='mMatchup')
        if week:
            return {'schedule': [x for x in data['schedule'] if x["matchupPeriodId"] == week]}
        else:
            return {'schedule': data['schedule']}

    def nav(self):
        return self._loader(view='mNav')

    def players(self):
        return self._loader(view='kona_player_info')

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
