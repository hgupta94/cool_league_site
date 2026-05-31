from scripts.utils.database import Database
from scripts.api.dataloader import DataLoader
from scripts.api.models.schedule import TeamResult
from scripts.api.settings import TeamSettings
from scripts.utils import constants


def load_matchups(
        dataloader: DataLoader,
        week: int = constants.WEEK-1,
        upsert: bool = False,
        upsert_cols: list[str] | None = None
) -> None:
    """Batch load rows to the matchups table for the prior week"""

    teams = TeamSettings(dataloader=dataloader)
    schedules = TeamResult.get_all_team_schedules(dataloader=dataloader)

    rows = []
    for t in teams.team_ids:
        team_matchup = schedules[t][week]
        team_id = team_matchup.team_id
        opp_id = team_matchup.opponent_id
        row = (
            f'{team_matchup.season}_{team_matchup.week:02}_{team_id:02}',
            team_matchup.season,
            team_matchup.week,
            team_id,
            team_matchup.team_score,
            opp_id,
            team_matchup.opponent_score,
            team_matchup.matchup_result,
            team_matchup.tophalf_result,
            team_matchup.game_type
        )
        rows.append(row)

    Database().batch_insert(
        table='matchups',
        columns='id, season, week, team, score, opponent, opponent_score, matchup_result, tophalf_result, game_type',
        rows=rows,
        upsert=upsert,
        update_columns=upsert_cols
    )
