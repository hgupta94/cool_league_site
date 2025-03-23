from scripts.api.DataLoader import DataLoader
from scripts.api.Teams import Teams
from scripts.api.Rosters import Rosters
from scripts.utils import constants
from scripts.utils import utils

import difflib
import scipy.stats as st
import random
import pandas as pd
pd.options.mode.chained_assignment = None


def _match_player_to_espn(the_player: str,
                          players: list) -> int | None:
    """
    Matches a name to ESPN's database and returns a player ID
    TODO: should include position too

    Args:
        the_player: a player's full name and team abbreviation (ex: Full Name|TM)
        players: list of players to match on from ESPN using same format as the_player

    Returns:
        matching ESPN player ID
    """
    player_lookup = [f"{p['player']['fullName']}|{constants.NFL_TEAM_MAP[p['player']['proTeamId']]}" for p in players]

    calc = [difflib.SequenceMatcher(None, the_player, m).ratio() for m in player_lookup]
    if max(calc) > 0.8:
        match_idx = calc.index(max(calc))
        return players[match_idx]['id']
    else:
        return None


def get_week_projections(week: int) -> pd.DataFrame:
    """Return Fantasy Pros projections for all positions"""

    data = DataLoader()
    players = data.players()['players']
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
    projections['match_on'] = projections.player + '|' + projections.team
    projections['id'] = (projections.player.str.replace(r'[^a-zA-Z]', '', regex=True)
                         + '_' + projections.season.astype(str)
                         + '_' + projections.week.astype(str).str.zfill(2))
    projections['espn_id'] = projections.apply(
        lambda x: _match_player_to_espn(x['match_on'], players), axis=1
    ).astype('Int64')

    return projections[~projections.espn_id.isnull()]


def query_projections_db(season: int,
                         week: int) -> pd.DataFrame:
    cols = ['id', 'season', 'week', 'name', 'espn_id', 'position', 'receeptions', 'projection', 'created']
    with utils.mysql_connection() as conn:
        c = conn.cursor()
        query = f'''
        SELECT *
        FROM projections
        WHERE season={season} and week={week};
        '''
        c.execute(query)
        result = c.fetchall()
        df = pd.DataFrame(result)
        df.columns = cols
    return df[['name', 'espn_id', 'projection']].set_index('espn_id').to_dict(orient='index')


def get_best_lineup(week_data: DataLoader,
                    rosters: Rosters,
                    projections: list[dict],
                    week: int,
                    team_id: int) -> dict:
    """
    Calculate a team's best lineup using projections from Fantasy Pros

    Args:
        week_data: ESPN data for the selected week
        rosters: roster settings from class
        projections: data from Fantasy Pros
        week: NFL week
        team_id: team to calculate lineup for

    Returns:
        dictionary containing the team's best projected players
    """

    slots = constants.SLOTCODES
    positions = constants.POSITION_MAP
    slot_limits = rosters.slot_limits
    team_data = [t for t in week_data['teams'] if t['id'] == team_id][0]
    roster = {}
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
        # TODO: need to know what this looks like when player hasn't played yet
        # TODO: need to figure out player injuries/bye weeks
        actual = 0
        projection = 0
        for stat in plr['playerPoolEntry']['player']['stats']:
            if stat['scoringPeriodId'] == week:
                if stat['statSourceId'] == 0:
                    pass
                    # actual = stat['appliedTotal']
                try:
                    projection = [
                        {k:v for k,v in d.items()}
                        for d in projections
                        if d['espn_id'] == player_id
                    ][0]['fpts']
                except IndexError:
                    # use ESPN projection of player is not found
                    if stat['statSourceId'] == 1:
                        projection = stat['appliedTotal']

        roster[player_id] = {
            'player_name': player_name,
            'slot_id': slot_id,
            'lineup_slot': lineup_slot,
            'position_id': position_id,
            'position': position,
            'actual': actual,
            'projection': projection
        }

    selected = []
    for player_id, pos in positions.items():
        # loop thru positions to get best projected lineup
        # TODO: need to update this to keep players who actually played
        position_limit = slot_limits[player_id]
        position_player_pool = {k: v for k, v in roster.items() if v['position'] == pos}
        selector = sorted(position_player_pool,
                          key=lambda x: position_player_pool[x]['projection'],
                          reverse=True)[0:position_limit]  # highest projected player(s)
        selected.append(selector)  # remove player from available pool
    selected_flat = utils.flatten_list(selected)

    # get flex player
    flex_pool = {k: v for k, v in roster.items() if k not in selected_flat and v['position_id'] in [2, 4, 6]}
    flex_selector = sorted(flex_pool, key=lambda x: flex_pool[x]['projection'], reverse=True)[0:1][0]

    # best projected lineup
    selected_flat.append(flex_selector)
    lineup = {k: v
              for k, v
              in roster.items()
              if k in selected_flat}
    return lineup


