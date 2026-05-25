from scripts.api.dataloader import DataLoader
from scripts.api.settings import LeagueSettings, TeamSettings
from scripts.utils.database import Database
from scripts.utils import constants
from scripts.home.power_ranks import power_rank

import pandas as pd


data = DataLoader(year=constants.SEASON)
params = LeagueSettings(data=data)
teams = TeamSettings(data=data)
week = params.as_of_week

# get previous week data
prev_wk = Database().retrieve_data(how='week', season=constants.SEASON, week=week-1, table='power_ranks')

df = pd.DataFrame(power_rank(params=params, teams=teams, season=constants.SEASON, week=week)).transpose()
df['season'] = constants.SEASON
df['week'] = week
df = df.reset_index().rename(columns={'index': 'team'})
df['id'] = df['season'].astype(str) + '_' + df['week'].astype(str) + '_' + df['team']
df['power_rank'] = df.power_score_norm.rank(ascending=False)
df_final = pd.concat([prev_wk, df])
df_final['score_raw_change'] = df_final.groupby(['team'])['power_score_raw'].diff()
df_final['score_norm_change'] = df_final.groupby(['team'])['power_score_norm'].diff()
df_final['rank_change'] = df_final.groupby(['team'])['power_rank'].diff()
df_final = df_final[constants.POWER_RANK_COLUMNS.split(', ')].fillna(0)
df_final = df_final[df_final.week==week]

Database().batch_insert(
    table='power_ranks',
    columns=constants.POWER_RANK_COLUMNS,
    rows=[tuple(row) for _, row in df_final.iterrows()]
)
