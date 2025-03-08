import pandas as pd
import numpy as np
import datetime as dt

today = dt.datetime.today()
weekday = today.weekday()
hour = today.hour
folder = r'C:\\Users\\hirsh\\PycharmProjects\\pythonProject\\cool_league_site\\Tables\\'
file = 'betting_table.csv'

# load aggregate projections
league_id = 1382012
season = 2024
swid = '{E01C2393-2E6F-420B-9C23-932E6F720B61}'
espn = 'AEAVE3tAjA%2B4WQ04t%2FOYl15Ye5f640g8AHGEycf002gEwr1Q640iAvRF%2BRYFiNw5T8GSED%2FIG9HYOx7iwYegtyVzOeY%2BDhSYCOJrCGevkDgBrhG5EhXMnmiO2GpeTbrmtHmFZAsao0nYaxiKRvfYNEVuxrCHWYewD3tKFa923lw3NC8v5qjjtljN%2BkwFXSkj91k2wxBjrdaL5Pp1Y77%2FDzQza4%2BpyJq225y4AUPNB%2FCKOXYF7DTZ5B%2BbuHfyUKImvLaNJUTpwVXR74dk2VUMD9St'
d = load_data(league_id, season, swid, espn)

week_bet = np.where(get_params(d)['matchup_week'] > get_params(d)['regular_season_end'],
                    'Final ' + str(season),
                    'Week ' + str(get_params(d)['matchup_week']))
week_bet = week_bet.item(0)

params = get_params(d)
positions = params['positions']
matchup_week = params['matchup_week']
league_size = params['league_size']
team_map = params['team_map']
matchups = params['matchup_df'].reset_index(drop=True)
teams = params['teams']
slotcodes = params['slotcodes']
lineup_slots_df = params['lineup_slots_df']
pos_df = lineup_slots_df[(lineup_slots_df.posID != 20) & (lineup_slots_df.posID != 21)]
faab = params['faab_remaining']
faab['team'] = faab.team.str[:-1].str[:4]

if (hour % 8 != 0):
    # takes ~110s to run 1000 sims
    n_sim = 5
    curr_wk_sim = sim_week(d, positions, matchup_week, league_size, team_map, matchups, teams, slotcodes, pos_df, n_sim=n_sim)
    avg_score = curr_wk_sim[1].groupby('team').mean().reset_index()
    avg_score['score'] = np.round(avg_score.score, 1)

    # get betting table
    betting_table = pd.merge(curr_wk_sim[0], avg_score, on='team')
    betting_table[['n_wins', 'n_highest', 'n_lowest', 'n_tophalf']] = betting_table[['n_wins', 'n_highest', 'n_lowest', 'n_tophalf']] / n_sim

    # calculate betting lines
    betting_table['game_line'] = np.round(np.where(betting_table.n_wins > 0.5,
                 (100 * betting_table.n_wins) / (1 - betting_table.n_wins) * -1,
                 100 / (betting_table.n_wins) - 100))
    betting_table['game_line'] = np.where(~np.isfinite(betting_table.game_line), 0, betting_table.game_line)
    betting_table['game_line'] = np.where(betting_table.game_line > 10000, 10000, betting_table.game_line)
    betting_table['game_line'] = np.where(betting_table.game_line < -10000, -10000, betting_table.game_line)
    betting_table['game_line'] = betting_table.game_line.round(-1)

    betting_table['high_line'] = np.round(np.where(betting_table.n_highest > 0.5,
                 (100 * betting_table.n_highest) / (1 - betting_table.n_highest) * -1,
                 100 / (betting_table.n_highest) - 100))
    betting_table['high_line'] = np.where(~np.isfinite(betting_table.high_line), 0, betting_table.high_line)
    betting_table['high_line'] = np.where(betting_table.high_line > 10000, 10000, betting_table.high_line)
    betting_table['high_line'] = np.where(betting_table.high_line < -10000, -1000, betting_table.high_line)
    betting_table['high_line'] = betting_table.high_line.round(-1)

    betting_table['low_line'] = np.round(np.where(betting_table.n_lowest > 0.5,
                 (100 * betting_table.n_lowest) / (1 - betting_table.n_lowest) * -1,
                 100 / (betting_table.n_lowest) - 100))
    betting_table['low_line'] = np.where(~np.isfinite(betting_table.low_line), 0, betting_table.low_line)
    betting_table['low_line'] = np.where(betting_table.low_line > 10000, 10000, betting_table.low_line)
    betting_table['low_line'] = np.where(betting_table.low_line < -10000, -1000, betting_table.low_line)
    betting_table['low_line'] = betting_table.low_line.round(-1)

    betting_table['tophalf_line'] = np.round(np.where(betting_table.n_tophalf > 0.5,
                 (100 * betting_table.n_tophalf) / (1 - betting_table.n_tophalf) * -1,
                 100 / (betting_table.n_tophalf) - 100))
    betting_table['tophalf_line'] = np.where(~np.isfinite(betting_table.tophalf_line), 0, betting_table.tophalf_line)
    betting_table['tophalf_line'] = np.where(betting_table.tophalf_line > 10000, 10000, betting_table.tophalf_line)
    betting_table['tophalf_line'] = np.where(betting_table.tophalf_line < -10000, -1000, betting_table.tophalf_line)
    betting_table['tophalf_line'] = betting_table.tophalf_line.round(-1)

    betting_table.replace([np.inf, -np.inf], 0, inplace=True)

    betting_table = betting_table[['team', 'game_id', 'n_wins', 'game_line', 'score', 'high_line', 'low_line', 'tophalf_line']]
    betting_table = betting_table.sort_values(['game_id', 'n_wins'])
    betting_table['n_wins'] = pd.Series(['{0:.0f}%'.format(val * 100) for val in betting_table['n_wins']], index = betting_table.index)

    betting_table[['game_line', 'high_line', 'low_line', 'tophalf_line']] = betting_table[['game_line', 'high_line', 'low_line', 'tophalf_line']].astype(int).map(lambda x: '+'+str(x) if x>0 else x)

    betting_table = betting_table.drop('game_id', axis=1)
    betting_table['team'] = betting_table.team.str[:-1].str[:4]

    # add faab budgets
    betting_table = pd.merge(betting_table, faab, on='team', how='left')
    betting_table['faab_left'] = '$' + betting_table['faab_left'].astype(str)

    # reformat 0s
    betting_table.replace(0, '–', inplace=True)

    betting_table.columns = ['Team', 'Win%', 'Game Line', 'Avg Score', 'High Score', 'Low Score', 'Top Half', 'FAAB']

    betting_table.to_csv(folder + file, index=False)
else:
    betting_table = pd.read_csv(folder + file)
    # betting_table[['Game Line', 'High Score', 'Low Score', 'Top Half']] = betting_table[['Game Line', 'High Score', 'Low Score', 'Top Half']].astype(int).map(lambda x: '+'+str(x) if x>0 else x)

# for rendering to webpage
headings_bets = tuple(betting_table.columns)
data_bets = [tuple(x) for x in betting_table.to_numpy()]

tstamp = dt.datetime.now() - dt.timedelta(hours=4)
tstamp = 'Last Refresh: ' + str(tstamp.strftime('%A %B %d, %Y %I:%M %p'))
