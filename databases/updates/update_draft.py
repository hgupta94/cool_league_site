from scripts.api.dataloader import DataLoader
from scripts.utils.database import Database
from scripts.utils.constants import DEFAULT_POSITION_MAP_ESPN, SEASON


def load_draft(dataloader:DataLoader, season: int):
    players = dataloader.players_info(n=2000)['players']
    player_map = {
        p['id']: {
            'name': p['player']['fullName'],
            'position': DEFAULT_POSITION_MAP_ESPN[p['player']['defaultPositionId']],
        } for p in players
        if p['player']['defaultPositionId'] in DEFAULT_POSITION_MAP_ESPN
    }

    draft = dataloader.draft()
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

if __name__ == '__main__':
    dataloader = DataLoader(year=SEASON)
    load_draft(dataloader=dataloader, season=SEASON)
