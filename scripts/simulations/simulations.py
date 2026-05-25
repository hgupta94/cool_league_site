from scripts.utils.utils import teamid_to_name
from scripts.api.dataloader import DataLoader
from scripts.utils.database import Database
from scripts.api.settings import LeagueSettings, RosterSettings, TeamSettings
from scripts.utils import constants

import scipy.stats as st
import numpy as np
import pandas as pd
import difflib
pd.options.mode.chained_assignment = None


def _match_player_to_espn(the_player: str,
                          players: list) -> int | None:
    """
    Matches a name to ESPN's database and returns a player ID

    Args:
        the_player: a player's full name, position, and team abbreviation (ex: Full Name|Pos|TM)
        players: list of players to match on from ESPN using same format as the_player

    Returns:
        matching ESPN player ID
    """

    player_lookup = []
    for p in players:
        try:
            pl_name = p['player']['fullName']
            pl_pos = constants.POSITION_MAP[list(set(constants.POSITION_MAP) & set(p['player']['eligibleSlots']))[0]]
            pl_team = constants.NFL_TEAM_MAP[p['player']['proTeamId']]
            pl_lookup = f"{pl_name}|{pl_pos}|{pl_team}"
        except (KeyError, IndexError):
            continue
        player_lookup.append(pl_lookup)

    calc = [difflib.SequenceMatcher(None, the_player, m).ratio() for m in player_lookup]
    if max(calc) > 0.8:
        match_idx = calc.index(max(calc))
        return players[match_idx]['id']
    else:
        return None


def get_week_projections(week: int) -> pd.DataFrame:
    """Return Fantasy Pros projections for all positions"""

    data = DataLoader()
    players = data.players_info()['players']
    positions = ['qb', 'rb', 'wr', 'te', 'dst']

    projections = pd.DataFrame()
    for pos in positions:
        url = f"https://www.fantasypros.com/nfl/projections/{pos}.php?scoring=HALF&week={week}"
        # url = f"https://www.fantasypros.com/nfl/rankings/half-point-ppr-{pos}.php?scoring=HALF&week={week}"
        df = pd.read_html(url)[0]

        # drop multi index column
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel()

        df['POSITION'] = pos.upper()
        try:
            df = df[['Player', 'FPTS', 'REC', 'POSITION']]
        except:
            df = df[['Player', 'FPTS', 'POSITION']]
            df['REC'] = 0

        # remove team from player name
        if pos != 'dst':
            df['TEAM'] = df.Player.str[-3:].str.strip()
            df['Player'] = df['Player'].str[:-3]
            df['Player'] = df['Player'].str.rstrip()

        if pos == 'dst':
            df['Player'] = df['Player'].str.split().str[-1] + ' DST'
            df['TEAM'] = ''

        projections = pd.concat([projections, df])

    projections['season'] = constants.SEASON
    projections['week'] = week
    projections.columns = [c.lower() for c in projections.columns]

    qb_mask = (projections.position == 'QB') & (projections.fpts > 10)
    rb_mask = (projections.position == 'RB') & (projections.fpts > 5)
    wr_mask = (projections.position == 'WR') & (projections.fpts > 5)
    te_mask = (projections.position == 'TE') & (projections.fpts > 3)
    dst_mask = (projections.position == 'DST') & (projections.fpts > 3)
    projections = projections[qb_mask | rb_mask | wr_mask | te_mask | dst_mask]

    # match player to ESPN
    projections['match_on'] = projections.player + '|' + projections.position + '|' + projections.team
    projections['id'] = (projections.player.str.replace(r'[^a-zA-Z0-9]', '', regex=True)
                         + '_' + projections.season.astype(str)
                         + '_' + projections.week.astype(str).str.zfill(2))

    projections['espn_id'] = projections.apply(
        lambda x: _match_player_to_espn(x['match_on'], players), axis=1
    ).astype('Int64')

    return projections[~projections.espn_id.isnull()]


