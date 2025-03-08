import pandas as pd
import numpy as np
import random
from functools import reduce

from scripts.utils.constants import SLOTCODES


def get_week_projections(params):
    """Return current week's projections for all positions"""
    positions = ['qb', 'rb', 'wr', 'te', 'dst']

    projections = pd.DataFrame()
    for pos in positions:
        url = f"https://www.fantasypros.com/nfl/projections/{pos}.php?scoring=HALF&week={params['matchup_week']}"
        df = pd.read_html(url)[0]

        # drop multi index column
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel()

        df['POSITION'] = pos
        df = df[['Player', 'FPTS', 'POSITION']]

        # remove team from player name
        if pos != 'dst':
            df['TEAM'] = df.Player.str[-3:].str.strip()
            df['Player'] = df['Player'].str[:-3]
            df['Player'] = df['Player'].str.rstrip()

        if pos == 'dst':
            df['Player'] = df['Player'].str.split().str[-1] + ' DST'

        projections = pd.concat([projections, df])

    return projections


def sim_week(d, params, projections, n_sim=10):
    """Simulates current week matchups using aggregate projections from FantasyPros"""
    # add 1.5 points for dst to account for stuffs
    # projections.loc[(projections[:, 3]=="dst")] = projections[projections.position == "dst"]["fpts"] + 1.5
    # projections = matches.copy()
    projections = projections[projections.FPTS > 0]
    projections.columns = projections.columns.str.lower()

    # load parameters
    week = params['matchup_week']
    lineup_slots_df = params['lineup_slots_df']
    pos_df = lineup_slots_df[(lineup_slots_df.posID != 20) & (lineup_slots_df.posID != 21)]
    df = params['matchup_df'].reset_index(drop=True)
    posns = pos_df.pos.str.lower().to_list()
    struc = pos_df.limit.to_list()

    # get actual player scores from espn
    # code thanks to Steven Morse: https://stmorse.github.io/journal/espn-fantasy-projections.html
    data = []
    for tm in d['teams']:
        tmid = tm['id']
        for p in tm['roster']['entries']:
            player_id = p['playerPoolEntry']['player']['id']
            name = p['playerPoolEntry']['player']['fullName']
            slot_id = p['lineupSlotId']
            slot = SLOTCODES[slot_id]

            # injured status (try/except bc dst cannot be injured)
            inj = 'NA'
            try:
                inj = p['playerPoolEntry']['player']['injuryStatus']
            except:
                pass

            # projected/actual points
            proj, act = None, None
            for stat in p['playerPoolEntry']['player']['stats']:
                if stat['scoringPeriodId'] != week:
                    continue
                if stat['statSourceId'] == 0:
                    act = stat['appliedTotal']

            data.append(
                [week, tmid, player_id, name, slot_id, slot, inj, act]
            )

    proj = pd.DataFrame(data,
                        columns=['week', 'team', 'player_id', 'player',
                                 'slot_id', 'slot', 'status', 'actual'])
    proj = proj.apply(lambda x: x.astype(str).str.lower() if x.dtype == 'object' else x)
    proj = proj.replace({"team": params['team_map']})
    proj = proj[(proj['slot'] != 'ir')]
    proj['actual'] = np.where(proj['actual'] == 'none', np.nan, proj['actual'])

    proj = pd.merge(proj,
                    projections[['player_id', 'position', 'fpts']],
                    how='left',
                    on='player_id')\
        .rename(columns={'fpts': 'projected'})
    proj['projected'] = np.where(proj['projected'].isnull(), 0, proj['projected'])

    # add standard deviations (same as get_ros_projections)
    proj['sd'] = np.where(proj['position'] == 'QB', proj['projected'] * 0.2, proj['projected'] * 0.4)

    # get current week matchups
    matchups = df[['week', 'team1', 'score1', 'team2', 'score2']]
    matchups = matchups[matchups['week'] == params['matchup_week']]
    matchups['team1'] = matchups.team1
    matchups['team2'] = matchups.team2
    matchups['game_id'] = range(1, int(params['league_size'] / 2) + 1)
    matchups = matchups.reset_index(drop=True)

    # initialize dicionaries for counts
    teams = list(params['team_map'].values())
    teams_dict = {key: 0 for key in teams}
    n_wins = {key: 0 for key in teams}
    n_highest = {key: 0 for key in teams}
    n_lowest = {key: 0 for key in teams}
    n_tophalf = {key: 0 for key in teams}

    # simulate current week scores
    projections["sd"] = np.where(projections['fpts'] == 'qb', projections['fpts'] * 0.2, projections['fpts'] * 0.4)
    ref = projections[["position", "fpts", "sd"]].groupby("position").quantile(0.75).reset_index()
    score_df = pd.DataFrame()
    for sim in range(1, n_sim + 1):
        print(sim)
        # get starting lineeup of highest projected player by position
        # for each team, select top: 1QB, 2RB, 3WR, 1TE, 1FLEX, 1DST
        for_sim = pd.DataFrame()
        for tm in teams:
            for pos, num in zip(posns, struc):
                if pos != "flex":
                    starter = proj.query('team == @tm & slot == @pos & ~actual.isnull()')
                    for_sim = pd.concat([for_sim, starter])
                    if len(starter) < num:
                        selection = proj \
                            .query('team == @tm & position == @pos & actual.isnull()') \
                            .sort_values(by='projected', ascending=False) \
                            .head(num - len(starter))
                        selection['proj_slot'] = pos
                        for_sim = pd.concat([for_sim, selection])
                        if len(selection) < num - len(starter):
                            # use 75th percentile player if position is not filled
                            num_left = num - len(selection)
                            ref_proj = ref \
                                .loc[ref.query('position == @pos').index.repeat(num_left)] \
                                .rename(columns={'fpts': 'projected'})
                            ref_proj["team"] = tm
                            ref_proj['proj_slot'] = pos
                            for_sim = pd.concat([for_sim, ref_proj])

                    pl_list = for_sim.player.tolist()

                if pos == "flex":
                    fl_starter = proj.query('team == @tm & slot == @pos & ~actual.isnull()')
                    if len(fl_starter) < num:
                        # select flex: 3rd RB/WR or 2nd TE
                        fpos = ["rb", "wr"]
                        fnum = [2, 3]
                        flex = pd.DataFrame()
                        for a, b in zip(fpos, fnum):
                            selection = proj \
                                .query('team == @ tm & position == @a & actual.isnull()') \
                                .sort_values(by='projected', ascending=False)
                            selection = selection[~selection.player.isin(pl_list)]
                            selection = selection.groupby("position").head(1)
                            flex = pd.concat([flex, selection])
                        # select flex player
                        flex = flex.sort_values(by='projected', ascending=False).head(1)
                        flex['proj_slot'] = pos
                        for_sim = pd.concat([for_sim, flex])
                    else:
                        for_sim = pd.concat([for_sim, fl_starter])
        for_sim = for_sim.reset_index(drop=True)

        # if player hasn't played, simulate score otherwise use actual scores
        for_sim['score'] = np.nan
        for index, row in for_sim.iterrows():
            try:
                if pd.isnull(row.actual):
                    for_sim.at[index, 'score'] = ((random.gauss(for_sim['projected'][index], for_sim['sd'][index]))
                                                  + (random.uniform(-1, 2))) * 0.95
                else:
                    for_sim.at[index, 'score'] = for_sim['actual'][index]
            except:
                pass

        for team in teams:
            teams_dict[team] = for_sim[for_sim['team'] == team].score.sum()
            score_df = pd.concat([score_df, for_sim[for_sim['team'] == team].groupby('team').score.sum().reset_index()])

        a = matchups.filter(like='team').columns
        matchups['score' + a.str.lstrip('team')] = matchups[a].stack().map(teams_dict).unstack()

        # calculate wins and losses
        matchups['team1_result'] = np.where(matchups['score1'] > matchups['score2'], 1.0, 0.0)
        matchups['team2_result'] = np.where(matchups['score2'] > matchups['score1'], 1.0, 0.0)

        # account for ties
        mask = (matchups.score1 == matchups.score2)
        matchups.loc[mask, ['team1_result', 'team2_result']] = 0.5

        # convert dataframe to long format so each row is a team week, not matchup
        home = matchups.iloc[:, [0, 1, 2, 5, 6]] \
            .rename(columns={'team1': 'team',
                             'score1': 'score',
                             'team1_result': 'wins'})
        away = matchups.iloc[:, [0, 3, 4, 5, 7]] \
            .rename(columns={'team2': 'team',
                             'score2': 'score',
                             'team2_result': 'wins'})
        df_sim = pd.concat([home, away]).iloc[:, [1, 2, 3, 4]]

        for team in teams:
            n_wins[team] += df_sim[df_sim['team'] == team].wins.values[0].astype(int)

        # get highest/lowest scorer and teams in top half (need to add this)
        high = df_sim.sort_values(by='score', ascending=False).iloc[0, 0]
        low = df_sim.sort_values(by='score').iloc[0, 0]
        tophalf = df_sim.sort_values(by='score', ascending=False).iloc[:5, 0].tolist()
        n_highest[high] += 1
        n_lowest[low] += 1
        for team in tophalf:
            n_tophalf[team] += 1

    # convert dicts to df and combine
    game_id = df_sim.loc[:, ['team', 'game_id']]
    wins = pd.DataFrame(n_wins.items(), columns=['team', 'n_wins'])
    highest = pd.DataFrame(n_highest.items(), columns=['team', 'n_highest'])
    lowest = pd.DataFrame(n_lowest.items(), columns=['team', 'n_lowest'])
    tophalf_wins = pd.DataFrame(n_tophalf.items(), columns=['team', 'n_tophalf'])

    dfs = [game_id, wins, highest, lowest, tophalf_wins]

    week_sim = reduce(lambda left, right: pd.merge(left, right, on='team'), dfs)

    return week_sim, score_df
