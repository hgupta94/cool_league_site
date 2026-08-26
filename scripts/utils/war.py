# calculate replacement player points by position
# not necessarily ACTUAL free agents, but "typical" free agents
# for each position, first calculate expected number of rostered players:
#   1. count total non-flex starters
#   2. count expected bench players from bench_pct
#   3. count expected flex players from flex_pct
#   4. this gets you position rank to start from (ie QB17, RB48, etc.)
#   5. calculate average points from band of 5 (large enough to get some blow ups and busts)
# sum to get a "replacement team" point total (typically 35-45)

from scripts.api.dataloader import DataLoader
from scripts.api.settings import LeagueSettings, RosterSettings
from scripts.utils.constants import (
    DEFAULT_POSITION_MAP_ESPN,
    BENCH_PCT,
    FLEX_PCT,
    IS_FLEX
)


def get_players(season, week):
    # player data for the current season and week

    dl = DataLoader(year=season, week=week)
    players = dl.players_info(n=1000)['players']
    players_week = []
    for p in players:
        if p['player']['defaultPositionId'] not in DEFAULT_POSITION_MAP_ESPN: continue

        pid = p['id']
        name = p['player']['fullName']
        team = p['onTeamId']
        pos = DEFAULT_POSITION_MAP_ESPN[p['player']['defaultPositionId']]
        act = None
        proj = None
        for stat in p['player']['stats']:
            if (stat['seasonId'] == season) & (stat['scoringPeriodId'] == week) & (stat['statSourceId'] == 0):
                act = stat['appliedTotal']
            if (stat['seasonId'] == season) & (stat['scoringPeriodId'] == week) & (stat['statSourceId'] == 1):
                proj = stat['appliedTotal']

        players_week.append([week, pid, team, name, pos, act, proj])
    return players_week


def replacement_players(
        league_settings: LeagueSettings,
        roster_settings: RosterSettings,
        season: int,
        week: int,
):
    band = 5

    n_teams = league_settings.league_size
    lineup_size = roster_settings.lineup_position_limits
    positions = roster_settings.positions

    player_stats = get_players(season=season, week=week)
    player_stats = sorted(player_stats, key=lambda row: float('-inf') if row[-1] is None else row[-1], reverse=True)

    repl_pts_dict = {}
    for p in positions:
        # expected number of rostered players
        p_str = positions[p]
        starters = lineup_size[p]
        avg_flex = (IS_FLEX[p] * FLEX_PCT[p])
        avg_bench = (lineup_size[20] * BENCH_PCT[p])   # 20 = espn bench id
        team_rostered = starters + avg_flex + avg_bench
        total_rostered = n_teams * team_rostered

        # average of top `band` scorers
        vals = [
            pl[-2] for pl in player_stats
            if pl[4] == p_str and pl[-2] is not None
        ]
        window = vals[int(total_rostered):int(total_rostered + band)]
        pts = (sum(window) / len(window)) if window else 0.0
        repl_pts_dict[p_str] = pts

    return repl_pts_dict
