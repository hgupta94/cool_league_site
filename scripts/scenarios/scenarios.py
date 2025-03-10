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
            tm1_disp = const.TEAM_IDS[owner1]['name']['display']
            tm2_disp = const.TEAM_IDS[owner2]['name']['display']
            if tm1 == tm2:
                result = 0.0
            else:
                score1 = teams.team_scores(team_id=tm1)[week-1]
                score2 = teams.team_scores(team_id=tm2)[week-1]
                result = 1.0 if score1 > score2 else 0.5 if score1 == score2 else 0.0

            tm_id = f'{season}_{str(week).zfill(2)}_{tm1_disp}_{tm2_disp}'
            row = [tm_id, season, week, tm1_disp, tm2_disp, result]
            df.loc[len(df)] = row

    return df


def schedule_switcher(teams: Teams, season: int, week: int):
    tms = teams.team_ids
    df = pd.DataFrame(columns=['id', 'season', 'week', 'team', 'schedule_of', 'result'])
    for sched_of in tms:
        for t_switch in tms:
            if sched_of != t_switch:
                owner1 = teams.teamid_to_primowner[sched_of]
                owner2 = teams.teamid_to_primowner[t_switch]
                sched_of_disp = const.TEAM_IDS[owner1]['name']['display']
                t_switch_disp = const.TEAM_IDS[owner2]['name']['display']

                # get sched_of team's schedule
                sched_of_sched = teams.team_schedule(sched_of)[week-1]

                # switch sched_of team with t_switch
                tm_sched = teams.team_schedule(t_switch)[week-1]
                score = tm_sched['score']
                new_opp_tm = sched_of_sched['opp']
                new_opp_score = sched_of_sched['opp_score']

                # if team and new opp are the same, need to use actual schedule results
                if t_switch != new_opp_tm:
                    result = 1.0 if score > new_opp_score else 0.5 if score == new_opp_score else 0.0
                else:
                    result = tm_sched['result']

                # print('Schedule of', sched_of_disp)
                # print('Switch with', t_switch_disp, score)
                # print('New opp', const.TEAM_IDS[teams.teamid_to_primowner[new_opp_tm]]['name']['display'], new_opp_score)
                # print('Result:', result, end='\n\n')
                tm_id = f'{season}_{str(week).zfill(2)}_{t_switch_disp}_{sched_of_disp}'
                row = [tm_id, season, week, t_switch_disp, sched_of_disp, result]
                df.loc[len(df)] = row

    return df
