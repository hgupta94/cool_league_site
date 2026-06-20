import json

import pandas as pd

from scripts.api.dataloader import DataLoader
from scripts.utils.database import Database
from scripts.api.settings import LeagueSettings, TeamSettings
from scripts.home.standings import Standings
from scripts.utils import constants
from scripts.utils.utils import calculate_odds
import scripts.scenarios.scenarios as scenarios
from scripts.efficiency.xxefficiencies import plot_efficiency


dataloader = DataLoader(week=constants.WEEK)
params = LeagueSettings(dataloader=dataloader)
teams = TeamSettings(dataloader=dataloader)
week = params.regular_season_end+1 if params.current_week > params.regular_season_end+1 else params.current_week
n_teams = len(teams.team_ids)

# load db tables
day = constants._TODAY.strftime('%a')
the_week = params.as_of_week if day == 'Tue' else params.current_week  # Wed is start of new week, and season_sim runs on Tue
db = Database()
query = f'select t.team_id team, m.display_name from team_ids t left join managers m on t.manager_id=m.manager_id where season={constants.SEASON};'
id_mapping = db.query(query=query)
id_map = {row.team: row.display_name for row in id_mapping.itertuples()}
alltime_df = db.retrieve_data(how='all', table='alltime_standings')
records_df = db.retrieve_data(how='all', table='records')


# HOME PAGE
standings = Standings(dataloader=dataloader, season=params.season, week=week)
standings_final = standings.format_standings()
# standings.final_week_playoff_scenarios(standings_final, seed=2)
standings_to_flask = []
for t in standings_final:
    standings_to_flask.append((
        t['seed'], id_map[t['team_id']], t['record'], t['win_pct'], t['matchup'], t['tophalf'],
        t['points_disp'], t['wb2'], t['wb5'], t['pb6'], t['bye_magic_disp'], t['po_magic_disp']
    ))
clinches = {'clinches': [], 'eliminations': []}
if week > 1:
    clinches = standings.get_playoff_scenarios(id_map=id_map)
    # TODO: fix last week clinches/elims. for wild card, net wins and probability should be blank (or save all sims to get prob of team getting outscored by x pts)


pr_data = Database().retrieve_data(how='season', table='power_ranks', season=params.season, week=week-1)
pr_data['team'] = pr_data.team.map(id_map)
pr_data[['power_score_norm', 'score_norm_change']] = pr_data[['power_score_norm', 'score_norm_change']] * 100
pr_table = pr_data[pr_data.week == week-1]
pr_table = pr_table.sort_values('power_score_raw', ascending=False)
pr_table[['power_score_norm', 'score_norm_change']] = round(pr_table[['power_score_norm', 'score_norm_change']]).astype('Int32')
pr_table['rank_change'] = -pr_table.rank_change
pr_table[['total_points', 'weekly_points', 'consistency', 'manager', 'luck']] = pr_table[['season_idx', 'week_idx', 'consistency_idx', 'manager_idx', 'luck_idx']].rank(ascending=False, method='min').astype('Int32')
pr_cols = ['team', 'total_points', 'weekly_points', 'consistency', 'manager', 'luck', 'power_rank', 'rank_change', 'power_score_norm', 'score_norm_change']
rank_data = (
    pr_data[['team', 'week', 'power_rank']]
    .sort_values(['week', 'power_rank'], ascending=[True, False])
    .rename(columns={'power_rank': 'y'})
    .to_dict(orient='records')
)
rank_data = json.dumps(rank_data, indent=2)
rank_data = {'rank_data': rank_data}
score_data = (
    pr_data[['team', 'week', 'power_score_norm']]
    .sort_values(['week', 'power_score_norm'], ascending=[True, False])
    .rename(columns={'power_score_norm': 'y'})
    .to_dict(orient='records')
)
score_data = json.dumps(score_data, indent=2)
score_data = {'score_data': score_data}


