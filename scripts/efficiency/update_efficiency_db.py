from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params
from scripts.utils import utils as ut
from scripts.utils import constants as const
from scripts.efficiency.efficiencies import get_optimal_points

import pandas as pd


def commit_efficiency(connection, data: pd.DataFrame):
    print(f'Writing efficiency data to database')

    for idx, row in data.iterrows():
        print(f'Committing {row.id}...', end='\n')
        c = connection.cursor()

        query = '''
        INSERT INTO
        efficiency
            (id, season, week, team,
            act_score, act_proj,
            best_projected_act, best_projected_proj,
            optimal_lineup_act, optimal_lineup_proj)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        '''
        values = (row.id, row.season, row.week, row.team,
                  row.actual_score, row.actual_projected,
                  row.best_projected_actual, row.best_projected_proj,
                  row.best_lineup_actual, row.best_lineup_proj)

        c.execute(query, values)
        connection.commit()
        print('Success!', end='\n')


def update_efficiency_db(season: int=const.SEASON):
    d = DataLoader(year=season)
    params = Params(d)
    settings = d.settings()

    end = params.regular_season_end
    as_of_week = params.as_of_week
    week = as_of_week if as_of_week <= end else end

    data = d.load_week(week=week)

    eff = get_optimal_points(data, params, settings, season, week)
    with ut.mysql_connection() as conn:
        commit_efficiency(connection=conn, data=eff)


if __name__ == '__main__':
    update_efficiency_db()