def query_projections_db(season: int,
                         week: int) -> dict:
    cols = ['id', 'season', 'week', 'name', 'espn_id', 'position', 'receptions', 'projection', 'actual', 'created']
    with Database() as conn:
        c = conn.cursor()
        query = f'''
        SELECT *
        FROM player_projections
        WHERE season={season} and week={week};
        '''
        c.execute(query)
        result = c.fetchall()
        df = pd.DataFrame(result)
        df.columns = cols
    return df[['name', 'espn_id', 'projection']].to_dict(orient='records')


def calculate_best_lineup(team_roster: dict,
                          rosters: RosterSettings,
                          n_flex: int = 1):
    positions = constants.POSITION_MAP
    slot_limits = rosters.slot_limits
    selected = []
    for position_id, position in positions.items():
        # loop thru positions to get best projected lineup
        try:
            position_limit = slot_limits[position_id]
            position_played = [p for p in team_roster.items() if p[1]['slot_id'] == position_id and p[1]['played'] == 1]  # take out players who played
            selected.extend([p[0] for p in position_played])
            position_player_pool = {k: v for k, v in team_roster.items() if v['position'] == position and v['played'] == 0}
            remaining = position_limit-len(position_played)
            selector: list = sorted(
                position_player_pool,
                key=lambda x: position_player_pool[x]['projection'],
                reverse=True
            )[0:remaining]  # highest projected player(s)
            selected.extend(selector)  # remove player from available pool
        except KeyError:  # position is not used
            pass

    # get flex player
    flex_played = {k: v for k, v in team_roster.items() if v['slot_id'] == 23 and v['played'] == 1}
    if len(flex_played) > 0:
        selected.extend(list(flex_played.keys()))
    else:
        flex_pool = {k: v for k, v in team_roster.items() if k not in selected and v['position_id'] in [2, 4, 6]}  # RB, WR, TE
        flex_selector = sorted(flex_pool, key=lambda x: flex_pool[x]['projection'], reverse=True)[0:n_flex]
        selected.extend(flex_selector)

    # best projected lineup
    lineup = {k: v
              for k, v
              in team_roster.items()
              if k in selected}
    return lineup


def get_best_lineup(week_data: dict,
                    rosters: RosterSettings,
                    params: LeagueSettings,
                    replacement_players: dict[str, float],
                    projections: list[dict],
                    week: int,
                    team_id: int) -> dict:
    """
    Calculate a team's best lineup using projections from Fantasy Pros

    Args:
        week_data: ESPN data for the selected week
        params: league settings from class
        rosters: roster settings from class
        projections: data from Fantasy Pros
        week: current NFL week
        team_id: team to calculate lineup for
        replacement_players: average of top free agents if team cannot field a full lineup

    Returns:
        dictionary containing the team's best projected players
    """

    slots = constants.SLOTCODES
    positions = constants.POSITION_MAP
    team_data = [t for t in week_data['teams'] if t['id'] == team_id][0]
    roster = {}
    position_id = 0
    position = ''
    for plr in team_data['roster']['entries']:
        # general player data
        player_id = plr['playerId']
        player_name = plr['playerPoolEntry']['player']['fullName']
        slot_id = plr['lineupSlotId']
        lineup_slot = slots[slot_id]
        player_positions = plr['playerPoolEntry']['player']['eligibleSlots']
        for p in player_positions:
            # get NFL position
            try:
                position = positions[p]
                position_id = p
            except KeyError:
                continue

        # get actual and projected scores
        actual = 0
        projection = 0
        played = 0
        for stat in plr['playerPoolEntry']['player']['stats']:
            if stat['scoringPeriodId'] == week:
                if stat['seasonId'] == constants.SEASON and stat['scoringPeriodId'] == week and stat['statSourceId'] == 0:
                    actual = stat['appliedTotal']
                    played = 1
                try:
                    projection = [
                        {k:v for k,v in d.items()}
                        for d in projections
                        if d['espn_id'] == player_id
                    ][0]['projection']
                except IndexError:
                    # use ESPN projection if player is not found
                    if stat['statSourceId'] == 1:
                        projection = stat['appliedTotal']

        if projection > 0:
            roster[player_id] = {
                'player_name': player_name,
                'slot_id': slot_id,
                'lineup_slot': lineup_slot,
                'position_id': position_id,
                'position': position,
                'actual': 0,
                'projection': projection,
                'played': 0
            }

    # check if roster is full, if not fill with replacement player
    roster_non_ir = {k: v for k, v in roster.items() if v['slot_id'] != 21}  # can't put IR player in lineup
    if len(roster_non_ir) < params.roster_size:
        for position in ['QB', 'RB', 'WR', 'TE', 'DST']:
            pos_dict = {k: v for k, v in roster.items() if v['position'] == position}
            pos_id = [k for k, v in rosters.slotcodes.items() if v == position][0]
            limit = rosters.slot_limits[pos_id]
            if len(pos_dict) < limit:
                needed = limit - len(pos_dict)
                for i in range(1, needed + 1):
                    player_id = int(str(-1 * i) + str(pos_id))
                    roster[player_id] = {
                        'player_name': 'Free Agent',
                        'slot_id': pos_id,
                        'lineup_slot': position,
                        'position_id': position_id,
                        'position': position,
                        'actual': 0,
                        'projection': replacement_players[position],
                        'played': 0
                    }

    return calculate_best_lineup(team_roster=roster, rosters=rosters)


