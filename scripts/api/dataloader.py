from scripts.utils import constants as const

from cachetools.func import ttl_cache
import logging
import requests
import json


class DataLoader:
    """Load a view from ESPN's API"""
    def __init__(
            self,
            year: int = const.SEASON,
            week: int = None,
            league_id: int = const.LEAGUE_ID,
            swid: str = const.SWID,
            espn_s2: str = const.ESPN_S2
    ):
        self.year = year
        self.week = week
        self.league_id = str(league_id)
        self.swid = swid
        self.espn_s2 = espn_s2
        self.endpoint = f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl'

    def _loader(
            self,
            view: str,
            filters: dict = None
    ) -> dict[str, dict]:
        if self.year >= 2018:
            url = f'{self.endpoint}/seasons/{self.year}/segments/0/leagues/{self.league_id}?view={view}'
        else:
            # data before 2018 stored in this endpoint
            url = f'{self.endpoint}/leagueHistory/{self.league_id}?seasonId={self.year}&view={view}'

        headers = None
        if filters:
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

        return d if self.year >= 2018 else d[0]

    @ttl_cache(maxsize=1, ttl=300)
    def settings(self):
        return self._loader(view='mSettings')

    def draft(self):
        return self._loader(view='mDraftDetail')

    @ttl_cache(maxsize=1, ttl=300)
    def teams(self):
        return self._loader(view='mTeam')

    @ttl_cache(maxsize=1, ttl=300)
    def rosters(self):
        return self._loader(view='mRoster')

    def standings(self):
        return self._loader(view='mStandings')

    def week_scores(self, week: int):
        if not week:
            week = self.week
        data = self._loader(view='mMatchup')
        matchups = [m for m in data['schedule'] if m['matchupPeriodId'] == week]
        if week:
            scores = []
            for m in matchups:
                for i, tm in enumerate(['home', 'away']):
                    try:
                        team_entry = m[tm]
                        scores.append(team_entry['totalPoints'])
                    except KeyError:
                        continue
            return scores
        else:
            raise ValueError('Must specify week')

    def all_scores(self):
        scores = {}
        for i in range(1, self.week+1):
            week_scores = self.week_scores(week=i)
            scores[i] = sorted(week_scores)
        return scores

    @ttl_cache(maxsize=1, ttl=300)
    def matchups(self):
        data = self._loader(view='mMatchup')
        if self.week:
            return {'schedule': [x for x in data['schedule'] if x["matchupPeriodId"] <= self.week]}
        else:
            return {'schedule': data['schedule']}

    def nav(self):
        return self._loader(view='mNav')

    @ttl_cache(maxsize=1, ttl=300)
    def players_info(self, n: int = 500):
        filters = {
            'players': {
                'limit': n,
                'sortDraftRanks': {
                    'sortPriority': 100,
                    'sortAsc': True,
                    'value': 'PPR'
                }
            }
        }
        return self._loader(view='kona_player_info', filters=filters)

    def players_wl(self):
        return self._loader(view='players_wl')

    def players_card(self):
        return self._loader(view='kona_playercard')

    @ttl_cache(maxsize=1, ttl=300)
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
