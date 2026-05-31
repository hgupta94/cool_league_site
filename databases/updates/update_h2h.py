from scripts.scenarios.scenarios import get_h2h
from scripts.api.dataloader import DataLoader
from scripts.api.models.schedule import TeamResult
from scripts.utils.database import Database
from scripts.utils import constants


def load_h2h(
        dataloader: DataLoader,
        season: int = constants.SEASON,
        week: int = constants.WEEK-1,
        upsert: bool = False,
        upsert_cols: list[str] | None = None
) -> None:
    """Batch load rows to the h2h table for the prior week"""
    schedules = TeamResult.get_all_team_schedules(dataloader=dataloader)
    h2h = get_h2h(schedules=schedules, season=season, week=week)
    rows = []
    for h in h2h:
        rowid = f'{h['season']}_{h['week']:02}_{h['team']:02}_{h['opponent']:02}'
        rows.append((
            rowid, h['season'], h['week'], h['team'], h['opponent'], h['result']
        ))

    Database().batch_insert(
        table='h2h',
        columns='id, season, week, team, opponent, result',
        rows=rows,
        upsert=upsert,
        update_columns=upsert_cols
    )
