from scripts.api.Teams import Teams
from scripts.utils import constants as const
import pandas as pd


def get_h2h(teams: Teams, season: int, week: int):
    tms = teams.team_ids
    df = pd.DataFrame(columns=['id', 'season', 'week', 'team', 'opp', 'result'])
    for tm1 in tms:
        for tm2 in tms:
            owner1 = teams.teamid_to_primowner[tm1]
            owner2 = teams.teamid_to_primowner[tm2]
            tm1_display = const.TEAM_IDS[owner1]['name']['display']
            tm2_display = const.TEAM_IDS[owner2]['name']['display']
            if tm1 == tm2:
                result = 0.0
            else:
                score1 = teams.team_scores(team_id=tm1)[week-1]
                score2 = teams.team_scores(team_id=tm2)[week-1]
                result = 1.0 if score1 > score2 else 0.5 if score1 == score2 else 0.0

            tm_id = f'{season}_{str(week).zfill(2)}_{tm1_display}_{tm2_display}'
            row = [tm_id, season, week, tm1_display, tm2_display, result]
            df.loc[len(df)] = row

    return df


def schedule_switcher(teams: Teams, season: int, week: int):
    tms = teams.team_ids
    df = pd.DataFrame(columns=['id', 'season', 'week', 'team', 'schedule_of', 'result'])
    for schedule_of in tms:
        for team_switch in tms:
            if schedule_of != team_switch:
                owner1 = teams.teamid_to_primowner[schedule_of]
                owner2 = teams.teamid_to_primowner[team_switch]
                schedule_of_display = const.TEAM_IDS[owner1]['name']['display']
                team_switch_display = const.TEAM_IDS[owner2]['name']['display']

                # get sched_of team's schedule
                schedule_of_schedule = teams.team_schedule(schedule_of)[week-1]

                # switch sched_of team with t_switch
                tm_sched = teams.team_schedule(team_switch)[week-1]
                score = tm_sched['score']
                new_opp_tm = schedule_of_schedule['opp']
                new_opp_score = schedule_of_schedule['opp_score']

                # if team and new opp are the same, need to use actual schedule results
                if team_switch != new_opp_tm:
                    result = 1.0 if score > new_opp_score else 0.5 if score == new_opp_score else 0.0
                else:
                    result = tm_sched['result']

                # print('Schedule of', sched_of_disp)
                # print('Switch with', t_switch_disp, score)
                # print('New opp', const.TEAM_IDS[teams.teamid_to_primowner[new_opp_tm]]['name']['display'], new_opp_score)
                # print('Result:', result, end='\n\n')
                tm_id = f'{season}_{str(week).zfill(2)}_{team_switch_display}_{schedule_of_display}'
                row = [tm_id, season, week, team_switch_display, schedule_of_display, result]
                df.loc[len(df)] = row

    return df
