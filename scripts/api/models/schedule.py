from dataclasses import dataclass, field
from enum import Enum

from scripts.utils.constants import SEASON
from scripts.api.dataloader import DataLoader
from scripts.api.settings import LeagueSettings


class Result(Enum):
    WIN = 1.0
    TIE = 0.5
    LOSS = 0.0


class GameType(Enum):
    REG = 'REG'
    POST = 'POST'


@dataclass(frozen=True)
class MatchupTeam:
    id: int
    points: float
    matchup_result: Result

@dataclass(frozen=True)
class Matchup:
    id: int
    week: int
    game_type: GameType
    teams: dict[int, MatchupTeam]

    @classmethod
    def create_matchup(cls, obj: dict, n_reg_weeks: int) -> 'Matchup':
        game_type = GameType.POST if obj.get('matchupPeriodId') > n_reg_weeks else GameType.REG
        teams = {}
        for i, tm in enumerate(['home', 'away']):
            try:
                team_entry = obj.get(tm, {})
                tmid = team_entry['teamId']
                points = team_entry.get('totalPoints', 0.0)
                winner = obj.get('winner', '').lower()
                matchup_result = Result.WIN if tm == winner else Result.LOSS
                teams[tmid] = MatchupTeam(
                    id=tmid,
                    points=points,
                    matchup_result=matchup_result
                )
            except KeyError:  # playoff bye
                continue

        return Matchup(
            id=obj.get('id', None),
            week=obj.get('matchupPeriodId', None),
            game_type=game_type.value,
            teams=teams
        )

    @classmethod
    def get_week_matchups(cls, params: LeagueSettings) -> dict[int, 'MatchupTeam']:
        week = params.current_week
        dataloader = DataLoader(week=week)
        n_weeks = params.regular_season_end
        # scores = dataloader.week_scores(week=week)
        matchups_obj = dataloader.matchups()
        week_matchups = [m for m in matchups_obj['schedule'] if m['matchupPeriodId'] == week]
        matchups = []
        # median = sum(sorted(scores)[(len(scores) // 2) - 1: (len(scores) // 2) + 1]) / 2
        for m in week_matchups:
            matchups.append(Matchup.create_matchup(obj=m, n_reg_weeks=n_weeks))

        return matchups

    @classmethod
    def get_season_matchups(
            cls,
            params: LeagueSettings
    ) -> dict[int, 'Matchup']:
        all_matchups = {}
        for w in range(1, params.regular_season_end + params.playoff_length + 1):
            # scores = DataLoader(week=w).week_scores(week=w)
            matchups_obj = DataLoader(week=w).matchups()
            week_matchups = [m for m in matchups_obj['schedule'] if m['matchupPeriodId'] == w]
            matchups = []
            # median = sum(sorted(scores)[(len(scores) // 2) - 1: (len(scores) // 2) + 1]) / 2
            for m in week_matchups:
                matchups.append(Matchup.create_matchup(obj=m, n_reg_weeks=params.regular_season_end))
            all_matchups[w] = matchups

        return all_matchups


@dataclass
class TeamResult:
    season: int
    week: int
    game_id: int
    game_type: GameType
    team_id: int
    team_score: float
    opponent_id: int
    opponent_score: float
    matchup_result: Result
    tophalf_result: Result
    wins: int = field(init=False)

    def __post_init__(self):
        if self.matchup_result and self.tophalf_result:
            m = self.matchup_result.value
            t = self.tophalf_result.value
            object.__setattr__(self, "wins", m + t)
        else:
            object.__setattr__(self, "wins", None)

    @classmethod
    def get_team_schedule(
            cls,
            obj: list[dict],
            team_id: int,
            medians: dict[int, float],
            n_reg_weeks: int
    ) -> 'TeamResult':
        schedule = {}
        for match in obj:
            if 'away' in match and 'home' in match:
                week = match.get('matchupPeriodId')
                game_type = GameType.POST if week > n_reg_weeks else GameType.REG
                tmid, opp_tm_id, points, opp_points = None, None, None, None
                if match['away']['teamId'] == team_id or match['home']['teamId'] == team_id:
                    for i, tm in enumerate(['home', 'away']):
                        team_entry = match.get(tm, {})
                        if team_entry['teamId'] == team_id:
                            tmid = team_entry['teamId']
                            points = team_entry.get('totalPoints', 0.0)
                        else:
                            opp_tm_id = team_entry['teamId']
                            opp_points = team_entry.get('totalPoints', 0.0)
                    matchup_result = Result.WIN if points > opp_points else Result.LOSS
                    tophalf_result = Result.WIN if points > medians[week] else Result.LOSS
                    schedule[week] = TeamResult(
                            season=SEASON,
                            week=week,
                            game_id=match['id'],
                            game_type=game_type,
                            team_id=tmid,
                            team_score=points,
                            opponent_id=opp_tm_id,
                            opponent_score=opp_points,
                            matchup_result=matchup_result,
                            tophalf_result=tophalf_result
                        )
        return schedule

    @classmethod
    def get_all_team_schedules(cls, week: int) -> dict[int, 'TeamResult']:
        def get_median(scores: list[float]):
            return sum(scores[(len(scores) // 2) - 1: (len(scores) // 2) + 1]) / 2

        dataloader = DataLoader(week=week)
        teams_obj = dataloader.teams()
        params = LeagueSettings(dataloader=dataloader)
        n_weeks = params.regular_season_end
        matchups_obj = dataloader.matchups()['schedule']
        all_scores = dataloader.all_scores()
        medians = {k: round(get_median(v), 2) for k, v in all_scores.items()}
        schedules = {}
        for team in teams_obj['teams']:
            schedules[team['id']] = TeamResult.get_team_schedule(
                obj=matchups_obj,
                team_id=team['id'],
                medians=medians,
                n_reg_weeks=n_weeks
            )

        return schedules
