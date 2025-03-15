from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params
from scripts.utils import utils as ut
from scripts.utils import constants as const
from scripts.home.standings import get_standings


def commit_standings(connection,
                     standings: list):
    print(f'Writing standings to database')

    for row in standings:
        print(f'Committing {row[0]}...', end='\n')
        c = connection.cursor()
        query = '''
        INSERT INTO
        standings
            (id, season, week, team, m_wins, m_losses, th_wins, th_losses, total_pf)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        '''
        values = (row[0], row[1], row[2], row[3], row[4],
                  row[5], row[6], row[7], row[8])

        c.execute(query, values)
        connection.commit()
        print('Success!', end='\n')


def update_standings_db(season: int=const.SEASON):
    d = DataLoader(year=season)
    params = Params(data=d)

    standings = get_standings(season=season, week=params.as_of_week)
    with ut.mysql_connection() as conn:
        commit_standings(connection=conn, standings=standings)


if __name__ == '__main__':
    update_standings_db()
