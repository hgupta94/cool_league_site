import pandas as pd

def get_h2h(params: dict, season: int, week: int):
    scores = params['scores_df']
    teams = params['teams']

    # get end week for loop
    matchup_week = params['matchup_week']
    regular_season_end = params['regular_season_end']
    end_week = matchup_week if matchup_week <= regular_season_end else regular_season_end

    df = pd.DataFrame(columns=['id', 'season', 'week', 'team', 'opp', 'result'])
    for wk in range(1, end_week+1):
        for tm1 in teams:
            for tm2 in teams:
                tm1_disp = params['team_map'][tm1]['name']['display']
                tm2_disp = params['team_map'][tm2]['name']['display']
                if tm1 == tm2:
                    result = 0
                else:
                    score1 = scores[(scores.week == wk) & (scores.team == tm1)].score.values[0]
                    score2 = scores[(scores.week == wk) & (scores.team == tm2)].score.values[0]
                    result = 1 if score1 > score2 else 0.5 if score1 == score2 else 0

                tm_id = f'{season}_{str(wk).zfill(2)}_{tm1_disp}_{tm2_disp}'
                row = [tm_id, season, wk, tm1_disp, tm2_disp, result]
                df.loc[len(df)] = row
    return df[df.week == week]


def schedule_switcher(params: dict, season: int, week: int):
    teams = params['teams']
    schedule = params['matchup_df']
    scores = params['scores_df']

    # get end week for loop
    matchup_week = params['matchup_week']
    regular_season_end = params['regular_season_end']
    end_week = matchup_week if matchup_week <= regular_season_end else regular_season_end

    # get team 1's schedule
    hm_cols = ['week', 'team', 'score', 'opp', 'opp_score', 'team_result', 'opp_result']
    aw_cols = ['week', 'opp', 'opp_score', 'team', 'score', 'opp_result', 'team_result']
    df = pd.DataFrame(columns=['id', 'season', 'week', 'team', 'schedule_of', 'wins'])
    for t_sched in teams:
        for t_switch in teams:
            if t_sched != t_switch:
                t_sched_disp = params['team_map'][t_sched]['name']['display']
                t_switch_disp = params['team_map'][t_switch]['name']['display']
                wins = 0

                # get first team's schedule
                hm = schedule[schedule.team1_id == t_sched]
                hm.columns = hm_cols
                aw = schedule[schedule.team2_id == t_sched]
                aw.columns = aw_cols
                tm_sched = pd.concat([hm, aw]).sort_values('week')

                # switch new team with first team
                new_scores = scores[scores.team == t_switch]
                for wk in range(1, end_week+1):
                    score = new_scores[(new_scores.week == wk) & (new_scores.team == t_switch)].score.values[0]
                    opp = tm_sched[tm_sched.week == wk]
                    opp_tm = opp.opp.values[0]
                    opp_score = opp.opp_score.values[0]
                    if t_switch != opp_tm:
                        wins += 1 if score > opp_score else 0.5 if score == opp_score else 0
                    else:
                        act_match = tm_sched[(tm_sched.week == wk) & (tm_sched.team == t_sched) & (tm_sched.opp == t_switch)]
                        wins += act_match.opp_result.values[0]

                # print('Schedule of', t_sched)
                # print('Switch with', t_switch)
                # print('Wins:', wins, end='\n')
                tm_id = f'{season}_{str(wk).zfill(2)}_{t_sched_disp}_{t_switch_disp}'
                row = [tm_id, season, wk, t_switch_disp, t_sched_disp, wins]
                df.loc[len(df)] = row

    return df
