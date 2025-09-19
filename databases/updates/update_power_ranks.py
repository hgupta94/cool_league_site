from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params
from scripts.utils.database import Database
from scripts.utils import constants
from scripts.home.power_ranks import power_rank

import pandas as pd


pr_table = 'power_ranks'
pr_cols = constants.POWER_RANK_COLUMNS
data = DataLoader(year=constants.SEASON)
params = Params(data=data)
# week = params.as_of_week

for week in range(1, params.current_week):
    # get previous week data
    prev_wk = Database(season=constants.SEASON, week=week-1, table='power_ranks').retrieve_data(how='week')

    df = pd.DataFrame(power_rank(params=params, season=constants.SEASON, week=week)).transpose()
    df['season'] = constants.SEASON
    df['week'] = week
    df = df.reset_index().rename(columns={'index': 'team'})
    df['id'] = df['season'].astype(str) + '_' + df['week'].astype(str) + '_' + df['team']
    df['power_rank'] = df.power_score_norm.rank(ascending=False)
    df_final = pd.concat([prev_wk, df])
    df_final['score_raw_change'] = df_final.groupby(['team'])['power_score_raw'].diff()
    df_final['score_norm_change'] = df_final.groupby(['team'])['power_score_norm'].diff()
    df_final['rank_change'] = df_final.groupby(['team'])['power_rank'].diff()
    df_final = df_final[pr_cols.split(', ')].fillna(0)
    df_final = df_final[df_final.week==week]
    for _, row in df_final.iterrows():
        pr_vals = tuple(row)
        db = Database(data=df_final, table=pr_table, columns=pr_cols, values=pr_vals)
        db.commit_row()
    print(f'Commited week {week}')
