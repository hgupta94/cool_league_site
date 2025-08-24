import json

import pandas as pd

from scripts.api.DataLoader import DataLoader
from scripts.utils.database import Database
from scripts.api.Settings import Params
from scripts.api.Teams import Teams
from scripts.home.standings import Standings
from scripts.scenarios.scenarios import get_total_wins, get_wins_by_week, get_wins_vs_opp, get_schedule_switcher_display
from scripts.simulations import week_sim as ws
from scripts.efficiency.efficiencies import plot_efficiency


# TODO: webpage errors out if past regular season
season, week = 2024, 4  # just finished previous week
data = DataLoader(season)
params = Params(data)
teams = Teams(data)
matchups = data.matchups()

week = params.regular_season_end+1 if week > params.regular_season_end+1 else week
# week_data = data.load_week(week=week)
# rosters = Rosters()

standings = Standings(season=season, week=week)
standings_df = standings.format_standings()
clinches = standings.clinching_scenarios()
# TODO: fix last week clinches/elims. if team is ahead (cl) or behind (el), net wins should be 0?

db_pr = Database(table='power_ranks', season=season, week=week)
pr_data = db_pr.retrieve_data(how='season')
pr_data[['power_score_norm', 'score_norm_change']] = round(pr_data[['power_score_norm', 'score_norm_change']] * 100).astype('Int32')
pr_table = pr_data[pr_data.week == week-1]
pr_table = pr_table.sort_values('power_score_raw', ascending=False)
pr_table['rank_change'] = -pr_table.rank_change
pr_table[['total_points', 'weekly_points', 'consistency', 'luck']] = pr_table[['season_idx', 'week_idx', 'consistency_idx', 'luck_idx']].rank(ascending=False, method='min').astype('Int32')
pr_cols = ['team', 'total_points', 'weekly_points', 'consistency', 'luck', 'power_rank', 'rank_change', 'power_score_norm', 'score_norm_change']
rank_data = pr_data[['team', 'week', 'power_rank', 'power_score_norm']].sort_values(['week', 'power_score_norm'], ascending=[True, False]).to_dict(orient='records')
rank_data = json.dumps(rank_data, indent=2)
rank_data = {'rank_data': rank_data}

db_betting = Database(table='betting_table', season=season, week=week)
betting_table = db_betting.retrieve_data(how='week')
betting_table = betting_table.sort_values(['matchup_id', 'avg_score'])
betting_table['avg_score'] = betting_table.avg_score.round(1).apply(lambda x: f'{x:.2f}')
betting_table['p_win'] = betting_table.p_win.apply(lambda x: ws.calculate_odds(init_prob=x))
betting_table['p_tophalf'] = betting_table.p_tophalf.apply(lambda x: ws.calculate_odds(init_prob=x))
betting_table['p_highest'] = betting_table.p_highest.apply(lambda x: ws.calculate_odds(init_prob=x))
betting_table['p_lowest'] = betting_table.p_lowest.apply(lambda x: ws.calculate_odds(init_prob=x))

db_h2h = Database(table='h2h', season=season, week=week)
h2h_data = db_h2h.retrieve_data(how='season')
total_wins = get_total_wins(h2h_data=h2h_data, params=params, teams=teams, week=week)
wins_by_week = get_wins_by_week(h2h_data=h2h_data, total_wins=total_wins, teams=teams)
wins_vs_opp = get_wins_vs_opp(h2h_data=h2h_data, total_wins=total_wins, wins_by_week=wins_by_week, params=params, week=week)

db_ss = Database(table='switcher', season=season, week=week)
ss_data = db_ss.retrieve_data(how='season')
ss_disp = get_schedule_switcher_display(ss_data=ss_data, total_wins=total_wins, week=week)

eff_plot = plot_efficiency(database=Database,
                           season=season, week=week-1,
                           x='actual_lineup_score', y='optimal_lineup_score',
                           xlab='Difference From Optimal Points per Week',
                           ylab='Optimal Points per Week',
                           title='')

db = Database(table='records')
records_df = db.retrieve_data(how='all')

# champs = pd.read_csv("//home//hgupta//fantasy-football-league-report//champions.csv")
champs = pd.read_csv(r'C:\Dev\hgupta94\cool_league\champions.csv').sort_values('Season', ascending=False)
prev_champs = champs[['Season', 'Team', 'Runner Up']]

champ_count = (
    pd.concat(
        [
            champs.groupby('Team').size().rename('First'),
            champs.groupby('Runner Up').size().rename('Second')
        ], axis=1
    )
    .fillna(0)
    .sort_values('First', ascending=False)
)

champ_count['First'] = champ_count.First.apply(
    lambda n: ''.join(
        [
            f'<i class="fa fa-trophy icon-gold"></i>{"" if (i + 1) % 3 else "<span><br></span>"}' for i in range(int(n))
        ]
    ) + '<br>'
)
champ_count['Second'] = champ_count.Second.apply(
    lambda n: ''.join(
        [
            f'<i class="fa fa-trophy" style="color: #C0C0C0"></i>{"" if (i + 1) % 3 else "<span><br></span>"}' for i in range(int(n))
        ]
    ) + '<br>'
)
champ_count = champ_count.reset_index()
