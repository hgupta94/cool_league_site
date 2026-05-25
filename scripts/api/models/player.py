from scripts.utils.constants import SEASON, POSITION_MAP
from dataclasses import dataclass


@dataclass(frozen=True)
class Player:
    id: int
    name: str
    position_id: int
    position: str
    lineup_slot_id: int
    is_locked: bool
    is_injured: bool
    status: str
    pts_proj: float
    pts_act: float
    percent_owned: float
    percent_start: float


def espn_to_player(
        obj: dict,
        season: int = SEASON,
        week: int = 0
) -> Player:
    player_entry = obj.get('playerPoolEntry', obj)
    player_data = player_entry.get('player', {})
    player_stats = player_data.get('stats', [])

    ownership = player_data.get("ownership", {})

    def get_position(eligible_slots: list[str]) -> dict:
        for posid in eligible_slots:
            if posid in POSITION_MAP and POSITION_MAP[posid]:
                return {'id': posid, 'position': POSITION_MAP[posid]}
        return {}

    def get_points(stat_source_id: int) -> float:
        for stat in player_stats:
            if (
                    stat.get("seasonId") == season
                    and stat.get("scoringPeriodId") == week
                    and stat.get("statSourceId") == stat_source_id
            ):
                return float(stat.get("appliedTotal", 0.0))
        return 0.0

    return Player(
        id=player_entry.get('id', None),
        name=player_data.get('fullName', None),
        position_id=get_position(player_data.get("eligibleSlots", [])).get('id', None),
        position=get_position(player_data.get("eligibleSlots", [])).get('position', None),
        lineup_slot_id=player_entry.get("lineupSlotId"),
        is_locked=player_entry.get('lineupLocked', None),
        is_injured=player_data.get('injured', None),
        status=player_data.get('injuryStatus', None),
        pts_proj=get_points(stat_source_id=1),
        pts_act=get_points(stat_source_id=0),
        percent_owned=float(ownership.get("percentOwned", 0.0)) / 100,
        percent_start=float(ownership.get("percentStarted", 0.0)) / 100,
    )
