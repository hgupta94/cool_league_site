from scripts.api.dataloader import DataLoader
from scripts.utils.database import Database
from scripts.utils.constants import DEFAULT_POSITION_MAP_ESPN


for season in range(2014, 2027):
    print(season)
    dl = DataLoader(year=season)
    players = dl.players_info(n=2000)['players']
    player_map = {
        p['id']: {
            'name': p['player']['fullName'],
            'position': DEFAULT_POSITION_MAP_ESPN[p['player']['defaultPositionId']],
        } for p in players
        if p['player']['defaultPositionId'] in DEFAULT_POSITION_MAP_ESPN
    }

    draft = dl.draft()
    picks = draft['draftDetail']['picks']

    rows = []
    for pick in picks:
        rows.append((
            f'{season}{pick['id']:03}',
            season,
            draft['settings']['draftSettings']['type'],
            pick['roundId'],
            pick['roundPickNumber'],
            pick['overallPickNumber'],
            pick['bidAmount'] or None,
            pick['nominatingTeamId'] or None,
            pick['teamId'],
            pick['playerId'],
            player_map[pick['playerId']]['name'],
            player_map[pick['playerId']]['position'],
        ))
    Database().batch_insert(
        table='draft',
        columns='id, season, draft_type, round, round_pick, pick, bid, nom_team, pick_team, player_id, player_name, player_position',
        rows=rows
    )

    # else:
    #     rows = []
    #     for pick in picks:
    #         rows.append((
    #             f'{season}{pick['id']:03}',
    #             season,
    #             pick['nominatingTeamId'],
    #             pick['teamId'],
    #             pick['overallPickNumber'],
    #             pick['bidAmount'],
    #             pick['playerId'],
    #             player_map[pick['playerId']]['name'],
    #             player_map[pick['playerId']]['position'],
    #         ))
    #     Database().batch_insert(
    #         table='draft_auction',
    #         columns='id, season, nom_team, team, pick, bid, player_id, player_name, player_position',
    #         rows=rows
    #     )
