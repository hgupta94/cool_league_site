import pandas as pd

from scripts.utils.database import Database
from scripts.api.dataloader import DataLoader
from scripts.api.fantasy_pros import FantasyPros
from scripts.utils.constants import DEFAULT_POSITION_MAP_ESPN


# dl = DataLoader(year=2025)
# fp = FantasyPros(dataloader=dl, season=2025, week=1)
# proj = fp.get_projections(ros=True)
# fp_df = pd.DataFrame.from_records(proj)


db = Database()
data = db.retrieve_data(table='player_stats', how='all')
flex = data[(data.lineup_slot == 'Flex')]
flex_by_season = (flex.groupby(['season', 'position']).size() / flex.groupby('season').size()).reset_index()
# about 60% RB/37% WR/3% TE



bench = data[(data.lineup_slot == 'BE')]
bench_by_season = bench.groupby(['season', 'position']).size() / bench.groupby('season').size()
# about 10% QB/TE, 5% DST, split RB/WR


bids = {
    'QB': 0,
    'RB': 0,
    'WR': 0,
    'TE': 0,
    'DST': 0,
}
counts = {
    'QB': 0,
    'RB': 0,
    'WR': 0,
    'TE': 0,
    'DST': 0
}
total_picks = 0
for season in [2022, 2023, 2024, 2025]:
    season = 2025
    rows = []
    print(season)
    d = DataLoader(year=season)
    settings = d.settings()
    players = d.players_info(n=1000)['players']
    draft = d._loader(view='chui_default').get('draftDetail', {})
    picks = draft.get('picks', [])
    for pick in picks:
        pid = pick['playerId']
        try:
            the_player = [p for p in players if p['id'] == pid][0]
            name = the_player['player']['fullName']
            proj = [s['appliedTotal'] for s in the_player['player']['stats'] if s['seasonId'] == 2025 and s['statSourceId'] == 1 and s['statSplitTypeId'] == 0][0]
            pos = DEFAULT_POSITION_MAP_ESPN[the_player['player']['defaultPositionId']]
        except IndexError:
            pos = list(set(data[data.espn_id == pid].position))[0]
            name = ''
            proj = 0
        rows.append([
            pick['overallPickNumber'],
            pick['bidAmount'],
            pick['playerId'],
            name,
            proj,
            pos,
            pick['teamId'],
        ])
        bids[pos] += pick['bidAmount']
        counts[pos] += 1
        total_picks += 1

print({k: v/sum(bids.values()) for k, v in bids.items()})
print({k: v/total_picks for k, v in counts.items()})



draft_df = pd.DataFrame(rows, columns=['pick', 'bid', 'player_id', 'name', 'projection', 'position', 'team'])
price_df = (
    pd.DataFrame.from_dict(price_data, orient='index')
    .reset_index()
    .rename(columns={'index': 'player_id'})
)
final_df = pd.merge(draft_df, price_df[['player_id', 'vor', 'price']], on='player_id', how='inner')


import numpy as np
from scipy.optimize import minimize_scalar

def predicted_prices(vor_array, exponent, avail_spend, min_bid, n_rostered):
    spend_above_floor = avail_spend - n_rostered * min_bid
    vor_adj = np.maximum(vor_array, 0) ** exponent
    total = vor_adj.sum()
    return min_bid + (vor_adj / total) * spend_above_floor

def loss(exponent, vor_array, actual_prices, avail_spend, min_bid, n_rostered):
    pred = predicted_prices(vor_array, exponent, avail_spend, min_bid, n_rostered)
    return np.sum((pred - actual_prices) ** 2)  # SSE

for pos in set(final_df.position):
    pos_df = final_df[final_df.position == pos]
    vor_array = pos_df.vor.values
    actual_prices = pos_df.bid.values
    avail_spend = 1850
    min_bid = 1
    n_rostered = 150
    result = minimize_scalar(
        loss,
        bounds=(1.0, 3.0),
        method='bounded',
        args=(vor_array, actual_prices, avail_spend, min_bid, n_rostered)
    )
    best_exponent = result.x
    print(pos, best_exponent)