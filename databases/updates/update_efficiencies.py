from scripts.efficiency.efficiency import get_efficiency_scores
from scripts.api.models.player import ParseContext, PlayerView
from scripts.api.dataloader import DataLoader
from scripts.api.fantasy_pros import FantasyPros
from scripts.utils.database import Database
from scripts.api.models.team import Team
from scripts.utils import constants


def load_efficiency(
        dataloader: DataLoader,
        fpros: FantasyPros,
        season: int = constants.SEASON,
        week: int = constants.WEEK-1,
        upsert: bool = False,
        upsert_cols: list[str] | None = None
) -> None:
    """Batch load rows to the efficiency table for the prior week"""

    ctx = ParseContext(view=PlayerView.WEEK, season=season, week=week)
    teams = Team.get_teams(dataloader=dataloader, fpros=fpros, obj=dataloader.teams(), roster_obj=dataloader.rosters(), ctx=ctx)
    scores = get_efficiency_scores(dataloader=dataloader, teams=teams, season=season, week=week)

    rows = []
    for s in scores:
        rowid = f'{s['season']}_{s['week']:02}_{s['team']:02}'
        rows.append((
            rowid, s['season'], s['week'], s['team'],
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

if __name__ == '__main__':
    d = DataLoader(year=constants.SEASON, week=constants.WEEK-1)
    fp = FantasyPros(dataloader=d)
    load_efficiency(dataloader=d, fpros=fp)
