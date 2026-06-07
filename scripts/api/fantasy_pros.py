import requests
import logging
import os

from cachetools.func import ttl_cache
from dotenv import load_dotenv

from scripts.utils import constants
from scripts.api.dataloader import DataLoader
from scripts.api.settings import LeagueSettings, RosterSettings


class FantasyPros:
    def __init__(
            self,
            dataloader: DataLoader,
            season: int = None,
            week: int = None,
            mapping: dict = None
    ):
        """
        :param dataloader: ESPN Dataloader object
        :param mapping: dictionary of Fantasy Pros to desired external source player IDs
        """
        load_dotenv()
        api_key = os.getenv('FPROS_KEY')
        self.base_url = 'https://api.fantasypros.com/public/v2/json/nfl'
        self.headers = {'x-api-key': api_key}

        self.season = season
        if not season:
            self.season = constants.SEASON
        self.week = week
        if not week:
            self.week = constants.WEEK

        self.league_settings = LeagueSettings(dataloader=dataloader)
        self.roster_settings = RosterSettings(dataloader=dataloader)

        self.mapping = mapping

        self.ppr_dict = {
            '0': 'points',
            '0.5': 'points_half',
            '1': 'points_ppr',
            'points': 0,
            'points_half': 0.5,
            'points_ppr': 1
        }
        self.proj_col = self.ppr_dict[str(self.league_settings.ppr_type)]

    def _loader(self, endpoint: str, params: dict = None):
        if endpoint not in {'players', 'projections'}:
            raise ValueError(f'Endpoint {endpoint} is not supported. Must be one of: '
                             f'["players", "news", "compare-players", "rankings", "consensus-rankings", "experts", "projections"]')

        if endpoint in {'players', 'news', 'injuries', 'compare-players'}:
            url = f'{self.base_url}/{endpoint}'
        else:
            url = f'{self.base_url}/{self.season}/{endpoint}'
            if endpoint == 'experts':
                url += '/rankings/experts'

        r = requests.get(url, params=params, headers=self.headers)
        r.raise_for_status()
        return r.json()

    @ttl_cache(maxsize=1, ttl=3600)
    def get_player_info(
            self,
            external_ids: tuple[str] = ('espn',),
            player_ids: tuple[int] = None
    ) -> dict:
        """
        Fantasy Pros player info

        :external_ids: External player IDs to include in the search
        :param player_ids: FantasyPros player IDs to search

        :return: Dictionary of player info, including ESPN player ID
        """
        params = {}
        if external_ids:
            eids = ':'.join(e.strip().lower() for e in external_ids)
            params['external_ids'] = eids

        if player_ids:
            pids = ':'.join([p for p in player_ids])
            params['player'] = pids

        players = self._loader(endpoint='players', params=params)

        data = {}
        for player in players['players']:
            if player['espn_id'] and player['position_id'] in set(self.roster_settings.positions.values()):
                data[player['player_id']] = {
                    'espn_id': int(player['espn_id']),
                    'name': player['player_name'],
                    'position': player['position_id'],
                    'nfl_team': player['team_id'],
                }
        return data

    @ttl_cache(maxsize=20, ttl=3600)
    def get_projections(
            self,
            player_ids: tuple[str] | None = None,
            ros: bool = False
    ) -> list[dict]:
        """
        Get FantasyPros projections.
        :param ros: Include rest of season projections (default: False)

        :return: Dictionary of projections with ESPN player ID as key
        """
        if self.season:
            if self.season < 2012:
                raise ValueError('Season cannot be < 2012')

        positions = ':'.join(self.roster_settings.positions.values())
        params = {'season': self.season, 'week': self.week, 'positions': positions}
        if player_ids:
            params['players'] = ':'.join(player_ids)
        if ros:
            params['ros'] = True

        projections = self._loader(endpoint='projections', params=params)
        player_info = self.get_player_info()

        players = []
        for player in projections['players']:
            player['projection'] = player['stats'][self.proj_col]
            player['espn_id'] = (
                player_info.get(player['fpid'], {}).get('espn_id')
                or (self.mapping or {}).get(str(player['fpid']))
            )
            players.append(player)
        return players
