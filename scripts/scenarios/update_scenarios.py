import pandas as pd

from scripts.utils import (utils as ut, constants as const)
from scripts.scenarios.scenarios import (get_h2h, schedule_switcher)


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
        values = (row.id, row.season, row.week, row.team, row.opp, row.win)

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


def update_scenarios_db(season: int=const.SEASON,
                        league_id: int=const.LEAGUE_ID,
                        swid: str=const.SWID,
                        espn_s2: str=const.ESPN_S2):

    d = ut.load_data(league_id=league_id, swid=swid, espn_s2=espn_s2, season=season)
    params = ut.get_params(d)
    week = params['current_week']
    end = params['regular_season_end']

    if week <= end:
        h2h_data = get_h2h(params=params, season=season, week=week)
        ss_data = schedule_switcher(params=params, season=season, week=week)
        with ut.mysql_connection() as conn:
            commit_h2h(connection=conn, h2h_data=h2h_data)
            commit_ss(connection=conn, ss_data=ss_data)


if __name__ == '__main__':
    update_scenarios_db()