def simulate_lineup(lineup: dict) -> float:
    """Simulate a team's total score using the best projected lineup"""

    gamma_map = constants.GAMMA_VALUES  # found by fitting curve to each position using data from 2021-2024
    projected_points = 0.0
    for _, player in lineup.items():
        gamma_values = gamma_map[player['position']]
        loc = gamma_values['loc'] + (player['projection'] - gamma_values['mean'])
        sim = st.gamma.rvs(a=gamma_values['a'], loc=loc, scale=gamma_values['scale'], size=1).item()
        # TODO: figure out a way to use a player's variance to adjust scale
        projected_points += sim
        # print(plr['player_name'], round(sim,2))
    # print(proj_points-base)
    return projected_points


def simulate_matchup(week_data: DataLoader,
                     rosters: Rosters,
                     week: int,
                     matchups: list[dict],
                     projections: list[dict]) -> list[dict]:
    """
    Simulate matchups of two teams

    Args:
        week_data: ESPN data for the selected week
        rosters: roster settings from class
        week: week of matchup to simulate
        matchups: matchups for the selected week
        projections: Fantasy Pros projections for the selected week

    Returns:
        game id, team, simulated score, and simulated result for each team
    """

    matchup_sim = []
    for idx, m in enumerate(matchups):
        game_id = idx + 1  # used to group matchups for website

        team1 = m['away']['teamId']
        lineup1 = get_best_lineup(week_data=week_data,
                                  rosters=rosters,
                                  projections=projections,
                                  week=week,
                                  team_id=team1)
        sim1 = simulate_lineup(lineup1)

        team2 = m['home']['teamId']
        lineup2 = get_best_lineup(week_data=week_data,
                                  rosters=rosters,
                                  projections=projections,
                                  week=week,
                                  team_id=team2)
        sim2 = simulate_lineup(lineup2)

        # redo sim if they are somehow tied
        if sim1 == sim2:
            sim1 = simulate_lineup(lineup1)
            sim2 = simulate_lineup(lineup2)

        matchup_sim.append({
            'game_id': game_id,
            'team': team1,
            'score': sim1,
            'result': 1 if sim1 > sim2 else 0
        })

        matchup_sim.append({
            'game_id': game_id,
            'team': team2,
            'score': sim2,
            'result': 1 if sim2 > sim1 else 0
        })

    return matchup_sim


def simulate_week(week_data: DataLoader,
                  teams: Teams,
                  rosters: Rosters,
                  matchups: list,
                  projections: list[dict],
                  week: int,
                  n_sims: int = 10) -> list:
    """Simulate a week n_sims times and calculate number of occurrences for each category below"""

    # initialize counters
    n_scores  = {key: 0 for key in teams.team_ids}
    n_wins    = {key: 0 for key in teams.team_ids}
    n_tophalf = {key: 0 for key in teams.team_ids}
    n_highest = {key: 0 for key in teams.team_ids}
    n_lowest  = {key: 0 for key in teams.team_ids}
    for i, sim in enumerate(range(n_sims)):
        print(f'{i+1}/{n_sims}', end='\r')
        random.seed(random.randrange(n_sims))
        matchup_sim = simulate_matchup(week_data=week_data,
                                       rosters=rosters,
                                       week=week,
                                       matchups=matchups,
                                       projections=projections)

        # update counters after simulation
        for team in matchup_sim:
            n_scores[team['team']] += team['score']
            if team['result'] == 1:
                n_wins[team['team']] += 1

        for_tophalf = sorted(matchup_sim, key=lambda d: d['score'], reverse=True)[:int((len(teams.team_ids)/2))]
        for team in for_tophalf:
            n_tophalf[team['team']] += 1

        n_highest[max(matchup_sim, key=lambda x: x['score'])['team']] += 1
        n_lowest[min(matchup_sim, key=lambda x: x['score'])['team']] += 1

    return [n_scores, n_wins, n_tophalf, n_highest, n_lowest]


def calculate_odds(sim_result: dict,
                   n_sims: int) -> dict:
    """Convert counters from simulation into american odds"""

    odds_dict = {}
    for k, v in sim_result.items():
        init_prob = v / n_sims
        if init_prob / (1 - init_prob) >= 1:
            odds = (-1 * init_prob / (1 - init_prob)) * 100
            odds_dict[k] = f'{max(-10000, round(odds / 5) * 5)}'  # round to nearest 5
        else:
            odds = (1 * (1 - init_prob) / init_prob) * 100
            odds_dict[k] = f'+{min(10000, round(odds / 5) * 5)}'  # round to nearest 5
    return odds_dict


















