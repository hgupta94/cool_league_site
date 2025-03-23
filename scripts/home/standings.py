from scripts.api.Teams import Teams
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
        th_result = 1 if matchups_filter['score'] > median else 0.5 if matchups_filter['score'] == median else 0
        score = matchups_filter['score']

        row = [db_id, season, week, display_name, opponent_display_name, matchup_result, th_result, score]
        rows.append(row)
    return rows


def format_standings():
    ...
