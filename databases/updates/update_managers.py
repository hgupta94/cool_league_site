from scripts.utils.constants import TEAM_IDS
from scripts.utils.database import Database

rows = []
for mid, team in TEAM_IDS.items():
    rows.append((
        mid, team['name']['first'], team['name']['last'], team['name']['display'], team['active']
    ))

Database().batch_insert(
    table='managers',
    columns='manager_id, first_name, last_name, display_name, active',
    rows=rows,
    upsert=False,
    update_columns=None
)
