from scripts.api.settings import LeagueSettings, TeamSettings
from scripts.api.models.schedule import TeamSchedule
from scripts.utils import constants as const
import scripts.utils.utils as ut

import pandas as pd


def get_h2h(
        season: int = const.SEASON,
        week: int = const.WEEK-1  # week just finished
) -> list[dict]:
    """
    Build pairwise head-to-head results for all teams in a given season/week.

    Args:
        season (int): NFL season to evaluate. Defaults to const.SEASON
        week (int): NFL week to evaluate. Defaults to const.WEEK

    Returns:
        list[dict]: A list of dictionaries with keys:
            - `team`: Team ID for the row team
            - `opponent`: Team ID for the compared team
            - `result`: Head-to-head outcome for `team` vs `opponent`
    """
    schedules = TeamSchedule.get_all_team_schedules(week=week)

    team_ids = list(schedules.keys())
    team_h2h = []
    for team1 in team_ids:
        for team2 in team_ids:
            owner1 = schedules[team1][week]
            owner2 = schedules[team2][week]
            if team1 == team2:
                result = 0.0
            else:
                score1 = owner1.team_score
                score2 = owner2.team_score
                result = 1.0 if score1 > score2 else 0.5 if score1 == score2 else 0.0
            team_h2h.append(
                {
                    'season': season,
                    'week': week,
                    'team': team1,
                    'opponent': team2,
                    'result': result
                }
            )
    return team_h2h


def get_total_wins(h2h_data: pd.DataFrame,
                   teams: TeamSettings,
                   week: int):
    """
    Calculate team's total wins: sum of wins against all teams for each week
    """
    end = week-1

    total_wins = h2h_data.groupby('team').result.sum().reset_index()
    total_wins['losses'] = (((len(teams.team_ids)-1) * end) - total_wins.result)
    total_wins['record'] = total_wins.result.astype('Int32').astype(str) + '-' + total_wins.losses.astype('Int32').astype(str)
    total_wins['win_perc'] = total_wins.result / ((len(teams.team_ids) -1 ) * end)
    total_wins['win_perc'] = total_wins.win_perc.map('{:.3f}'.format)
    return total_wins[['team', 'result', 'record', 'win_perc']]


def get_wins_by_week(h2h_data: pd.DataFrame,
                     total_wins: pd.DataFrame,
                     params: LeagueSettings,
                     teams: TeamSettings):
    """
    Calculate team's record vs league median for each week
    """
    wins_by_week = h2h_data.groupby(['team', 'week']).result.sum().reset_index()
    wins_by_week['losses'] = (len(teams.team_ids) -1) - wins_by_week.result
    wins_by_week['record'] = wins_by_week.result.astype('Int32').astype(str) + '-' + wins_by_week.losses.astype('Int32').astype(str)
    best_str = f'{int(wins_by_week.result.max())}-{int(wins_by_week.result.min())}'
    worst_str = f'{int(wins_by_week.result.min())}-{int(wins_by_week.result.max())}'
    wins_by_week_p = wins_by_week.pivot(index='team', columns='week', values='record')
    wins_by_week_p = wins_by_week_p.reindex(columns=list(range(1, params.regular_season_end+1))).fillna('')
    wins_by_week_p['weeks_best'] = (wins_by_week_p == best_str).sum(axis=1).astype(str)
    wins_by_week_p['weeks_worst'] = (wins_by_week_p == worst_str).sum(axis=1).astype(str)
    return (
        pd.merge(wins_by_week_p, total_wins, on='team')
        .sort_values('result', ascending=False)
        .drop(columns=['result', 'record', 'win_perc'], axis=1)
    )


