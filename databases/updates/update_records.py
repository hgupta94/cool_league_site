from scripts.records.initialize import *
from scripts.utils.database import Database
from scripts.utils import constants

import pandas as pd


season = constants.SEASON + 1

standings_recs = get_standings_records(season)
longest_streaks = pd.DataFrame(get_streaks_records(), columns=['category', 'record', 'holder', 'season', 'week'])
matchup_recs = get_matchup_records(season)
per_stat_recs = get_per_stat_records(season)
stat_group_records = get_stat_group_records(season)
points_by_position = get_most_points_by_position(season)
records = pd.concat([standings_recs, longest_streaks, matchup_recs, per_stat_recs, stat_group_records, points_by_position])
records = records.reset_index(drop=True).reset_index().rename(columns={'index': 'id'})

records_table = 'records'
records_cols = constants.RECORDS_COLUMNS
for idx, row in records.iterrows():
    db = Database(table=records_table, columns=records_cols, values=tuple(row))
    db.sql_insert_query()
    db.commit_row()