def simulate_lineup(lineup: dict) -> float:
    """Simulate a team's total score using the best projected lineup"""

    gamma_map = constants.GAMMA_VALUES  # found by fitting curve to each position using data from 2021-2024
    projected_points = 0.0
    for _, player in lineup.items():
        if player['played']:
            # add players who played first
            sim = player['actual']
            projected_points += sim
        else:
            # add players yet to play
            proj = player['projection']
            gamma_values = gamma_map[player['position']]
            a = gamma_values['a']
            base_scale = gamma_values['scale']
            base_mean = gamma_values['mean']

            # no loc for simplicity/stability; set scale so raw mean ~= proj
            # Gamma mean = a*scale
            scale = base_scale * np.clip((proj / base_mean) ** 0.5, 0.7, 1.5)

            # projection-aware cap: baseline + multiple std devs
            # Gamma std = sqrt(a)*scale
            sd = (a**0.5) * scale
            cap = max(55, proj + 2 * sd)

            # truncated draw via inverse CDF
            fc = st.gamma.cdf(cap, a=a, loc=0.0, scale=scale)
            u = np.random.uniform(0.0, fc)
            sim = st.gamma.ppf(u, a=a, loc=0.0, scale=scale)
            # TODO: figure out a way to use a player's variance to adjust scale
            projected_points += sim
    return projected_points


def simulate_matchup(week_data: DataLoader,
                     rosters: RosterSettings,
                     params: LeagueSettings,
                     replacement_players: dict[str, float],
                     week: int,
                     matchups: list[dict],
                     projections: list[dict]) -> list[dict]:
    """
    Simulate matchups of two teams

    Args:
        week_data: ESPN data for the selected week
        rosters: roster settings from class
        params: league settings from class
        replacement_players: average of top free agents if team cannot field a full lineup
        week: week of matchup to simulate
        matchups: matchups for the selected week
        projections: Fantasy Pros projections for the selected week

    Returns:
        game id, team, simulated score, and simulated result for each team
    """
    matchup_sim = []
    for idx, m in enumerate(matchups):
        matchup = {}
        game_id = idx + 1  # used to group matchups for website

        sim_scores = {}
        for tm in m['teams']:
            team_id = tm['team_id']
            team_name = tm['team_disp']
            lineup = get_best_lineup(week_data=week_data,
                                     rosters=rosters,
                                     params=params,
                                     replacement_players=replacement_players,
                                     projections=projections,
                                     week=week,
                                     team_id=team_id)
            score = simulate_lineup(lineup)
            sim_scores[team_name] = score

            matchup[team_name] = {
                'game_id': game_id,
                'team_id': team_id,
                'score': score
            }

        # get matchup result
        teams = list(sim_scores.keys())
        scores = list(sim_scores.values())
        if scores[0] > scores[1]:
            matchup[teams[0]]['result'] = 1
            matchup[teams[1]]['result'] = 0
        elif scores[0] < scores[1]:
            matchup[teams[0]]['result'] = 0
            matchup[teams[1]]['result'] = 1
        else:  # tie
            matchup[teams[0]]['result'], matchup[teams[1]]['result'] = 0.5, 0.5
        matchup_sim.append(matchup)
    return matchup_sim


