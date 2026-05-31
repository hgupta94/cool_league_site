from scripts.api.dataloader import DataLoader
from scripts.utils.database import Database


def load_team_ids(dataloader: DataLoader, season: int) -> None:
    rows = []
    teams = dataloader.teams()['teams']
    for team in teams:
        rows.append((
            f'{season}_{team['id']:02}',
            season,
            team['id'],
            team['primaryOwner']
        ))

    Database().batch_insert(
        table='team_ids',
        columns='id, season, team_id, manager_id',
        rows=rows,
        upsert=False,
        update_columns=None
    )
