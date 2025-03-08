import pandas as pd
import numpy as np
from scripts.utils import (utils as ut,
                           constants as const)


def get_standings(params, season, week):
    regular_season_end = params['regular_season_end']
    weeks_left = regular_season_end - week
    teams = params['teams']
    team_map = params['team_map']
    team_map = {a: b for a, b in team_map.items() if a in teams}
    matchups = params['matchup_df']
    n_playoff_teams = params['playoff_teams']

    flatten_first = {}
    flatten_display = {}
    for k, v in team_map.items():
        flatten_first[k] = v['name']['first']
        flatten_display[k] = v['name']['display']

    if season <= 2020:
        # 4 playoff teams, no top half win
        col_order = ['id', 'season', 'week', 'rank', 'team', 'record', 'win_perc', 'total_pf', 'wb4']

        if week == 0:
            final_standings = pd.DataFrame(list(team_map.keys())).rename(columns={0: 'team_id'})
            final_standings['team'] = final_standings.team_id.map(flatten_first)
            final_standings = final_standings.sort_values('team')
            final_standings['season'] = season
            final_standings['week'] = week
            final_standings['win_perc'] = '.000'
            final_standings['record'] = '0-0'
            final_standings['total_pf'] = '0'
            final_standings['wb4'] = '–'
            final_standings['rank'] = 1
            final_standings['id'] = final_standings.season.astype(str) \
                                    + '_' \
                                    + final_standings.week.astype(str).str.zfill(2) \
                                    + '_' \
                                    + final_standings.team_id.map(flatten_display)

            final_standings = final_standings[col_order]

            return final_standings

        else:
            # teams sorted by wins then points
            matchups = matchups[matchups.week <= week]
            matchups['team1_result'] = np.where(matchups['score1'] > matchups['score2'], 1.0, 0.0)
            matchups['team2_result'] = np.where(matchups['score2'] > matchups['score1'], 1.0, 0.0)
            mask = (matchups.score1 == matchups.score2)\
                   & (matchups.score1 > 0)\
                   & (matchups.score2 > 0)  # Account for ties
            matchups.loc[mask, ['team1_result', 'team2_result']] = 0.5

            # convert dataframe to long format so each row is a team week, not matchup
            home = matchups.iloc[:, [0, 1, 2, 5]].rename(columns={
                'team1_id': 'team_id',
                'score1': 'score',
                'team1_result': 'result'
            })
            away = matchups.iloc[:, [0, 3, 4, 6]].rename(columns={
                'team2_id': 'team_id',
                'score2': 'score',
                'team2_result': 'result'
            })

            standings = pd.concat([home, away]).sort_values(['week', 'team_id']).reset_index(drop=True)
            standings['team'] = standings.team_id.map(flatten_first)
            standings['season'] = season
            standings['wins'] = standings.groupby('team').result.cumsum()
            standings['total_pf'] = standings.groupby('team').score.cumsum()
            standings['ppg'] = standings.total_pf / standings.week

            standings = standings[standings.week == standings.week.max()]
            standings['total_pf'] = standings.total_pf.round(2)
            standings['m_losses'] = np.where(week > regular_season_end,
                                             regular_season_end - standings['wins'],
                                             standings['week'] - standings['wins'])
            standings['record'] = standings.wins.astype(int).astype(str) + '-' + standings.m_losses.astype(int).astype(str)
            standings['win_perc'] = round(standings['wins'] / (standings['wins'] + standings['m_losses']), 3)
            standings['win_perc'] = standings.win_perc.map('{:.3f}'.format)

            # Clinching Scenarios #
            # for clinch scenarios, need to order by wins then points
            clinch_standings = standings.sort_values(['wins', 'total_pf'], ascending=False)

            # calculate games back: 4th seed
            fourth_seed_wins = clinch_standings.iloc[3, :].wins
            clinch_standings['wb4'] = fourth_seed_wins - clinch_standings.wins
            clinch_standings['wb4'] = clinch_standings['wb4'].astype(int)

            # Calculate clinches and eliminations
            # 1. Team clinched first round bye (top 2 seed)
            four_seed_wins = clinch_standings.iloc[n_playoff_teams-1, 6]
            four_seed_pts = clinch_standings.iloc[n_playoff_teams-1, 7]
            five_seed_wins = clinch_standings.iloc[n_playoff_teams, 6]
            five_seed_pts = clinch_standings.iloc[n_playoff_teams, 7]

            cl_po = []
            for idx, row in clinch_standings.iterrows():
                if (row['wins'] - five_seed_wins) < weeks_left:
                    # if difference in wins is less than weeks remaining, team does not clinch top 4 seed
                    cl_po.append(0)
                elif (weeks_left < 1) & (row['wins'] == five_seed_wins):
                    #  if season is over AND team is tied in wins, move to points
                    if row['total_pf'] > five_seed_pts:
                        # if team is tied with four seed in wins AND has more points than three seed, clinch bye
                        cl_po.append(1)
                    else:
                        # if team is tied in wins and DOES NOT have more points, does not clinch
                        cl_po.append(0)
                elif (row['wins'] - five_seed_wins) == weeks_left:
                    # if team is ahead by same number of weeks remaining, no clinch
                    cl_po.append(0)
                else:
                    cl_po.append(1)

            # 3. teams eliminated from playoffs
            elim_po = []
            for idx, row in clinch_standings.iterrows():
                if (four_seed_wins - row['wins']) > weeks_left:
                    # if difference in wins is greater than weeks remaining, team is eliminated
                    elim_po.append(1)
                elif (weeks_left < 1) & (row['wins'] == four_seed_wins):
                    # if season is over AND team is tied in wins, move to points
                    if row.total_pf < four_seed_pts:
                        elim_po.append(1)
                    else:
                        elim_po.append(0)
                else:
                    elim_po.append(0)

            final_standings = clinch_standings.assign(cl_po=cl_po, elim_po=elim_po)

            # Format weeks behind and points for
            final_standings.iloc[:, -3] = np.where(final_standings.iloc[:, -3] < 0,
                                                      '+' + final_standings.iloc[:, -3].mul(-1.0).astype(str),
                                                      final_standings.iloc[:, -3].mul(1.0).astype(str))
            final_standings.iloc[:, -3] = np.where(
                (final_standings.iloc[:, -3] == '0') | (final_standings.iloc[:, -3] == '0.0'),
                '–',
                final_standings.iloc[:, -3])
            final_standings['total_pf'] = final_standings.total_pf.astype(float).map('{:,.2f}'.format)

            # Add clinches/eliminations
            final_standings['wb4'] = np.where(final_standings.cl_po == 1, 'c', final_standings.wb4)
            final_standings['wb4'] = np.where(final_standings.elim_po == 1, 'x', final_standings.wb4)
            final_standings['rank'] = np.arange(final_standings.shape[0]) + 1
            final_standings['id'] = final_standings.season.astype(str)\
                                    + '_'\
                                    + final_standings.week.astype(str).str.zfill(2)\
                                    + '_'\
                                    + final_standings.team_id.map(flatten_display)
            final_standings = final_standings.sort_values('rank')
            final_standings = final_standings[col_order]

            return final_standings

    if season >= 2021:
        col_order = ['id', 'season', 'week', 'rank', 'team', 'ov_record', 'win_perc',
                     'm_record', 'thw_record', 'total_pf', 'wb2', 'wb5', 'pb6']

        if week == 0:
            final_standings = pd.DataFrame(list(team_map.keys())).rename(columns={0: 'team_id'})
            final_standings['team'] = final_standings.team_id.map(flatten_first)
            final_standings = final_standings.sort_values('team')
            final_standings['season'] = season
            final_standings['week'] = week
            final_standings['ov_record'] = '0-0'
            final_standings['win_perc'] = '.000%'
            final_standings['m_record'] = '0-0'
            final_standings['thw_record'] = '0-0'
            final_standings['total_pf'] = '0'
            final_standings['wb2'] = '–'
            final_standings['wb5'] = '–'
            final_standings['pb6'] = '–'
            final_standings['rank'] = 1
            final_standings['id'] = final_standings.season.astype(str) \
                                    + '_' \
                                    + final_standings.week.astype(str).str.zfill(2) \
                                    + '_' \
                                    + final_standings.team_id.map(flatten_display)
            final_standings = final_standings[col_order]

            return final_standings

        else:
            # standings order:
            #   - all teams sorted by wins then points

            matchups = matchups[matchups.week <= week]
            matchups['team1_result'] = np.where(matchups['score1'] > matchups['score2'], 1.0, 0.0)
            matchups['team2_result'] = np.where(matchups['score2'] > matchups['score1'], 1.0, 0.0)
            mask = (matchups.score1 == matchups.score2) \
                   & (matchups.score1 > 0) \
                   & (matchups.score2 > 0)  # Account for ties
            matchups.loc[mask, ['team1_result', 'team2_result']] = 0.5

            # convert dataframe to long format so each row is a team week, not matchup
            home = matchups.iloc[:, [0, 1, 2, 5]].rename(columns={
                'team1_id': 'team_id',
                'score1': 'score',
                'team1_result': 'result'
            })
            away = matchups.iloc[:, [0, 3, 4, 6]].rename(columns={
                'team2_id': 'team_id',
                'score2': 'score',
                'team2_result': 'result'
            })

            standings = pd.concat([home, away]).sort_values(['week', 'team_id']).reset_index(drop=True)
            standings['team'] = standings.team_id.map(flatten_first)
            standings['season'] = season
            standings['wins'] = standings.groupby('team').result.cumsum()
            standings['total_pf'] = standings.groupby('team').score.cumsum()
            standings['ppg'] = standings.total_pf / standings.week

            medians = {}
            for w in standings.week.unique().tolist():
                s = standings[standings.week == w]
                medians[w] = round(s.score.median(), 2)

            vals = []
            for idx, row in standings.iterrows():
                the_median = medians[row.week]
                vals.append(1 if row.score > the_median else 0)

            standings['thw_res'] = vals
            standings['thw_tot'] = standings.groupby(['team']).thw_res.cumsum()

            standings = standings[standings.week == standings.week.max()]
            standings['total_pf'] = standings.total_pf.round(2)
            standings['m_losses'] = np.where(week > regular_season_end,
                                             regular_season_end - standings['wins'],
                                             standings['week'] - standings['wins'])

            standings['thw_losses'] = np.where(week > regular_season_end,
                                               regular_season_end - standings['thw_tot'],
                                               standings['week'] - standings['thw_tot'])
            standings['m_record'] = standings.wins.astype(int).astype(str) + '-' + standings.m_losses.astype(
                int).astype(str)
            standings['thw_record'] = standings.thw_tot.astype(int).astype(str) + '-' + standings.thw_losses.astype(
                int).astype(str)
            standings['ov_wins'] = standings.wins + standings.thw_tot
            standings['ov_losses'] = standings.m_losses + standings.thw_losses
            standings['ov_record'] = standings.ov_wins.astype(int).astype(str) + '-' + standings.ov_losses.astype(
                int).astype(str)
            standings['win_perc'] = round(standings['ov_wins'] / (standings['ov_wins'] + standings['ov_losses']), 3)
            standings['win_perc'] = standings.win_perc.map('{:.3f}'.format)

            top_five = standings \
                .sort_values(['ov_wins', 'total_pf'], ascending=False) \
                .head(5)
            top_five_list = top_five.team.tolist()

            # get 6th place by points and append to top 5
            sixth = standings[~standings.team.isin(top_five_list)] \
                .sort_values('total_pf', ascending=False) \
                .head(1)
            final_standings = pd.concat([top_five, sixth])
            playoff_list = final_standings.team.tolist()

            # get bottom 4 by wins
            bottom_four = standings[~standings.team.isin(playoff_list)].sort_values(['ov_wins', 'total_pf'],
                                                                                    ascending=False)
            final_standings = pd.concat([final_standings, bottom_four])

            # calculate games back: bye, fifth seed; points back of 6th seed
            last_bye_wins = final_standings.iloc[1, :].ov_wins
            final_standings['wb2'] = last_bye_wins - final_standings.ov_wins
            final_standings['wb2'] = final_standings['wb2'].astype(int) / 2

            fifth_seed_wins = final_standings.iloc[4, :].ov_wins
            final_standings['wb5'] = fifth_seed_wins - final_standings.ov_wins
            final_standings['wb5'] = final_standings['wb5'].astype(int) / 2

            sixth_seed_pf = final_standings.iloc[5, :].total_pf
            final_standings['pb6'] = round(sixth_seed_pf - final_standings.total_pf, 2)
            final_standings['rank'] = np.arange(final_standings.shape[0]) + 1

            # Clinching Scenarios #
            # for clinch scenarios, need to order by wins then points
            clinch_standings = final_standings.sort_values(['ov_wins', 'total_pf'], ascending=False)

            # Calculate clinches and eliminations
            # 1. Team clinched first round bye (top 2 seed)
            two_seed_wins = clinch_standings.iloc[1, 15]
            two_seed_pts = clinch_standings.iloc[1, 7]
            three_seed_wins = clinch_standings.iloc[2, 15]
            three_seed_pts = clinch_standings.iloc[2, 7]
            five_seed_wins = clinch_standings.iloc[4, 15]
            five_seed_pts = clinch_standings.iloc[4, 7]
            six_seed_wins = clinch_standings.iloc[5, 15]
            six_seed_pts = clinch_standings.iloc[5, 7]

            cl_bye = []
            for idx, row in clinch_standings.iterrows():
                if (row['ov_wins'] - three_seed_wins) / 2 < weeks_left:
                    # if difference in wins is less than weeks remaining, team does not clinch bye
                    cl_bye.append(0)
                elif (weeks_left < 1) & (row['ov_wins'] == three_seed_wins):
                    #  if season is over AND team is tied in wins, move to points
                    if row['total_pf'] > three_seed_pts:
                        # if team is tied with three seed in wins AND has more points than three seed, clinch bye
                        cl_bye.append(1)
                    else:
                        # if team is tied in wins and DOES NOT have more points, does not clinch
                        cl_bye.append(0)
                elif (row['ov_wins'] - three_seed_wins) / 2 == weeks_left:
                    # if team is ahead by same number of weeks remaining, no clinch
                    cl_bye.append(0)
                else:
                    cl_bye.append(1)

            # 2. Team clinched top 5 seed
            cl_po = []
            for idx, row in clinch_standings.iterrows():
                if (row['ov_wins'] - six_seed_wins) / 2 < weeks_left:
                    # if difference in wins is less than weeks remaining, team does not clinch top 5 seed
                    cl_po.append(0)
                elif (weeks_left < 1) & (row['ov_wins'] == six_seed_wins):
                    #  if season is over AND team is tied in wins, move to points
                    if row['total_pf'] > six_seed_pts:
                        # if team is tied with six seed in wins AND has more points than three seed, clinch bye
                        cl_po.append(1)
                    else:
                        # if team is tied in wins and DOES NOT have more points, does
                        cl_po.append(0)
                elif (row['ov_wins'] - six_seed_wins) / 2 == weeks_left:
                    # if team is ahead by same number of weeks remaining, no clinch
                    cl_po.append(0)
                else:
                    cl_po.append(1)

            # 3. teams eliminated from bye week (top 2 seed)
            elim_bye = []
            for idx, row in clinch_standings.iterrows():
                if (two_seed_wins - row['ov_wins']) / 2 > weeks_left:
                    # if difference in wins is greater than weeks remaining, team is eliminated
                    elim_bye.append(1)
                elif (weeks_left < 1) & (row['wins'] == two_seed_pts):
                    # if season is over AND team is tied in wins, move to points
                    if row.total_pf < two_seed_pts:
                        elim_bye.append(1)
                    else:
                        elim_bye.append(0)
                else:
                    elim_bye.append(0)

            # Calculate wins clinches (five seed or better)
            elim_po = []
            for idx, row in clinch_standings.iterrows():
                if (five_seed_wins - row['ov_wins']) / 2 > weeks_left:
                    # if difference in wins is less than weeks remaining, team does not clinch bye
                    elim_po.append(1)
                elif (weeks_left < 1) & (row['wins'] == five_seed_pts):
                    # if season is over AND team is tied in wins, move to points
                    if row.total_pf < five_seed_pts:
                        elim_bye.append(1)
                    else:
                        elim_bye.append(0)
                else:
                    elim_po.append(0)

            final_standings = clinch_standings.assign(cl_bye=cl_bye, elim_bye=elim_bye, cl_po=cl_po, elim_po=elim_po)

            # Format weeks/points behind values standings
            final_standings.iloc[:, -8:-5] = np.where(final_standings.iloc[:, -8:-5] < 0,
                                                      '+' + final_standings.iloc[:, -8:-5].mul(-1).astype(str),
                                                      final_standings.iloc[:, -8:-5].astype(str))

            final_standings.iloc[:, -8:-5] = np.where(
                (final_standings.iloc[:, -8:-5] == '0') | (final_standings.iloc[:, -8:-5] == '0.0'),
                '–',
                final_standings.iloc[:, -8:-5])

            final_standings['total_pf'] = final_standings.total_pf.astype(float).map('{:,.2f}'.format)

            # Add clinches/eliminations
            final_standings['wb2'] = np.where(final_standings.cl_bye == 1, 'c', final_standings.wb2)
            final_standings['wb2'] = np.where(final_standings.elim_bye == 1, 'x', final_standings.wb2)
            final_standings['wb5'] = np.where(final_standings.cl_po == 1, 'c', final_standings.wb5)
            final_standings['wb5'] = np.where(final_standings.elim_po == 1, 'x', final_standings.wb5)
            final_standings = final_standings.sort_values('rank')
            final_standings['id'] = final_standings.season.astype(str) + '_' + final_standings.week.astype(
                str).str.zfill(2) + '_' + final_standings.team_id.map(flatten_display)

            final_standings = final_standings[col_order]

            return final_standings


def query_standings(season, week):
    with ut.mysql_connection() as conn:
        query = f'''
        SELECT *
        FROM standings
        WHERE season={season} AND week={week}
        '''
        standings = pd.read_sql(query, con=conn).sort_values('rank')

    cols_2018_2020 = ['team', 'm_record', 'win_perc', 'total_pf', 'wb4']
    cols_2021_curr = ['team', 'ov_record', 'win_perc', 'm_record', 'thw_record', 'total_pf', 'wb2', 'wb5', 'pb6']
    cols_filter = cols_2018_2020 if season <= 2020 else cols_2021_curr
    cols_rename = const.STANDINGS_COL_MAP_2018_2020 if season <= 2020 else const.STANDINGS_COL_MAP_2021_CURR
    standings_final = standings[cols_filter].rename(columns=cols_rename)

    headings = tuple(standings_final.columns)
    data_st = [tuple(x) for x in standings_final.to_numpy()]

    return headings, data_st
