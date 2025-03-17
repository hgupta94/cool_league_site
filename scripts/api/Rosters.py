from scripts.api.DataLoader import DataLoader
# from scripts.api.Teams import Teams
from scripts.utils import constants as const


class Rosters:
    def __init__(self, year):
        self.data = DataLoader(year=year)
        settings = self.data.settings()
        slot_limits = settings['settings']['rosterSettings']['lineupSlotCounts']
        roster_limits = settings['settings']['rosterSettings']['positionLimits']

        self.player_stats_map = const.PLAYER_STATS_MAP
        self.slotcodes = const.SLOTCODES
        self.nfl_team_map = const.NFL_TEAM_MAP
        self.espn_tonfl_position_map = const.POSITION_MAP
        self.slot_limits = {int(k): v for k, v in slot_limits.items() if v > 0}
        self.roster_limits = {int(k): v for k, v in roster_limits.items() if v > 0}
        self.positions = [v for v in self.espn_tonfl_position_map.values()] + ['FLEX']

    # def get_player_week_actual(self, player_id):
    #     player_id = 4374302
    #     players = self.data.players()
    #     teams = Teams(self.data)
    #
    # def get_player_week_projected(self, player_id):
    #     players = self.data.players()