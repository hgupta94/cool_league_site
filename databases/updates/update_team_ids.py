from scripts.api.dataloader import DataLoader
from scripts.utils.database import Database

rows = []
for season in range(2014, 2026):
    dl = DataLoader(year=season)
    if season < 2018:
        teams = dl.teams()[0]['teams']
    else:
        teams = dl.teams()['teams']
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
