from scripts.scenarios.scenarios import schedule_switcher
from scripts.api.dataloader import DataLoader
from scripts.api.settings import TeamSettings
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

    teams = TeamSettings(dataloader)
    switcher = schedule_switcher(season=season, week=week)
    rows = []
    for s in switcher:
        t1_disp = constants.TEAM_IDS[teams.teamid_to_primowner[s['team']]]['name']['display']
        t2_disp = constants.TEAM_IDS[teams.teamid_to_primowner[s['schedule_of']]]['name']['display']
        rowid = f'{s['season']}_{s['week']:02}_{t1_disp}_{t2_disp}'
        rows.append((
            rowid, s['season'], s['week'], t1_disp, t2_disp, s['result']
        ))

    Database().batch_insert(
        table='schedule_switcher',
        columns=constants.SCHEDULE_SWITCH_COLUMNS,
        rows=rows,
        upsert=upsert,
        update_columns=upsert_cols
    )
