from scripts.api.dataloader import DataLoader
from scripts.utils.database import Database
from scripts.utils import constants

from datetime import datetime as dt, timedelta


def load_trades(
        dataloader: DataLoader,
        season: int = constants.SEASON
):
    trades = []
    seen_trade = set()

    players = dataloader.players_card(n=2000)['players']
    for p in players:
        trans = p.get('transactions')
        for t in trans:
            trade_id = t['id']
            trade_week = t['scoringPeriodId']
            processed = t.get('processDate')
            proposed = t.get('proposedDate')
            timestamp = processed or proposed
            completed = dt.fromtimestamp(timestamp / 1000) or dt.fromtimestamp(timestamp / 1000)

            # check if this trade was made yesterday
            if completed.date() == (constants._TODAY - timedelta(days=1)).date():
                if 'TRADE' in t['type']:
                    for i in t['items']:
                        team_from = i['fromTeamId']
                        team_to = i['toTeamId']
                        player = i['playerId']
                        faab = i['acquisitionBudget']

                        row = (
                            season,
                            trade_week,
                            trade_id,
                            team_from,
                            team_to,
                            player or None,
                            faab,
                            completed.date()
                        )
                        key = (trade_id, player)
                        if key in seen_trade:
                            continue

                        seen_trade.add(key)
                        trades.append(row)

    Database().batch_insert(
        table='trades',
        columns='season, week, trade_id, team_from, team_to, player, faab, completed',
        rows=trades,
        upsert=False,
        update_columns=None
    )


if __name__ == '__main__':
    dataloader = DataLoader()
    load_trades(dataloader=dataloader)