# SIMULATIONS PAGE
betting_table = (
    db
    .retrieve_data(how='season', table='betting_table', season=params.season, week=params.current_week)  # show previous week on Tues
    .sort_values('created')
    .tail(n_teams)  # most recent db updates
)
betting_table['team'] = betting_table.team.map(id_map)
timestamp_betting = pd.to_datetime(betting_table.created.values[0]).strftime("%A, %b %d %Y")
betting_table = betting_table.sort_values(['matchup_id', 'avg_score'])
betting_table['avg_score'] = betting_table.avg_score.round(2).apply(lambda x: f'{x:.2f}')
betting_table['p_win'] = betting_table.p_win.apply(lambda x: calculate_odds(init_prob=x))
betting_table['p_tophalf'] = betting_table.p_tophalf.apply(lambda x: calculate_odds(init_prob=x))
betting_table['p_highest'] = betting_table.p_highest.apply(lambda x: calculate_odds(init_prob=x))
betting_table['p_lowest'] = betting_table.p_lowest.apply(lambda x: calculate_odds(init_prob=x))

season_sim_table_full = (
    db
    .retrieve_data(how='season', table='season_sim', season=params.season, week=week)
    .sort_values('created')
)
season_sim_table_full['team'] = season_sim_table_full.team.map(id_map)
season_sim_table_full['xpo'] = (
        season_sim_table_full.top_scores * constants.PAYOUTS['weekly_top_score']
        + season_sim_table_full.champion * constants.PAYOUTS['first']
        + (season_sim_table_full.finals - season_sim_table_full.champion) * constants.PAYOUTS['second']
        + season_sim_table_full.third * constants.PAYOUTS['third']
        + season_sim_table_full.most_wins * constants.PAYOUTS['most_wins']
        + season_sim_table_full.most_points * constants.PAYOUTS['most_points']
)
playoff_chart_data = season_sim_table_full.drop(['id', 'season', 'created'], axis=1).to_dict(orient='records')
playoff_chart_data = json.dumps(playoff_chart_data, indent=2)
playoff_chart_data = {'probs': playoff_chart_data}

season_sim_table = season_sim_table_full.tail(n_teams)  # most recent db updates
timestamp_season_sim = pd.to_datetime(season_sim_table.created.values[0]).strftime("%A, %b %d %Y")
keep_cols = ['team', 'matchup_wins', 'tophalf_wins', 'total_wins', 'total_points', 'playoffs', 'finals', 'champion', 'xpo']
season_sim_table[['playoffs', 'finals', 'champion']] = (season_sim_table[['playoffs', 'finals', 'champion']]*100).round(1).astype(str) + '%'
season_sim_table[['matchup_wins', 'tophalf_wins', 'total_wins']] = season_sim_table[['matchup_wins', 'tophalf_wins', 'total_wins']].round(1)
season_sim_table['total_points'] = season_sim_table.total_points.apply(lambda x: f'{x:,.2f}')
season_sim_table['xpo'] = season_sim_table.xpo.apply(lambda x: f'${x:,.2f}')
teams_order = season_sim_table.sort_values(['total_wins', 'total_points'], ascending=False).iloc[:5, 3].to_list()
teams_order.extend(season_sim_table[~season_sim_table.team.isin(teams_order)].sort_values('total_points', ascending=False).iloc[:1, 3].to_list())
teams_order.extend(season_sim_table[~season_sim_table.team.isin(teams_order)].sort_values(['total_wins', 'total_points'], ascending=False).iloc[:4, 3].to_list())
season_sim_table = season_sim_table.set_index('team')
season_sim_table = season_sim_table.reindex(teams_order).reset_index()[keep_cols]

