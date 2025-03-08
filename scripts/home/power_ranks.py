import pandas as pd
import numpy as np
import math


def linear_decay(x, r):
    """Calculates weights for each week using an linear decay function"""
    return r / ((x * (x + 1)) / 2)


def exp_decay(week: int, r=1.5, reverse=False) -> list:
    """Calculates weights for each week using an exponential decay function"""

    wts = []
    for w in range(1, week+1):
        if reverse:
            wts.append(math.exp(-w * 1/r))
        else:
            wts.append(math.exp(w * 1/r))

    return [(w/sum(wts)) for w in wts]  # scale so sum == 1


def scoring_index(score, median, weight):
    return (score / median) * weight


def consistency_index(sd, ppg, ppg_median):
    return (1 - (sd / ppg)) * (ppg / ppg_median)


def scale_luck(x, from_min=-1, from_max=1, to_min=0, to_max=1):
    return (x - from_min) * (to_max - to_min) / (from_max - from_min) + to_min


def power_rank(params, week):
    """
    Calculates a weekly power ranking and power score for each team
    Factors taken into account:
        1. Total Scoring Index (40%) -
        1. Weekly Scoring Index (30%) - recent weeks weighted more
        2. Consistency Index (20%) - variance of weekly scoring
        3. Luck Index (10%) - difference in matchup wins vs. expected
    """

    # return parameters
    matchup_df = params['matchup_df']
    n_teams = params['league_size']
    teams = params['teams']
    teams.sort()

    # scoring weights
    ts_idx_wt = 0.4
    ws_idx_wt = 0.3
    c_idx_wt = 0.2
    l_idx_wt = 0.1

    # Calculate W/L
    matchup_df = matchup_df[matchup_df.week <= week]
    matchup_df['team1_result'] = np.where(matchup_df['score1'] > matchup_df['score2'], 1.0, 0.0)
    matchup_df['team2_result'] = np.where(matchup_df['score2'] > matchup_df['score1'], 1.0, 0.0)
    mask = (matchup_df.score1 == matchup_df.score2)\
           & (matchup_df.score1 > 0)\
           & (matchup_df.score2 > 0)  # Account for ties
    matchup_df.loc[mask, ['team1_result', 'team2_result']] = 0.5

    # convert dataframe to long format so each row is a team week, not matchup
    home = matchup_df.iloc[:, [0, 1, 2, 5]].rename(columns={
        'team1_id': 'team',
        'score1': 'score',
        'team1_result': 'result'
    })
    home['id'] = home['team'].astype(str) + home['week'].astype(str)
    away = matchup_df.iloc[:, [0, 3, 4, 6]].rename(columns={
        'team2_id': 'team',
        'score2': 'score',
        'team2_result': 'result'
    })
    away['id'] = away['team'].astype(str) + away['week'].astype(str)
    pr_df = pd.concat([home, away]).sort_values(['week', 'id']).reset_index(drop=True)
    pr_df['rank'] = pr_df.groupby('week').score.rank()

    ppg_med = pr_df.groupby('team').score.mean().median()
    wts = exp_decay(week=week, reverse=False)
    pr_dict = {}
    for t in teams:
        scores = []
        luck = []
        pr_tm = pr_df[pr_df.team == t]
        ts_index = scoring_index(pr_tm.score.mean(), ppg_med*14, 1)
        for wk in range(1, week+1):
            # Weekly Scoring Index
            pr_wk = pr_tm[pr_tm.week == wk]
            wk_med = round(np.median(pr_df[pr_df.week == wk].score.to_list()), 2)
            wk_wt = wts[wk-1]
            wk_t_score = pr_wk.score.values[0]
            s_idx = scoring_index(score=wk_t_score, median=wk_med, weight=wk_wt)
            scores.append(s_idx)

            # Luck Index
            raw_score = (pr_wk['result'] - ((pr_wk['rank']-1) / (n_teams-1))).item()
            luck.append(round(raw_score, 2))

        pr_dict[t] = [ts_index]
        pr_dict[t].append[sum(scores)]
        pr_dict[t].append(round(1-scale_luck(x=sum(luck)), 2))

        # Consistency Index
        sd = pr_tm.score.std()
        tm_ppg = pr_tm.score.mean()
        c_idx = 0 if len(pr_tm) < 2 else consistency_index(sd=sd, ppg=tm_ppg, ppg_median=ppg_med)
        pr_dict[t].append(c_idx)

        total_score = (pr_dict[t][0] * ts_idx_wt)\
                      + (pr_dict[t][1] * ws_idx_wt)\
                      + (pr_dict[t][2] * c_idx_wt)\
                      + (pr_dict[t][3] * l_idx_wt)
        pr_dict[t] = total_score

    med = np.median([v for v in pr_dict.values()])
    sorted_pr = {k: v / med for k, v in sorted(pr_dict.items(), key=lambda item: item[1])}

    return sorted_pr
