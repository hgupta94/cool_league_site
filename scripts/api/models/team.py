from dataclasses import dataclass

from scripts.api.dataloader import DataLoader
from scripts.api.fantasy_pros import FantasyPros
from scripts.utils.constants import TEAM_IDS
from scripts.api.models.player import Player, ParseContext


@dataclass(frozen=True)
class Team:
    team_id: int
    manager_id: str
    first_name: str
    last_name: str
    display_name: str
    espn_name: str
    abbrev: str
    total_wins: int
    total_losses: int
    points_for: float
    points_against: float
    faab_spent: int
    acquisitions: int
    drops: int
    trades: int
    roster: dict[Player.id, Player]

    def __repr__(self) -> str:
        return f'Team(id={self.team_id}, display_name={self.display_name})'

    @classmethod
    def create_team(
            cls,
            dataloader: DataLoader,
            fpros: FantasyPros,
            obj: dict,
            roster_obj: dict,
            ctx: ParseContext
    ) -> Team:
        def get_name_obj(mgr_id: str) -> dict:
            return TEAM_IDS[mgr_id]

        name = get_name_obj(obj.get('owners', None)[0])['name']
        record_obj = obj.get('record', {}).get('overall', {})
        transaction_obj = obj.get('transactionCounter', {})
        roster_entry = roster_obj['entries'] if 'entries' in roster_obj else roster_obj
        roster = Player.get_players(dataloader=dataloader, fpros=fpros, obj=roster_entry, ctx=ctx)

        return Team(
            team_id=obj.get('id', None),
            manager_id=obj.get('primaryOwner', None),
            first_name=name.get('first', None),
            last_name=name.get('last', None),
            display_name=name.get('display', None),
            espn_name=obj.get('name', None),
            abbrev=obj.get('abbrev', None),
            total_wins=record_obj.get('wins', None),
            total_losses=record_obj.get('losses', None),
            points_for=record_obj.get('pointsFor', None),
            points_against=record_obj.get('pointsAgainst', None),
            faab_spent=transaction_obj.get('acquisitionBudgetSpent', None),
            acquisitions=transaction_obj.get('acquisitions', None),
            drops=transaction_obj.get('drops', None),
            trades=transaction_obj.get('trades', None),
            roster=roster
        )

    @classmethod
    def get_teams(
            cls,
            dataloader: DataLoader,
            fpros: FantasyPros,
            obj: dict,
            roster_obj: dict,
            ctx: ParseContext
    ) -> dict[Team.team_id, Team]:
        teams = {}
        for team_obj in obj['teams']:
            roster_entry = roster_obj['teams']
            team_roster = [r for r in roster_entry if r['id'] == team_obj['id']][0]['roster']
            team = cls.create_team(dataloader=dataloader, fpros=fpros, obj=team_obj, roster_obj=team_roster, ctx=ctx)
            teams[team.team_id] = team
        return teams
