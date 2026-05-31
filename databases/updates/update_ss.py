from scripts.scenarios.scenarios import schedule_switcher
from scripts.api.models.schedule import TeamResult
from scripts.api.dataloader import DataLoader
from scripts.utils.database import Database
from scripts.utils import constants


def load_switcher(
        dataloader: DataLoader,
        season: int = constants.SEASON,
        week: int = constants.WEEK-1,
        upsert: bool = False,
        upsert_cols: list[str] | None = None
) -> None:
    """Batch load rows to the schedule_switcher table for the prior week"""

    schedules = TeamResult.get_all_team_schedules(dataloader=dataloader)
    switcher = schedule_switcher(schedules=schedules, season=season, week=week)
    rows = []
    for s in switcher:
        rowid = f'{s['season']}_{s['week']:02}_{s['team']:02}_{s['schedule_of']:02}'
        rows.append((
            rowid, s['season'], s['week'], s['team'], s['schedule_of'], s['result']
        ))

    Database().batch_insert(
        table='schedule_switcher',
        columns='id, season, week, team, schedule_of, result',
        rows=rows,
        upsert=upsert,
        update_columns=upsert_cols
    )
