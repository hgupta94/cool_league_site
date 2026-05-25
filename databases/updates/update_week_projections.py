from scripts.api.dataloader import DataLoader
from scripts.api.settings import LeagueSettings
from scripts.simulations.simulations import get_week_projections
from scripts.utils.database import Database
from scripts.utils import constants

import mysql.connector.errors


data = DataLoader(year=constants.SEASON)
params = LeagueSettings(data=data)
week = params.current_week
players = DataLoader().players_info()['players']

projections = get_week_projections(week=week)
projections = projections[['id', 'season', 'week', 'player', 'espn_id', 'position', 'rec', 'fpts']]
projections['actual'] = None
projections.columns = ['id', 'season', 'week', 'name', 'espn_id', 'position', 'receptions', 'projection', 'actual']

try:
    Database().batch_insert(
        table='player_projections',
        columns=constants.PROJECTIONS_COLUMNS,
        rows=[tuple(row) for _, row in projections.iterrows()]
    )
except mysql.connector.errors.IntegrityError:
    # update projections
    Database().batch_insert(
        table='player_projections',
        columns=constants.PROJECTIONS_COLUMNS,
        rows=[tuple(row) for _, row in projections.iterrows()],
        upsert=True,
        update_columns=['projection']
    )


# get actual scores
if day == 'Wed':
    players = data.load_week(week=week)['players']
    for player in players:
        actual = 0
        for stat in player['player']['stats']:
            if (
                    stat['seasonId'] == 2025
                    and stat['scoringPeriodId'] == week
                    and stat['statSourceId'] == 0
            ):
                actual = stat['appliedTotal']
        Database().batch_insert(
            table='player_projections',
            columns=constants.PROJECTIONS_COLUMNS,
            rows=[tuple(row) for _, row in projections.iterrows()],
            upsert=True,
            update_columns=['actual']
        )
