from scripts.api.dataloader import DataLoader
from scripts.utils.database import Database
from scripts.utils import constants


def update_team_ids(
    season: int = constants.SEASON,
    upsert: bool = False,
    update_columns: list[str] | None = None
    ):
    # update every season after the draft
    rows = []
    teams = dl.teams()['teams']
    for team in teams:
        rows.append((
            f"{season}_{team['id']:02}",
            season,
            team['id'],
            team['primaryOwner']
        ))

    Database().batch_insert(
        table='team_ids',
        columns='id, season, team_id, manager_id',
        rows=rows,
        upsert=upsert,
        update_columns=update_columns
    )


if __name__ == '__main__':
    season = constants.SEASON
    dl = DataLoader(year=constants.SEASON)
    update_team_ids()
