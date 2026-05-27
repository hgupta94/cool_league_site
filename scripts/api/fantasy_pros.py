import requests
import os

from cachetools.func import ttl_cache
from dotenv import load_dotenv
import difflib

from scripts.utils import constants
from scripts.api.dataloader import DataLoader
from scripts.api.settings import LeagueSettings


class FantasyPros:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv('FPROS_KEY')
        self.base_url = 'https://api.fantasypros.com/public/v2/json'
        self.headers = {'x-api-key': api_key}

        self.settings = LeagueSettings()
        self.ppr_dict = {0: 'points', 0.5: 'points_half', 1: 'points_ppr'}
        self.proj_col = self.ppr_dict[self.settings.ppr_type]

    @ttl_cache(maxsize=1, ttl=3600)
    def get_player_info(self) -> dict:
        """
        Fantasy Pros player info

        :param playerid: FantasyPros player ID to search

        :return: Dictionary of player info, including ESPN player ID
        """
        players = requests.get(
            f'{self.base_url}/NFL/players?external_ids=espn',
            headers=self.headers
        ).json()

        data = {}
        try:
            for player in players['players']:
                if player['espn_id'] and player['position_id'] in ['QB', 'RB', 'WR', 'TE', 'DST']:
                    data[player['player_id']] = {
                        'espn_id': int(player['espn_id']),
                        'name': player['player_name'],
                        'position': player['position_id'],
                        'nfl_team': player['team_id'],
                        'search_string': f'{player["player_name"]}|{player["position_id"]}|{player["team_id"]}',
                    }
        except KeyError:
            print(players)
        return data

    @ttl_cache(maxsize=1, ttl=3600)
    def get_projections(
            self,
            season: int = constants.SEASON,
            week: int = constants.WEEK,
            ros: bool = False
    ) -> dict[int, dict]:
        """
        Get FantasyPros projections for a given season and week.
        :param season: Season to search
        :param week: Week to search
        :param ros: Include rest of season projections (default: False)

        :return: Dictionary of projections with ESPN player ID as key
        """
        if season < 2012:
            raise ValueError('Season cannot be < 2012')

        player_info = self.get_player_info()
        ros_str = '' if not ros else '&ros=true'
        projections = requests.get(
            f'{self.base_url}/nfl/{season}/projections?week={week}{ros_str}',
            headers=self.headers
        ).json()

        espn_lookups = self.build_espn_lookup(season)
        players = {}
        for player in projections['players']:
            try:
                espn_id = player_info[player['fpid']].get('espn_id', None)
            except KeyError:
                fpros_player_string = f'{player["name"]}|{player["position_id"]}|{player["team_id"]}'
                espn_id = self.match_player(espn_lookups, fpros_player_string, thresh=0.8)
                # {k: v for k, v in espn_lookups.items() if v['id'] == espn_id}
                if not espn_id:
                    break
            players[player['fpid']]  = {
                'espn_id': espn_id,
                'name': player['name'],
                'position': player['position_id'],
                'projection': player['stats'][self.proj_col],
                'rec': player['stats']['rec_rec'],
                'ppr': self.settings.ppr_type,
            }

        return players

    @staticmethod
    def build_espn_lookup(season: int) -> dict[int, dict]:
        def get_position(eligible_slots: list[int]) -> dict:
            for posid in eligible_slots:
                if posid in constants.POSITION_MAP and constants.POSITION_MAP[posid]:
                    return {'id': posid, 'position': constants.POSITION_MAP[posid]}
            return {}

        dataloader = DataLoader(year=season, n=1000)
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

fp = FantasyPros()
projections = fp.get_projections(season=2018, week=0)
