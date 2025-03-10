from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params
from scripts.api.Teams import Teams
from scripts.utils import utils as ut
from scripts.utils import constants as const
from scripts.scenarios.scenarios import get_h2h
from scripts.scenarios.scenarios import schedule_switcher

import pandas as pd


def commit_h2h(connection, h2h_data: pd.DataFrame):
    print(f'Writing h2h data to database')
    for idx, row in h2h_data.iterrows():
        print(f'Committing {row.id}...', end='\n')
        c = connection.cursor()

        query = '''
        INSERT INTO
        h2h
            (id, season, week, team, opp, result)
        VALUES
            (%s, %s, %s, %s, %s, %s);
        '''
        values = (row.id, row.season, row.week, row.team, row.opp, row.result)

        c.execute(query, values)
        connection.commit()
        print('Success!', end='\n')


def commit_ss(connection, ss_data: pd.DataFrame):
    print(f'Writing schedule switcher data to database')
    for idx, row in ss_data.iterrows():
        print(f'Committing {row.id}...', end='\n')
        c = connection.cursor()

        query = '''
        INSERT INTO
        switcher
            (id, season, week, team, schedule_of, result)
        VALUES
            (%s, %s, %s, %s, %s, %s);
        '''
        values = (row.id, row.season, row.week, row.team, row.schedule_of, row.result)

        c.execute(query, values)
        connection.commit()
        print('Success!', end='\n')


def update_scenarios_db(season: int=const.SEASON):
    d = DataLoader(year=season)
    teams = Teams(data=d)
    params = Params(data=d)
    end = params.regular_season_end
    as_of_week = params.as_of_week
    week = as_of_week if as_of_week <= end else end

    if week <= end:
        h2h_data = get_h2h(teams=teams, season=season, week=week)
        ss_data = schedule_switcher(teams=teams, season=season, week=week)
        with ut.mysql_connection() as conn:
            commit_h2h(connection=conn, h2h_data=h2h_data)
            commit_ss(connection=conn, ss_data=ss_data)


if __name__ == '__main__':
    update_scenarios_db()
