import requests
import logging
import os

from cachetools.func import ttl_cache
from dotenv import load_dotenv
import difflib

from scripts.utils import constants
from scripts.api.dataloader import DataLoader
from scripts.api.settings import LeagueSettings, RosterSettings
from scripts.api.models.player import Player, ParseContext, PlayerView


class FantasyPros:
    def __init__(self, dataloader: DataLoader):
        load_dotenv()
        api_key = os.getenv('FPROS_KEY')
        self.base_url = 'https://api.fantasypros.com/public/v2/json/nfl'
        self.headers = {'x-api-key': api_key}

        self.season = constants.SEASON
        self.week = constants.WEEK

        self.league_settings = LeagueSettings(dataloader=dataloader)
        self.roster_settings = RosterSettings(dataloader=dataloader)

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
    def get_player_info(self) -> dict:
        """
        Fantasy Pros player info

        :param player_ids: FantasyPros player IDs to search, in id1:id2:...:idn format

        :return: Dictionary of player info, including ESPN player ID
        """
        params = {'external_ids': 'espn'}
        players = self._loader(endpoint='players', params=params)

        data = {}
        for player in players['players']:
            if player['espn_id'] and player['position_id'] in {'QB', 'RB', 'WR', 'TE', 'DST'}:
                data[player['player_id']] = {
                    'espn_id': int(player['espn_id']),
                    'name': player['player_name'],
                    'position': player['position_id'],
                    'nfl_team': player['team_id'],
                    'search_string': f'{player["player_name"]}|{player["position_id"]}|{player["team_id"]}',
                }
        return data

    @ttl_cache(maxsize=1, ttl=3600)
    def get_projections(
            self,
            season: int = None,
            week: int = None,
            ros: bool = False
    ) -> list[Player]:
        """
        Get FantasyPros projections for a given season and week.
        :param season: Season to search
        :param week: Week to search
        :param ros: Include rest of season projections (default: False)

        :return: Dictionary of projections with ESPN player ID as key
        """
        if season:
            if season < 2012:
                raise ValueError('Season cannot be < 2012')

        if not season:
            season = self.season
        if not week:
            week = self.week

        positions = ':'.join(self.roster_settings.positions.values())
        params = {'season': season, 'week': week, 'positions': positions}
        if ros:
            params['ros'] = True

        player_info = self.get_player_info()
        projections = self._loader(endpoint='projections', params=params)

        # espn_lookups = self.build_espn_lookup(season)
        espn_id = None
        ctx = ParseContext(view=PlayerView.WEEK)
        players = []
        for player in projections['players']:
            try:
                espn_id = player_info[player['fpid']].get('espn_id', None)
            except KeyError:
                pass
                # get fpros to espn json mapping, or list of player ids to pass to self.get_player_info
                # fpros_player_string = f'{player["name"]}|{player["position_id"]}|{player["team_id"]}'
                # espn_id = self.match_player(espn_lookups, fpros_player_string, thresh=0.8)
            p = Player.create_player(obj=player, ctx=ctx)
            p.espn_id = espn_id
            p.projection = p.pts_proj[self.proj_col]
            players.append(p)
        return players

    @staticmethod
    def build_espn_lookup(season: int) -> dict[int, dict]:
        def get_position(eligible_slots: list[int]) -> dict:
            for posid in eligible_slots:
                if posid in constants.POSITION_MAP and constants.POSITION_MAP[posid]:
                    return {'id': posid, 'position': constants.POSITION_MAP[posid]}
            return {}

        dataloader = DataLoader(year=season)
        espn_players = dataloader.players_info()['players']
        all_lookups = {}
        for i, ep in enumerate(espn_players):
            espnid = ep['id']
            name = ep['player']['fullName']
            position = get_position(ep['player']['eligibleSlots'])['position']
            team = constants.NFL_TEAM_MAP[ep['player']['proTeamId']]
            string = f'{name}|{position}|{team}'
            all_lookups[i] = {'id': espnid, 'string': string}
        return all_lookups

    @staticmethod
    def match_player(espn_lookup: dict, player_string: str, thresh: float = 0.8):
        espn_strings = [a['string'] for a in espn_lookup.values()]
        calc = [difflib.SequenceMatcher(None, player_string, m).ratio() for m in espn_strings]
        if max(calc) > thresh:
            match_idx = calc.index(max(calc))
            return espn_lookup[match_idx]['id'], max(calc)
        return None
