from scripts.api.Settings import Params

import pandas as pd


def get_h2h(params: Params, season: int, week: int):
    scores = params.scores_df
    teams = params.teams

    df = pd.DataFrame(columns=['id', 'season', 'week', 'team', 'opp', 'result'])
    for tm1 in teams:
        for tm2 in teams:
            tm1_disp = params.team_map[tm1]['name']['display']
            tm2_disp = params.team_map[tm2]['name']['display']
            if tm1 == tm2:
                result = 0
            else:
                score1 = scores[(scores.week == week)
                                & (scores.team == tm1)].score.values[0]
                score2 = scores[(scores.week == week)
                                & (scores.team == tm2)].score.values[0]
                result = 1 if score1 > score2 else 0.5 if score1 == score2 else 0

            tm_id = f'{season}_{str(week).zfill(2)}_{tm1_disp}_{tm2_disp}'
            row = [tm_id, season, week, tm1_disp, tm2_disp, result]
            df.loc[len(df)] = row

    return df


def schedule_switcher(params: Params, season: int, week: int):
    teams = params.teams
    schedule = params.matchups_df
    scores = params.scores_df

    # get team 1's schedule
    hm_cols = ['week', 'team', 'score', 'opp', 'opp_score', 'team_result', 'opp_result']
    aw_cols = ['week', 'opp', 'opp_score', 'team', 'score', 'opp_result', 'team_result']
    df = pd.DataFrame(columns=['id', 'season', 'week', 'team', 'schedule_of', 'result'])
    for t_sched in teams:
        for t_switch in teams:
            if t_sched != t_switch:
                t_sched_disp = params.team_map[t_sched]['name']['display']
                t_switch_disp = params.team_map[t_switch]['name']['display']

                # get first team's schedule
                hm = schedule[schedule.team1_id == t_sched]
                hm.columns = hm_cols
                aw = schedule[schedule.team2_id == t_sched]
                aw.columns = aw_cols
                tm_sched = pd.concat([hm, aw]).sort_values('week')

                # switch new team with first team
                new_scores = scores[scores.team == t_switch]
                score = new_scores[(new_scores.week == week)
                                   & (new_scores.team == t_switch)].score.values[0]
                opp = tm_sched[tm_sched.week == week]
                opp_tm = opp.opp.values[0]
                opp_score = opp.opp_score.values[0]

                # if team and new opp are the same, need to use actual schedule results
                if t_switch != opp_tm:
                    result = 1.0 if score > opp_score else 0.5 if score == opp_score else 0.0
                else:
                    act_match = tm_sched[(tm_sched.week == week)
                                         & (tm_sched.team == t_sched)
                                         & (tm_sched.opp == t_switch)]
                    result = act_match.opp_result.values[0]

                # print('Schedule of', t_sched_disp, score)
                # print('Switch with', t_switch_disp)
                # print('New opp', params.team_map'][opp_tm]['name']['display'], opp_score)
                # print('Result:', result, end='\n\n')
                tm_id = f'{season}_{str(week).zfill(2)}_{t_sched_disp}_{t_switch_disp}'
                row = [tm_id, season, week, t_sched_disp, t_switch_disp, result]
                df.loc[len(df)] = row

    return df
