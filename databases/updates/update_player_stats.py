import pandas as pd

from scripts.utils.war import replacement_players
from scripts.api.fantasy_pros import FantasyPros
from scripts.api.settings import LeagueSettings, RosterSettings
from scripts.api.dataloader import DataLoader
from scripts.utils.database import Database
from scripts.utils import constants


def load_player_stats(
        dataloader:DataLoader,
        fpros: FantasyPros,
        season: int = constants.SEASON,
        week: int = constants.WEEK,
        upsert: bool = False,
        upsert_cols: list[str] | None = None
):
    ls = LeagueSettings(dataloader=dataloader)
    rs = RosterSettings(dataloader=dataloader)
    ppr = ls.ppr_type
    oprojections = fpros.get_projections()
    projections = {v['espn_id']: v for v in oprojections if v['espn_id']}
    rosters = dataloader.rosters()

    war_repl = replacement_players(league_settings=ls, roster_settings=rs, season=season, week=week)

    rows = []
    for team in rosters['teams']:
        tid = team['id']
        for player in team['roster']['entries']:
            pid = player['playerId']
            lineup_slot = constants.SLOTCODES_ESPN[player['lineupSlotId']][:4]
            player_entry = player['playerPoolEntry']
            name = player_entry['player']['fullName']
            position = constants.DEFAULT_POSITION_MAP_ESPN[player_entry['player']['defaultPositionId']]

            # get actual points
            stats_entry = player_entry['player']['stats']
            try:
                pts = [v['appliedTotal'] for v in stats_entry if
                       v['seasonId'] == season and v['scoringPeriodId'] == week and v['statSourceId'] == 0][0]
                espn_projection = [v['appliedTotal'] for v in stats_entry if
                                   v['seasonId'] == season and v['scoringPeriodId'] == week and v['statSourceId'] == 1][0]
            except IndexError:
                pts = None
                espn_projection = None

            # get projected points
            try:
                fp_projection = projections[pid].get('projection', None)
                fpid = projections[pid].get('fpid', None)
            except KeyError:
                fp_projection = None
                fpid = None

            projection = fp_projection or espn_projection
            war = None
            if pts is not None and projection > 0:
                war = ((pts - war_repl[position]) / constants.WAR_MARGINAL_POINTS) if pts is not None else None

            rows.append((
                f'{pid}{season}{week:02}',
                season,
                week,
                pid,
                fpid,
                name,
                position,
                tid,
                lineup_slot,
                pts,
                projection,
                'fp' if fp_projection is not None else 'espn',
                ppr,
                war
            ))

    Database().batch_insert(
        table='player_stats',
        columns='id, season, week, espn_id, fp_id, name, position, team_id, lineup_slot, actual, projection, source, ppr, war',
        rows=rows,
        upsert=upsert,
        update_columns=upsert_cols
    )


if __name__ == '__main__':
    dataloader = DataLoader(year=constants.SEASON, week=constants.WEEK)
    fpros = FantasyPros(dataloader=dataloader)
    load_player_stats(dataloader=dataloader, fpros=fpros)
