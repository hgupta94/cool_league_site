import numpy as np
import math

from scripts.utils.database import Database
from scripts.api.settings import LeagueSettings, TeamSettings


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


def power_rank(params: LeagueSettings,
               teams: TeamSettings,
               season: int,
               week: int):
    """
    Calculates a weekly power ranking and power score for each team
    Factors taken into account:
        1. Total Scoring Index (40%) -
        1. Weekly Scoring Index (30%) - recent weeks weighted more
        2. Consistency Index (20%) - variance of weekly scoring
        3. Luck Index (10%) - difference in matchup wins vs. expected
    """
    wks_played_factor = week / params.regular_season_end
    wks_rem_factor = (params.regular_season_end - week) / params.regular_season_end

    # scoring weights
    if week < 2:
        ts_idx_wt = 0.45  # total score (actual & projected points)
        ws_idx_wt = 0.45  # week score
        c_idx_wt  = 0.00  # consistency
        l_idx_wt  = 0.05  # luck
        m_idx_wt  = 0.05  # manager
    else:
        ts_idx_wt = 0.40
        ws_idx_wt = 0.30
        c_idx_wt  = 0.15
        m_idx_wt  = 0.10
        l_idx_wt  = 0.05
    consistency_factor = 1 if week >= 5 else week / 5  # increase by 20% each week

    # load data from db
    season_sim = Database(table='season_sim', season=season, week=week+1).retrieve_data(how='week')
    eff = Database(table='efficiency', season=season, week=week).retrieve_data(how='season')
    h2h = Database(table='h2h', season=season, week=week).retrieve_data(how='season')
    ss = Database(table='schedule_switcher', season=season, week=week).retrieve_data(how='season')
    matchups = Database(table='matchups', season=season, week=week).retrieve_data(how='season')
    matchups = matchups[matchups.week <= params.regular_season_end]
    matchups['median'] = matchups.groupby('week')['score'].transform('median')

    sim_ppg_med = (season_sim.total_points.median() / params.regular_season_end) * wks_rem_factor
    ppg_med = (0 if week == 0 else matchups.groupby('team').score.mean().median()) * wks_played_factor
    eff_med = eff.groupby('team').actual_lineup_score.mean().median() / eff.groupby('team').optimal_lineup_score.mean().median()
    wts = [1] if week == 0 else exp_decay(week=week, reverse=False)
    pr_dict = {}
    c_scores = {}
    l_scores = {}
    for t in teams.teams:
        # Season Scoring Index (includes season projections)
        pr_tm = matchups[matchups.team == t]
        pr_tm_sim = season_sim[season_sim.team == t]
        act_ppg = 0 if week == 0 else pr_tm.score.mean()
        sim_ppg = pr_tm_sim.total_points.values[0] / params.regular_season_end
        tm_ppg = (act_ppg * wks_played_factor) + (sim_ppg * wks_rem_factor)
        tm_score_index = scoring_index(tm_ppg, sim_ppg_med + ppg_med, weight=1)
        pr_dict[t] = {'season_idx': tm_score_index.item()}

        if week > 0:
            scores = []
            for wk in range(1, week+1):
                # Weekly Scoring Index
                pr_wk = pr_tm[pr_tm.week == wk]
                wk_med = pr_wk['median'].values[0]
                wk_wt = wts[wk-1]
                wk_t_score = pr_wk.score.values[0]
                s_idx = scoring_index(score=wk_t_score, median=wk_med, weight=wk_wt)
                scores.append(s_idx)
            pr_dict[t].update({'week_idx': sum(scores)})

            # Luck Index
            # compare matchup record to schedule switcher
            tm_m_wp = matchups[matchups.team==t].matchup_result.sum() / week
            ss_wp = ss[(ss.team==t) & (ss.schedule_of!=t)].result.sum() / ((len(set(matchups.team))-1) * week)
            tm_m_luck = scale_luck(tm_m_wp - ss_wp)

            # compare tophalf record to h2h data
            tm_th_wp = matchups[matchups.team==t].tophalf_result.sum() / week
            th_wp = h2h[h2h.team==t].result.sum() / ((len(set(matchups.team))-1) * week)
            tm_th_luck = scale_luck(tm_th_wp - th_wp)
            l_scores[t] = tm_m_luck + tm_th_luck
            pr_dict[t].update({'luck_idx': (tm_m_luck + tm_th_luck) / 2})

            # Consistency Index
            sd = pr_tm.score.std()
            tm_ppg = pr_tm.score.mean()
            c_idx = 0 if len(pr_tm) < 2 else consistency_index(sd=sd, ppg=tm_ppg, ppg_median=ppg_med)
            c_scores[t] = c_idx * consistency_factor

            # Manager Index
            tm_eff = eff[eff.team==t]
            lineup_eff = tm_eff.actual_lineup_score.sum() / tm_eff.optimal_lineup_score.sum()
            m_idx = scoring_index(score=lineup_eff, median=eff_med, weight=1)
            pr_dict[t].update({'manager_idx': m_idx})
        else:
            pr_dict[t].update({'week_idx': 1})
            pr_dict[t].update({'luck_idx': 1})
            c_scores[t] = 1
            pr_dict[t].update({'manager_idx': 1})

        if week >= 2:
            c_idx_new = scoring_index(score=c_scores[t], median=np.median([c for c in c_scores.values()]), weight=1)
            pr_dict[t].update({'consistency_idx': c_idx_new})
        else:
            pr_dict[t].update({'consistency_idx': 1})

        total_score = (pr_dict[t]['season_idx'] * wks_rem_factor * ts_idx_wt) \
                      + (pr_dict[t]['week_idx'] * wks_played_factor * ws_idx_wt) \
                      + (pr_dict[t]['consistency_idx'] * c_idx_wt) \
                      + (pr_dict[t]['manager_idx'] * m_idx_wt) \
                      + (pr_dict[t]['luck_idx'] * wks_played_factor * l_idx_wt)
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