season_sim_wins_table = db.retrieve_data(how='week', table='season_sim_wins', season=params.season, week=the_week)
season_sim_wins_table['team'] = season_sim_wins_table.team.map(id_map)
order = season_sim_table.team.tolist()
season_sim_wins_table = season_sim_wins_table[['team', 'wins', 'p']].pivot(index='team', columns='wins', values='p').fillna('')
# ensure every integer win column exists from min to max
win_min = int(season_sim_wins_table.columns.min())
win_max = int(season_sim_wins_table.columns.max())
all_wins = list(range(win_min, win_max + 1))
season_sim_wins_table = season_sim_wins_table.reindex(columns=all_wins).fillna('')
season_sim_wins_table = season_sim_wins_table.reindex(order).reset_index().rename(columns={'team': 'Team'})

season_sim_ranks_table = db.retrieve_data(how='week', table='season_sim_ranks', season=params.season, week=the_week)
season_sim_ranks_table['team'] = season_sim_ranks_table.team.map(id_map)
season_sim_ranks_table = season_sim_ranks_table[['team', 'ranks', 'p']].pivot(index='team', columns='ranks', values='p').fillna('')
season_sim_ranks_table = season_sim_ranks_table.reindex(order).reset_index().rename(columns={'team': 'Team'})


# SCENARIOS PAGE
h2h_data = db.retrieve_data(how='season', table='h2h', season=params.season, week=params.as_of_week)
h2h_data = h2h_data[h2h_data.week <= params.regular_season_end]
total_wins = scenarios.get_total_wins(h2h_data=h2h_data, teams=teams, week=week-1)
if week > 1:
    wins_by_week = scenarios.get_wins_by_week(h2h_data=h2h_data, total_wins=total_wins, params=params, teams=teams)
    wins_vs_opp = scenarios.get_wins_vs_opp(h2h_data=h2h_data, total_wins=total_wins, wins_by_week=wins_by_week, week=week-1)
    wins_by_week['team'] = wins_by_week.team.map(id_map)
    wins_vs_opp['team'] = wins_vs_opp.team.map(id_map)
    wins_vs_opp = wins_vs_opp.rename(columns=id_map)

ss_data = db.retrieve_data(how='season', table='schedule_switcher', season=params.season, week=week)
ss_disp_temp = scenarios.get_schedule_switcher_display(ss_data=ss_data, total_wins=total_wins, week=week)
ss_disp_temp = ss_disp_temp.rename(columns=id_map)
ss_luck = pd.DataFrame.from_dict(scenarios.calculate_schedule_luck(ss_data), orient='index').reset_index().rename(columns={'index':'team', 0:'Luck'})
ss_disp = pd.merge(ss_disp_temp, ss_luck, on='team')
ss_disp['team'] = ss_disp.team.map(id_map)

h2h_data['team'] = h2h_data.team.map(id_map)
total_wins['team'] = total_wins.team.map(id_map)


# TEAM EFFICIENCY PAGE
eff = Database().retrieve_data(how='season', table='efficiency', season=params.season, week=week-1)
eff['team'] = eff.team.map(id_map)
cols = eff.select_dtypes(include=['float']).columns.tolist()
eff_df = eff.groupby('team')[cols].sum() / eff.week.max()
eff_df['efficiency'] = eff_df['actual_lineup_score'] / eff_df['optimal_lineup_score']
eff_df['difference_from_optimal'] = eff_df.actual_lineup_score - eff_df.optimal_lineup_score
eff_df['act_bestproj_perc'] = eff_df.actual_lineup_score / eff_df.best_projected_lineup_score
eff_chart_data = eff_df[['optimal_lineup_score', 'difference_from_optimal', 'efficiency']].reset_index().to_dict(orient='records')
eff_chart_data = json.dumps(eff_chart_data, indent=2)
eff_chart_data = {'efficiencies': eff_chart_data}

# HISTORY/CHAMPIONS PAGE
champs = pd.read_csv(r'champions.csv').sort_values('Season', ascending=False)
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
champ_count = champ_count.reset_index().rename(columns={'index': 'Team'})
