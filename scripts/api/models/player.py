from scripts.api.dataloader import DataLoader
from scripts.api.fantasy_pros import FantasyPros
from scripts.utils.constants import SEASON, WEEK, POSITION_MAP_ESPN

from dataclasses import dataclass
from enum import Enum


class PlayerView(str, Enum):
    WEEK = 'week'
    SEASON = 'season'


@dataclass(frozen=True)
class ParseContext:
    view: PlayerView
    season: int = SEASON
    week: int = WEEK  # unused for season view


@dataclass
class Player:
    id: int
    name: str
    team_id: int
    eligible_slots: list[int]
    position_id: int
    position: str
    lineup_slot_id: int
    is_locked: bool
    is_injured: bool
    status: str
    pts_act: float
    pts_act_breakdown: dict
    pts_proj: float
    pts_proj_breakdown: dict
    percent_owned: float
    percent_start: float
    source_view: ParseContext
    pts_proj_fp: float | None = None
    pts_proj_fp_breakdown: dict | None = None

    def __repr__(self) -> str:
        return f'Player(name={self.name})'

    @classmethod
    def build_lineup_slot_lookup(
            cls,
            teams_data: dict,
            rosters_data: dict,
    ) -> dict[int, int]:
        """
        Returns {(team_id, player_id): lineup_slot_id}
        from week_data -> teams_list -> team -> roster -> player.
        """
        slot_map: dict[int, int] = {}

        teams_list = teams_data.get("teams", teams_data)
        rosters = rosters_data.get('teams', [])
        for team_obj in teams_list:
            team_id = team_obj.get("id")
            if team_id is None:
                continue

            roster_data = [r for r in rosters if r['id'] == team_id][0].get('roster', {})
            entries = roster_data.get("entries", [])

            for player in entries:
                # player_obj = (
                #     entry.get("player")
                #     or entry.get("playerPoolEntry", {}).get("player")
                #     or {}
                # )
                player_obj = player.get("playerPoolEntry", {})
                player_id = player_obj.get("id")
                lineup_slot_id = player.get("lineupSlotId")

                if player_id is None or lineup_slot_id is None:
                    continue

                slot_map[player_id] = int(lineup_slot_id)
        return slot_map

    @classmethod
    def create_player(
            cls,
            obj: dict,
            ctx: ParseContext,
            fpros: dict | None = None,
            slot_lookup: dict | None = None,
    ) -> 'Player':
        """Create a player object from ESPN"""
        player_entry = obj.get('playerPoolEntry', obj)
        player_data = player_entry.get('player', player_entry)
        player_stats = player_data.get('stats', [])

        player_id = player_entry.get('id', player_entry.get('fpid', None))
        ownership = player_data.get("ownership", {})

        if slot_lookup:
            try:
                lineup_slot_id = slot_lookup[player_id]
            except KeyError:  # player is not present
                lineup_slot_id = None
        else:
            lineup_slot_id = player_entry.get('lineupSlotId')

        def get_position(eligible_slots: list[int]) -> dict:
            for posid in eligible_slots:
                if posid in POSITION_MAP_ESPN and POSITION_MAP_ESPN[posid]:
                    return {'id': posid, 'position': POSITION_MAP_ESPN[posid]}
            return {}

        def get_points(stat_source_id: int) -> float:
            if isinstance(player_stats, list):
                # espn
                for stat in player_stats:
                    if ctx.view is PlayerView.WEEK:
                        if (
                                stat.get('seasonId') == ctx.season
                                and stat.get('scoringPeriodId') == ctx.week
                                and stat.get('statSourceId') == stat_source_id
                        ):
                            return float(stat.get('appliedTotal', None)), stat.get('stats', {})
                    else:
                        if (
                                stat.get('seasonId') == ctx.season
                                and stat.get('statSourceId') == stat_source_id
                                and stat.get('statSplitTypeId') == 0
                        ):
                            return float(stat.get('appliedTotal', None)), stat.get('stats', {})

            if isinstance(player_stats, dict):
                # fantasypros
                if stat_source_id == 0:
                    return None, None
                else:
                    return (
                        {
                            'points': player_stats.get('points', None),
                            'points_half': player_stats.get('points_half', None),
                            'points_ppr': player_stats.get('points_ppr', None)
                        }
                    ), None
            return None, None

        eligible_slots = player_data.get('eligibleSlots', [])
        pl_position = get_position(eligible_slots)

        act_points_obj: tuple = get_points(stat_source_id=0)
        proj_points_obj: tuple = get_points(stat_source_id=1)
        pts_proj_fp = None
        pts_proj_fp_breakdown = None
        if fpros:
            pts_proj_fp = fpros['projection']
            pts_proj_fp_breakdown = fpros['stats']

        return Player(
            id=player_id,
            name=player_data.get('fullName', player_data.get('name', None)),
            team_id=player_entry.get('onTeamId', None),
            eligible_slots=eligible_slots,
            position_id=pl_position.get('id', None),
            position=pl_position.get('position', player_data.get('position_id', None)),
            lineup_slot_id=lineup_slot_id,
            is_locked=False,  # is_locked=player_entry.get('lineupLocked', None),
            is_injured=player_data.get('injured', None),
            status=player_data.get('injuryStatus', None),
            pts_act=0, # act_points_obj[0] if act_points_obj else None,
            pts_act_breakdown={},  #act_points_obj[1] if act_points_obj else None,
            pts_proj=proj_points_obj[0] if act_points_obj else None,
            pts_proj_breakdown=proj_points_obj[1] if act_points_obj else None,
            pts_proj_fp=pts_proj_fp,
            pts_proj_fp_breakdown=pts_proj_fp_breakdown,
            percent_owned=round(float(ownership.get('percentOwned', 0.0)) / 100, 4),
            percent_start=round(float(ownership.get('percentStarted', 0.0)) / 100, 4),
            source_view=ctx,
        )

    @classmethod
    def get_players(
            cls,
            dataloader: DataLoader,
            fpros: FantasyPros,
            obj: list[dict],
            ctx: ParseContext
    ) -> dict[int, 'Player']:
        """get all player objects from ESPN"""

        fantasy_pros = fpros.get_projections()
        slot_lookup = None
        if ctx.week:
            teams_data = dataloader.teams()
            rosters_data = dataloader.rosters()
            slot_lookup = cls.build_lineup_slot_lookup(teams_data, rosters_data)
        players = {}
        for p in obj:
            p_fp = next((fp for fp in fantasy_pros if fp.get('espn_id') == p.get('id')), None)
            player = cls.create_player(obj=p, fpros=p_fp, ctx=ctx, slot_lookup=slot_lookup)
            players[player.id] = player
        return players