def simulate_week(week_data: DataLoader,
                  teams: TeamSettings,
                  rosters: RosterSettings,
                  params: LeagueSettings,
                  replacement_players: dict[str, float],
                  matchups: list,
                  projections: list[dict],
                  week: int,
                  n_sims: int = 10) -> list:
    """Simulate a week n_sims times and calculate number of occurrences for each category below"""

    # initialize counters
    n_scores  = {key: 0 for key in teams.teams}
    n_wins    = {key: 0 for key in teams.teams}
    n_tophalf = {key: 0 for key in teams.teams}
    n_highest = {key: 0 for key in teams.teams}
    n_lowest  = {key: 0 for key in teams.teams}
    mid = len(teams.teams) // 2

    # run simulation
    for i in range(n_sims):
        print(f'{i}/{n_sims}', end='\r')
        matchup_sim = simulate_matchup(week_data=week_data,
                                       rosters=rosters,
                                       params=params,
                                       replacement_players=replacement_players,
                                       week=week,
                                       matchups=matchups,
                                       projections=projections)

        # update counters after simulation
        # get matchup winners
        scores = []
        for matchup in matchup_sim:
            for team, result in matchup.items():
                scores.append(result['score'])
                n_scores[team] += result['score']
                if result['result'] == 1:
                    n_wins[team] += 1

        # get tophalf winners, highest and lowest scores
        max_score = max(scores)
        min_score = min(scores)
        median_score = sum(sorted(scores)[(mid) - 1:(mid) + 1]) / 2
        for matchup in matchup_sim:
            for team, result in matchup.items():
                if result['score'] > median_score:
                    n_tophalf[team] += 1
                if result['score'] == min_score:
                    n_lowest[team] += 1
                if result['score'] == max_score:
                    n_highest[team] += 1

    return n_scores, n_wins, n_tophalf, n_highest, n_lowest


def calculate_odds(init_prob: dict) -> dict:
    """Convert counters from simulation into american odds"""

    # init_prob = sim_value / n_sims
    # round off very likely and unlikely events, less than 10/100,000
    if init_prob >= 0.9999:
        return '&#x2713;'  # check mark
    elif init_prob <= 0.0001:
        return '-'
    else:
        try:
            if init_prob >= 0.5:
                odds = (-1 * init_prob / (1 - init_prob)) * 100
                return f'{max(-10000, round(odds / 5) * 5)}'  # round to nearest 5
            else:
                odds = (1 * (1 - init_prob) / init_prob) * 100
                return f'+{min(10000, round(odds / 5) * 5)}'  # round to nearest 5
        except ZeroDivisionError:  # init_prob = 1 or 0
            if init_prob == 1:
                return '&#x2713;'  # check mark
            else:
                return '-'


