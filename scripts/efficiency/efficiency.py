from scripts.api.settings import RosterSettings
from scripts.api.dataloader import DataLoader
from scripts.api.models.team import Team
from scripts.utils import constants


def get_efficiency_scores(
        dataloader: DataLoader,
        teams: dict[int, Team],
        season: int = constants.SEASON,
        week: int = constants.WEEK-1,
) -> list[dict]:
    # roster settings
    roster_settings = RosterSettings(dataloader=dataloader)
    position_map = roster_settings.slotcodes
    slot_limits = roster_settings.roster_limits
    starter_limits = {i: v for i, v in slot_limits.items() if i not in {19, 20, 21, 22, 24, 25}}  # 23 is FLEX
    nfl_position_limits = {i: v for i, v in slot_limits.items() if i in {0, 2, 4, 6, 16}}  # QB, RB, WR, TE, DST. add position ids if needed
    flex_positions = []
    for i in [23, 5, 3]:  # ESPN flex positions
        if i in starter_limits.keys():
            for pos in position_map[i].split(' ')[1].split('_'):
                p = next((k for k, v in position_map.items() if v == pos), None)
                flex_positions.append(p)

    scores = []
    for t_id, team in teams.items():
        roster = team.roster
        act_lineup_act = sum(p.pts_act for p in roster.values() if p.lineup_slot_id in starter_limits.keys())
        act_lineup_proj = sum(p.pts_proj for p in roster.values() if p.lineup_slot_id in starter_limits.keys())

        # optimal lineup
        best_proj_lineup = []
        best_proj_flex_pool = []
        optimal_lineup = []
        optimal_flex_pool = []
        for pos_id, pos_limit in nfl_position_limits.items():
            pool = [p for p in roster.values() if p.position_id == pos_id]

            best_proj_selector = sorted(pool, key=lambda p: (p.pts_proj or 0), reverse=True)
            best_proj_lineup.extend(best_proj_selector[:pos_limit])

            opt_selector = sorted(pool, key=lambda p: (p.pts_act or 0), reverse=True)
            optimal_lineup.extend(opt_selector[:pos_limit])

            # get flex pool
            if pos_id in flex_positions:
                best_proj_flex_pool.extend(best_proj_selector[pos_limit:])
                optimal_flex_pool.extend(opt_selector[pos_limit:])

        for i in {3, 5, 23}:
            if i in starter_limits.keys():
                flex_limit = starter_limits[i]
                best_proj_lineup.extend([max(best_proj_flex_pool, key=lambda p: (p.pts_proj or 0))][:flex_limit])
                optimal_lineup.extend([max(optimal_flex_pool, key=lambda p: (p.pts_act or 0))][:flex_limit])

        best_proj_lineup_act = sum((p.pts_act or 0) for p in best_proj_lineup)
        best_proj_proj = sum((p.pts_proj or 0) for p in best_proj_lineup)

        opt_lineup_act = sum((p.pts_act or 0) for p in optimal_lineup)
        opt_lineup_proj = sum((p.pts_proj or 0) for p in optimal_lineup)

        scores.append({
            'season': season,
            'week': week,
            'team': t_id,
            'actual_score': act_lineup_act,
            'actual_projected': act_lineup_proj,
            'best_projected_actual': best_proj_lineup_act,
            'best_projected_projected': best_proj_proj,
            'best_lineup_actual': opt_lineup_act,
            'best_lineup_projected': opt_lineup_proj,
        })
    return scores
