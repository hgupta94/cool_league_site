from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params
from scripts.utils import utils as ut
from scripts.utils import constants as const
from scripts.simulations.projections import get_week_projections

import pandas as pd


def commit_projections(connection,
                       projections: pd.DataFrame):
    print(f'Writing projections to database')

    for idx, row in projections.iterrows():
        c = connection.cursor()
        query = '''
        INSERT INTO
        projections
            (id, season, week, name, espn_id, position, receptions, projection)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s);
        '''
        values = (row.id, row.season, row.week, row.player, row.espn_id, row.position, row.rec, row.fpts)

        c.execute(query, values)
        connection.commit()
        print(f'Committed {row[0]}...', end='\n')


def update_projections_db(season: int=const.SEASON):
    d = DataLoader(year=season)
    params = Params(d)

    projections = get_week_projections(params.current_week)
    with ut.mysql_connection() as conn:
        commit_projections(connection=conn, projections=projections)


if __name__ == '__main__':
    update_projections_db()
