from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params
from scripts.api.Teams import Teams
from scripts.utils import constants as const


def get_standings(season: int,
                  week: int):
    data = DataLoader(season)
    regular_season_end = Params(data).regular_season_end
    teams = Teams(data)
    tm_ids = teams.team_ids

    # calculate weekly medians for the season
    medians = {}
    for wk in range(1, regular_season_end+1):
        medians[wk] = teams.week_median(wk)

    rows = []
    for tm in tm_ids:
        disp_nm = const.TEAM_IDS[teams.teamid_to_primowner[tm]]['name']['display']
        first_nm = const.TEAM_IDS[teams.teamid_to_primowner[tm]]['name']['first']
        db_id = f'{season}_{str(week).zfill(2)}_{disp_nm}'

        matchups = teams.team_schedule(tm)
        matchups_filt = [{k: v for k, v in d.items()} for d in matchups if d.get('week') <= week]
        m_wins = sum(d.get('result', 0) for d in matchups_filt)
        m_losses = week - m_wins
        points = round(sum(d.get('score', 0) for d in matchups_filt), 2)

        th_wins = 0
        for i in matchups_filt:
            th_wins += 1 if i['score'] > medians[i['week']] else 0.5 if i['score'] == medians[i['week']] else 0
        th_losses = week - th_wins

        row = [db_id, season, week, first_nm, m_wins, m_losses, th_wins, th_losses, points]
        rows.append(row)
    return rows


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
