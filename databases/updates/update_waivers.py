from scripts.api.dataloader import DataLoader
from scripts.utils.database import Database
from scripts.utils.constants import SEASON, WEEK

from datetime import datetime as dt

# TODO: add a check for if the move was made today
def load_waivers(
        dataloader:DataLoader,
        season: int = SEASON,
        week: int = WEEK
):
    waivers = dataloader.transactions()
    rows = []
    if 'transactions' in waivers:
        for tran in waivers['transactions']:
            if tran['type'] == 'WAIVER' and tran['status'] == 'EXECUTED':
                team = tran['teamId']
                if team < 0:
                    ids = []
                    for i in tran['items']:
                        ids.append(i['fromTeamId'])
                        ids.append(i['toTeamId'])
                    team = max(ids)
                bid = tran['bidAmount']
                completed = dt.fromtimestamp(tran['processDate'] / 1000).date()
                is_commish = tran['isLeagueManager'] or tran['isActingAsTeamOwner']
                added = None
                dropped = None
                for i in tran['items']:
                    if i['type'] == 'ADD':
                        added = i['playerId']
                    else:
                        dropped = i['playerId']

                if added or dropped:
                    row = (season, week, team, bid, added, dropped, completed, is_commish)
                    rows.append(row)

    Database().batch_insert(
        table='draft',
        columns='season, week, team, bid, added, dropped, completed. is_commish',
        rows=rows
    )

if __name__ == '__main__':
    dataloader = DataLoader(year=SEASON)
    load_waivers(dataloader=dataloader)
