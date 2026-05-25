from dataclasses import dataclass

from scripts.utils.constants import TEAM_IDS
from scripts.api.models.player import Player, espn_to_player


@dataclass(frozen=True)
class Team:
    team_id: int
    mgr_id: str
    first_name: str
    last_name: str
    display_name: str
    display_name: str
    abbrev: str
    espn_name: str
    faab_rem: int
    roster: list[Player]


def espn_to_team(
        obj: dict
) -> Team:
    def get_name_obj(mgr_id: str) -> dict:
        return TEAM_IDS[mgr_id]

    name = get_name_obj(obj.get('owners', None)[0])

    return Team(
        team_id=obj.get('id', None),
        mgr_id=obj.get('owners', None),
        first_name=name.get('first', None),
        last_name=name.get('last', None),
        display_name=name.get('display', None),
        abbrev=obj.get('abbrev', None),
    )
