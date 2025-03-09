from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params
from scripts.utils import utils as ut
from scripts.utils import constants as const
from scripts.home.standings import get_standings

import pandas as pd


def commit_standings_2018(connection, standings: pd.DataFrame):
    print(f'Writing standings to database')
    for idx, row in standings.iterrows():

        print(f'Committing {row["rank"]}. {row.team}...', end='\n')
        c = connection.cursor()

        query = '''
        INSERT INTO
        standings_2018
            (id, season, week, `rank`, team, record, win_perc, total_pf, wb4)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        '''
        values = (row.id, row.season, row.week, row['rank'], row.team,
                  row.win_perc, row.record, row.total_pf, row.wb4)

        c.execute(query, values)
        connection.commit()
        print('Success!', end='\n')


def commit_standings_2021(connection, standings: pd.DataFrame):
    print(f'Writing standings to database')
    for idx, row in standings.iterrows():

        print(f'Committing {row["rank"]}. {row.team}...', end='')
        c = connection.cursor()

        query = '''
        INSERT INTO
        standings_2021
            (id, season, week, `rank`, team, win_perc, m_record, total_pf, ov_record, thw_record, wb2, wb5, pb6)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        '''
        values = (row.id, row.season, row.week, row['rank'], row.team, row.win_perc, row.m_record,
                  row.total_pf, row.ov_record, row.thw_record, row.wb2, row.wb5, row.pb6)

        c.execute(query, values)
        connection.commit()
        print('Success!', end='\n')


def update_standings_db(season: int=const.SEASON):
    d = DataLoader(year=season)
    params = Params(data=d)

    standings = get_standings(params=params, season=season, week=params.as_of_week)
    with ut.mysql_connection() as conn:
        commit_standings_2021(connection=conn, standings=standings)


if __name__ == '__main__':
    update_standings_db()