def get_wins_vs_opp(h2h_data: pd.DataFrame,
                    total_wins: pd.DataFrame,
                    wins_by_week: pd.DataFrame,
                    week: int):
    """
    Calculate team's record if he played every team each week
    """
    end = week-1

    wins_vs_opp = h2h_data.groupby(['team', 'opponent']).result.sum().reset_index()
    wins_vs_opp['losses'] = end - wins_vs_opp.result
    wins_vs_opp['record'] = wins_vs_opp.result.astype('Int32').astype(str) + '-' + wins_vs_opp.losses.astype('Int32').astype(str)
    wins_vs_opp_p = wins_vs_opp.pivot(index='team', columns='opponent', values='record')
    wins_vs_opp_final = pd.merge(wins_vs_opp_p, total_wins, on='team').sort_values('win_perc', ascending=False)
    col_order = ut.flatten_list([['team'], wins_by_week.team.to_list(), ['record', 'win_perc']])
    wins_vs_opp_final = wins_vs_opp_final[col_order].set_index('team')
    for i in range(min(wins_vs_opp_final.shape)):
        # blank out diagonals where teams intersect
        wins_vs_opp_final.iloc[i, i] = ''
    return wins_vs_opp_final.reset_index()


def schedule_switcher(
        season: int = const.SEASON,
        week: int = const.WEEK-1  # week just finished
):
    """
    Create the schedule switcher dataframe
    """
    schedules = TeamSchedule.get_all_team_schedules(week=week)
    team_ids = list(schedules.keys())
    switches = []
    for team in team_ids:
        for schedule_of in team_ids:
            switch_with_sched = schedules[team][week]
            schedule_of_sched = schedules[schedule_of][week]

            # switch sched_of team with switch_with team
            score = switch_with_sched.team_score
            new_opp_tm = schedule_of_sched.opponent_id
            new_opp_score = schedule_of_sched.opponent_score

            # if team and new opp are the same, need to use actual schedule results
            if team != new_opp_tm:
                result = 1.0 if score > new_opp_score else 0.5 if score == new_opp_score else 0.0
            else:
                result = float(switch_with_sched.matchup_result)
            switches.append({
                'season': season,
                'week': week,
                'team': team,
                'schedule_of': schedule_of,
                'result': result,
            })
    return switches


def calculate_schedule_luck(ss_data: pd.DataFrame):
    """
    Calculate each team's schedule luck: difference of a teams' actual matchup wins and the average number of wins using all other schedules.
    Positive values indicate team is luckier
    """
    teams = set(ss_data.team)
    luck = {}
    for t in teams:
        ss_t = ss_data[ss_data.team == t]
        wins_act = ss_t[ss_t.schedule_of == t].result.sum()
        wins_exp = ss_t[ss_t.schedule_of != t].result.mean() * len(set(ss_data.week))
        diff = (wins_act - wins_exp)
        luck[t] = f'{"+" if diff >= 0 else ""}{diff:.1f}'
    return dict(sorted(luck.items(), key=lambda item: float(item[1]), reverse=True))


def get_schedule_switcher_display(ss_data: pd.DataFrame,
                                  total_wins: pd.DataFrame,
                                  week):
    """
    Format schedule switcher table for display on website.
    """
    end = week-1

    ss_data = ss_data.groupby(['team', 'schedule_of']).result.sum().reset_index()
    ss_data['losses'] = end - ss_data.result
    ss_data['record'] = ss_data.result.astype(str).str[0] + '-' + ss_data.losses.astype(str).str[0]
    ss_data_p = ss_data.pivot(index='team', columns='schedule_of', values='record')
    ss_data_final = pd.merge(ss_data_p, total_wins, on='team').sort_values('win_perc', ascending=False)
    col_order = ut.flatten_list([['team'], ss_data_final.team.to_list()])
    ss_data_final = ss_data_final[col_order].set_index('team')
    for irow, row in ss_data_final.iterrows():
        # bold diagonals where teams intersect
        for icol, col in enumerate(ss_data_final.columns):
            if irow == col:
                ss_data_final.loc[irow, col] = f'<span class="diagonal">{row[col]}</span>'
    return ss_data_final.reset_index()
