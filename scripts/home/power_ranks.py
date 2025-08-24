import pandas as pd
import numpy as np
import math

from scripts.utils.database import Database


def linear_decay(x, r):
    """Calculates weights for each week using an linear decay function"""
    return r / ((x * (x + 1)) / 2)


def exp_decay(week: int, r=3, reverse=False) -> list:
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


def power_rank(season, week):
    """
    Calculates a weekly power ranking and power score for each team
    Factors taken into account:
        1. Total Scoring Index (40%) -
        1. Weekly Scoring Index (30%) - recent weeks weighted more
        2. Consistency Index (20%) - variance of weekly scoring
        3. Luck Index (10%) - difference in matchup wins vs. expected
    """
    with Database() as conn:
        query = f'''
        SELECT *
        FROM matchups
        WHERE season={season} AND week<={week}
        '''
        matchups = pd.read_sql(query, con=conn)
    matchups['median'] = matchups.groupby('week')['score'].transform('median')

    # scoring weights
    if week == 1:
        ts_idx_wt = 0.45
        ws_idx_wt = 0.45
        c_idx_wt = 0.0
        l_idx_wt = 0.1
    else:
        ts_idx_wt = 0.4
        ws_idx_wt = 0.3
        c_idx_wt = 0.2
        l_idx_wt = 0.1

    ppg_med = matchups.groupby('team').score.mean().median()
    wts = exp_decay(week=week, reverse=False)
    pr_dict = {}
    for t in matchups.team:
        scores = []
        pr_tm = matchups[matchups.team == t]
        tm_score_index = scoring_index(pr_tm.score.mean(), ppg_med, weight=1)
        pr_dict[t] = {'season_idx': tm_score_index.item()}
        for wk in range(1, week+1):
            # Weekly Scoring Index
            pr_wk = pr_tm[pr_tm.week == wk]
            wk_med = pr_wk['median'].values[0]
            wk_wt = wts[wk-1]
            wk_t_score = pr_wk.score.values[0]
            s_idx = scoring_index(score=wk_t_score, median=wk_med, weight=wk_wt)
            scores.append(s_idx)
        pr_dict[t].update({'week_idx': sum(scores).item()})

        # Consistency Index
        sd = pr_tm.score.std()
        tm_ppg = pr_tm.score.mean()
        c_idx = float(0) if len(pr_tm) < 2 else consistency_index(sd=sd, ppg=tm_ppg, ppg_median=ppg_med)
        try:
            pr_dict[t].update({'consistency_idx': c_idx.item()})
        except AttributeError:
            pr_dict[t].update({'consistency_idx': c_idx})

        # Luck Index
        luck_score = pr_tm.tophalf_result.sum() - pr_tm.matchup_result.sum()
        pr_dict[t].update({'luck_idx': scale_luck(luck_score, from_min=-week, from_max=week).item()})

        total_score = (pr_dict[t]['season_idx'] * ts_idx_wt)\
                      + (pr_dict[t]['week_idx'] * ws_idx_wt)\
                      + (pr_dict[t]['consistency_idx'] * c_idx_wt)\
                      + ((pr_dict[t]['luck_idx']-0.5) * l_idx_wt)
        pr_dict[t].update({'power_score_raw': total_score})

    meds = []
    for outer_key, inner_dict in pr_dict.items():
        for inner_key, value in inner_dict.items():
            if inner_key == 'power_score_raw':
                meds.append(value)
    med = np.median(meds).item()
    for k, v in pr_dict.items():
        pr_dict[k].update({'power_score_norm': v['power_score_raw']/med})
    sorted_pr_norm = dict(sorted(pr_dict.items(), key=lambda item: item[1]['power_score_norm']))

    return sorted_pr_norm
