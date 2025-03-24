import pandas as pd

from scripts.api.Teams import Teams
from scripts.simulations.season_simulation import regular_season_end
from scripts.utils import constants


def get_matchup_results(teams: Teams,
                        season: int,
                        week: int):
    tm_ids = teams.team_ids

    # get median for the week
    median = teams.week_median(week)

    rows = []
    for tm in tm_ids:
        display_name = constants.TEAM_IDS[teams.teamid_to_primowner[tm]]['name']['display']
        db_id = f'{season}_{str(week).zfill(2)}_{display_name}'

        matchups = teams.team_schedule(tm)
        matchups_filter = [{k: v for k, v in d.items()} for d in matchups if d.get('week') == week][0]
        opponent_display_name = constants.TEAM_IDS[teams.teamid_to_primowner[matchups_filter['opp']]]['name']['display']
        matchup_result = matchups_filter['result']
        th_result = 1.0 if matchups_filter['score'] > median else 0.5 if matchups_filter['score'] == median else 0.0
        score = matchups_filter['score']

        # row = [db_id, season, week, display_name, opponent_display_name, matchup_result, th_result, score]
        row = {
            'id': db_id,
            'season': season,
            'week': week,
            'team': display_name,
            'opponent': opponent_display_name,
            'matchup_result': matchup_result,
            'top_half_result': th_result,
            'score': score
        }
        rows.append(row)
    return rows


def format_standings(week):
    from scripts.api.DataLoader import DataLoader
    from scripts.api.Settings import Params
    from scripts.utils import utils
    import pandas as pd

    season, week = 2023, 12
    data = DataLoader(year=season)
    teams = Teams(data)
    params = Params(data)
    n_playoff_teams = params.playoff_teams
    regular_season_end = params.regular_season_end
    # weeks_left = params.weeks_left
    weeks_left = regular_season_end - week

    results = []
    for wk in range(1, week+1):
        results.extend(get_matchup_results(teams=teams, season=season, week=wk))

    rows = []
    for team in teams.team_ids:
        display_name = constants.TEAM_IDS[teams.teamid_to_primowner[team]]['name']['display']
        team_matchups = [m for m in results if m['team'] == display_name]

        m_wins = sum(d['matchup_result'] for d in team_matchups)
        m_losses = week - m_wins
        m_record = f'{int(m_wins)}-{int(m_losses)}'

        th_wins = sum(d['top_half_result'] for d in team_matchups)
        th_losses = week - th_wins
        th_record = f'{int(th_wins)}-{int(th_losses)}'

        ov_wins = m_wins + th_wins
        ov_losses = m_losses + th_losses
        ov_record = f'{int(ov_wins)}-{int(ov_losses)}'

        win_pct = f'{(ov_wins / (week*2)):.3f}'

        total_points = f"{sum(d['score'] for d in team_matchups):.2f}"

        rows.append([display_name, ov_record, ov_wins, win_pct, m_record, th_record, total_points])

    cols = ['team', 'overall', 'overall_wins', 'win_perc', 'matchup', 'top_half', 'total_points']
    standings = pd.DataFrame(rows, columns=cols)
    standings.sort_values(['win_perc', 'total_points'], ascending=[False, False], inplace=True)

    if season >= 2021:
        playoff_list = []

        top5 = standings.head(n_playoff_teams-1)
        playoff_list.extend(top5.team.to_list())

        sixth = standings[~standings.team.isin(playoff_list)].sort_values('total_points', ascending=False).head(1)
        playoff_list.extend(sixth.team.values)

        rest = (
            standings[~standings.team.isin(playoff_list)]
            .sort_values(['overall_wins', 'total_points'], ascending=[False, False])
        )

        standings = pd.concat([top5, sixth, rest], axis=0)
        standings['rank'] = range(1, len(standings)+1)

        # TODO: need to check these calculations - subtract from seed or seed+1?
        two_seed_wins = standings.iloc[1].overall_wins
        two_seed_points = standings.iloc[1].total_points
        five_seed_wins = standings.iloc[4].overall_wins
        five_seed_points = standings.iloc[4].total_points
        six_seed_points = standings.iloc[5].total_points

        standings['wb2'] = (two_seed_wins - standings.overall_wins) / 2
        standings['wb5'] = (five_seed_wins - standings.overall_wins) / 2
        standings['pb6'] = float(six_seed_points) - standings.total_points.astype(float)

        for idx, row in standings.iterrows():
            break

        # check if team clinched a bye
        def clinch_bye(row, week):
            if week < regular_season_end:
                if row['wb2'] < -weeks_left:
                    return -99  # clinched

                elif row['wb2'] > weeks_left:
                    return 99  # eliminated

                else:
                    return row['wb2']

        def clinch_playoff(row, week):
            if week < regular_season_end:
                if row['wb5'] < -weeks_left:
                    return -99  # clinched

                elif row['wb5'] > weeks_left:
                    return 99  # eliminated

                else:
                    return row['wb5']

        def format_weeks_back(value):
            if value == -99:
                return 'c'
            elif value == 99:
                return 'x'
            elif value < 0:
                return f'+{abs(value)}'
            elif value > 0:
                return f'{value}'
            else:
                return '-'

        def format_points_back(value):
            if value < 0:
                return f'+{abs(value):.2f}'
            elif value == 0:
                return '-'
            else:
                return f'{value:.2f}'

        standings['wb2'] = standings.apply(lambda x: clinch_bye(x, week), axis=1)
        standings['wb2'] = standings.wb2.apply(lambda x: format_weeks_back(x))
        standings['wb5'] = standings.apply(lambda x: clinch_playoff(x, week), axis=1)
        standings['wb5'] = standings.wb5.apply(lambda x: format_weeks_back(x))
        standings['pb6'] = standings.pb6.apply(lambda x: format_points_back(x))