def get_matchup_id(teams: TeamSettings,
                   week: int,
                   team_id: int):
    """Create a matchup ID for a team's matchup to display in UI table"""
    matchups = [m for m in teams.matchups if m['week'] == week]
    for m in matchups:
        if any([t['team_disp'] == team_id for t in m['teams']]):  # the current team name is present in the matchup
            return int((len(teams.team_ids) // 2) - ((week * len(teams.team_ids) / 2) - m['matchup_id']))
    return None


def get_ros_projections(data: DataLoader,
                        params: LeagueSettings,
                        teams: TeamSettings,
                        rosters: RosterSettings,
                        replacement_players: dict[str, float] = None):
    """Get rest of season projections from ESPN for all rostered players"""

    projections_dict = {}
    for week in range(params.current_week, 17+1):  # next week (already simmed current week) to end of playoffs+1
        week_data = data.load_week(week)
        team_dict = {}
        for team in week_data['teams']:
            roster_dict = {}
            projection = 0
            position_id = 0
            position = ''
            team_name = ''
            for player in team['roster']['entries']:
                player_id = player['playerId']
                team_name = teamid_to_name(ids=constants.TEAM_IDS, teams=teams, teamid=team['id'])
                player_name = player['playerPoolEntry']['player']['fullName']
                slot_id = player['lineupSlotId']
                for pos in player['playerPoolEntry']['player']['eligibleSlots']:
                    if pos in constants.POSITION_MAP:
                        position_id = pos
                        position = constants.POSITION_MAP[pos]

                for stat in player['playerPoolEntry']['player']['stats']:
                    # check if correct season, week and statSourceId are present in any of the player's dictionaries
                    # if not, get a replacement player
                    if not any(
                            all(
                                stat.get(key) == value
                                for key, value in {
                                    'seasonId': constants.SEASON,
                                    'scoringPeriodId': week,
                                    'statSourceId': 1
                                }.items()
                            )
                            for stat in player['playerPoolEntry']['player']['stats']
                    ):
                        position_id = -1
                        player_name = 'Free Agent'
                        projection = replacement_players[position]

                    else:
                        if stat['seasonId'] == constants.SEASON and stat['scoringPeriodId'] == week and stat['statSourceId'] == 1:
                            projection = stat['appliedTotal']

                if projection > 0:
                    roster_dict[player_id] = {
                        'week': week,
                        'team': team_name,
                        'player_id': player_id,
                        'player_name': player_name,
                        'slot_id': slot_id,
                        'position_id': position_id,
                        'position': position,
                        'projection': projection,
                        'played': 0
                    }

            # check if roster is full, if not fill with replacement player
            roster_non_ir = {k: v for k, v in roster_dict.items() if v['slot_id'] != 21}  # can't put IR player in lineup
            if len(roster_non_ir) < params.roster_size:
                for position in ['QB', 'RB', 'WR', 'TE', 'DST']:
                    pos_dict = {k: v for k, v in roster_dict.items() if v['position'] == position}
                    pos_id = [k for k, v in rosters.slotcodes.items() if v == position][0]
                    limit = rosters.slot_limits[pos_id]
                    if len(pos_dict) < limit:
                        needed = limit - len(pos_dict)
                        for i in range(1, needed+1):
                            player_id = int(str(-1 * i) + str(pos_id))
                            roster_dict[player_id] = {
                                'week': week,
                                'team': team_name,
                                'player_id': player_id,
                                'player_name': 'Free Agent',
                                'slot_id': pos_id,
                                'position_id': pos_id,
                                'position': position,
                                'projection': replacement_players[position],
                                'played': 0
                            }

            team_dict[team_name] = calculate_best_lineup(team_roster=roster_dict, rosters=rosters)
        projections_dict[week] = team_dict
    return projections_dict


def simulate_season(params: LeagueSettings,
                    teams: TeamSettings,
                    lineups: dict,
                    team_names: list[str] = None):
    """Simulate the remaining regular season weeks"""
    all_weeks = []
    for week, team_lineups in lineups.items():
        if week <= params.regular_season_end:
            matchups = [m for m in teams.matchups if m['week'] == week]
            matchup_sim = []
            all_scores = []  # for tophalf results
            for m in matchups:  # entering a matchup
                sim_scores = {}  # for matchup result
                matchup = {}
                for team_sim in m['teams']:  # entering a team in a matchup
                    lineup = team_lineups[team_sim['team_disp']]
                    score = simulate_lineup(lineup)
                    all_scores.append(score)
                    sim_scores[team_sim['team_disp']] = score

                    matchup[team_sim['team_disp']] = {
                        'team_id': team_sim['team_id'],
                        'team_disp': team_sim['team_disp'],
                        'score': score
                    }

                # get matchup result
                m_teams = list(sim_scores.keys())
                scores = list(sim_scores.values())
                if scores[0] > scores[1]:
                    matchup[m_teams[0]]['matchup'] = 1
                    matchup[m_teams[1]]['matchup'] = 0
                elif scores[0] < scores[1]:
                    matchup[m_teams[0]]['matchup'] = 0
                    matchup[m_teams[1]]['matchup'] = 1
                else:  # tie
                    matchup[m_teams[0]]['matchup'], matchup[m_teams[1]]['matchup'] = 0.5, 0.5
                matchup_sim.append(matchup)

            # get tophalf and top score results
            top_score = max(all_scores)
            median = sum(sorted(all_scores)[(len(all_scores) // 2) - 1:(len(all_scores) // 2) + 1]) / 2
            for matchup in matchup_sim:
                for team, result in matchup.items():
                    if result['score'] > median:
                        matchup[team]['tophalf'] = 1
                    else:
                        matchup[team]['tophalf'] = 0

                    if result['score'] == top_score:
                        matchup[team]['top_score'] = 1
                    else:
                        matchup[team]['top_score'] = 0
            all_weeks.append(matchup_sim)

    # summarize results
    season_sim_dict = {
        t: {
            'matchup_wins': 0,
            'tophalf_wins': 0,
            'total_wins': 0,
            'total_points': 0,
            'top_score': 0
        } for t in team_names
    }
    for week in all_weeks:
        for matchup in week:
            for t, result in matchup.items():
                season_sim_dict[t]['matchup_wins'] += result['matchup']
                season_sim_dict[t]['tophalf_wins'] += result['tophalf']
                season_sim_dict[t]['total_wins'] += result['matchup'] + result['tophalf']
                season_sim_dict[t]['total_points'] += result['score']
                season_sim_dict[t]['top_score'] += result['top_score']

    return season_sim_dict


def get_playoff_teams(params: LeagueSettings,
                      sim_data: dict):
    """Calculate playoff teams: top 5 decided by total wins, final seed by most point out of remaining teams"""
    playoff_teams = []

    # top 5 teams by wins
    top5 = [t[0] for t in sorted(sim_data.items(), key=lambda x: (x[1]['total_wins'], x[1]['total_points']), reverse=True)][0: params.playoff_teams-1]
    playoff_teams.extend(top5)

    # sixth seed by most points
    sixth = [t[0] for t in sorted(sim_data.items(), key=lambda x: (x[1]['total_points']), reverse=True) if t[0] not in top5][0]
    playoff_teams.extend([sixth])

    return playoff_teams


def sim_playoff_round(week: int,
                      lineups: dict,
                      params: LeagueSettings,
                      teams: TeamSettings,
                      replacement_players: dict[str, float],
                      projections: list[dict] = None,
                      week_data: DataLoader = None,
                      rosters: RosterSettings = None,
                      n_bye: int = None,
                      round_teams: list[str] = None,
                      matchups: list[dict] = None):
    """Simulates one week of playoffs to determine which teams advance

    week: the week to simulate
    lineups: dictionary of all lineups that week
    rosters: rosters settings from ESPN API
    n_bye: number of teams with a BYE this round
    round_teams: list of teams in the current round

    returns: list of teams advancing to the next round
    """
    this_round_lineups = {t: l for t, l in lineups.items() if t in round_teams}
    next_round_teams = []
    if n_bye:
        # add teams on bye to next round
        next_round_teams.extend(round_teams[0:n_bye])

    # simulate round with remaining teams
    this_round_teams = [t for t in round_teams if t not in next_round_teams]
    n_advance = int(len(this_round_teams) / 2)

    if week_data:
        # if in the playoffs, simulate current matchup
        results = simulate_matchup(week=week, week_data=week_data, rosters=rosters, params=params, replacement_players=replacement_players, matchups=matchups, projections=projections)
        winners = [teamid_to_name(ids=constants.TEAM_IDS, teams=teams, teamid=r['team']) for r in results if r['result']==1]
        next_round_teams.extend(winners)
        return next_round_teams
    else:
        this_round_scores = {}
        for team, lineup in {k: v for k, v in this_round_lineups.items() if k in this_round_teams}.items():
            this_round_scores[team] = simulate_lineup(lineup=lineup)

        # top scoring teams advance to next round
        teams_sorted = dict(sorted(this_round_scores.items(), key=lambda item: item[1], reverse=True))
        next_round_teams.extend(list(teams_sorted.keys())[:n_advance])
        return next_round_teams
