from scripts.utils.constants import POSITION_MAP

class Player:
    def __init__(self, obj: dict, lineup_slot_id: int = None):
        self.metadata = obj
        self.id = obj['id']
        self.name = obj['player']['fullName']
        self.position_id = obj['player']['defaultPositionId']
        self.position = self._get_position()
        self.team_id = obj['onTeamId']
        self.is_locked = obj['lineupLocked']
        self.is_injured = obj['player']['injured']
        self.status = obj['player']['injuryStatus']
        self.lineup_slot = obj[lineup_slot_id] if lineup_slot_id else None
        self.eligible_positions = obj['player']['eligibleSlots']
        self.percent_owned = obj['player']['ownership']['percentOwned']
        self.percent_start = obj['player']['ownership']['percentStarted']
        self.week = max(x['scoringPeriodId'] for x in obj['player']['stats'])
        self.projection = self._get_points(how='projection')
        self.actual = self._get_points(how='actual')

    def _get_points(self, how: str):
        stat_source_id = 1 if how == 'projection' else 0
        pts = None
        for stat in self.metadata['player']['stats']:
            if stat['scoringPeriodId'] == self.week and stat['statSourceId'] == stat_source_id:
                pts = stat['appliedTotal']
        return pts

    def _get_position(self):
        for pid in self.eligible_positions:
            if pid in POSITION_MAP:
                position = POSITION_MAP[pid]
                if position:
                    return position
