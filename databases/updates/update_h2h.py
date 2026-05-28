from scripts.scenarios.scenarios import get_h2h
from scripts.api.dataloader import DataLoader
from scripts.api.settings import TeamSettings
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

    teams = TeamSettings(dataloader)
    h2h = get_h2h(season=season, week=week)
    rows = []
    for h in h2h:
        t1_disp = constants.TEAM_IDS[teams.teamid_to_primowner[h['team']]]['name']['display']
        t2_disp = constants.TEAM_IDS[teams.teamid_to_primowner[h['opponent']]]['name']['display']
        rowid = f'{h['season']}_{h['week']:02}_{t1_disp}_{t2_disp}'
        rows.append((
            rowid, h['season'], h['week'], t1_disp, t2_disp, h['result']
        ))

    Database().batch_insert(
        table='h2h',
        columns=constants.H2H_COLUMNS,
        rows=rows,
        upsert=upsert,
        update_columns=upsert_cols
    )
