from scripts.efficiency.efficiency import get_efficiency_scores
from scripts.api.models.player import ParseContext, PlayerView
from scripts.api.dataloader import DataLoader
from scripts.api.settings import TeamSettings
from scripts.utils.database import Database
from scripts.api.models.team import Team
from scripts.utils import constants


def load_efficiency(
        dataloader: DataLoader,
        season: int = constants.SEASON,
        week: int = constants.WEEK-1,
        upsert: bool = False,
        upsert_cols: list[str] | None = None
) -> None:
    """Batch load rows to the efficiency table for the prior week"""

    ctx = ParseContext(view=PlayerView.WEEK, season=season, week=week)
    teams = Team.get_teams(obj=dataloader.teams(), roster_obj=dataloader.rosters(), ctx=ctx, week=week)
    scores = get_efficiency_scores(dataloader=dataloader, teams=teams, season=season, week=week)

    ts = TeamSettings(dataloader)
    rows = []
    for s in scores:
        disp = constants.TEAM_IDS[ts.teamid_to_primowner[s['team']]]['name']['display']
        rowid = f'{s['season']}_{s['week']:02}_{disp}'
        rows.append((
            rowid, s['season'], s['week'], disp,
            s['actual_score'], s['actual_projected'],
            s['best_projected_actual'], s['best_projected_projected'],
            s['best_lineup_actual'], s['best_lineup_projected'],
        ))

    Database().batch_insert(
        table='efficiency',
        columns=constants.EFFICIENCY_COLUMNS,
        rows=rows,
        upsert=upsert,
        update_columns=upsert_cols
    )
