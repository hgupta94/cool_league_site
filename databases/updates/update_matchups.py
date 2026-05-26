from scripts.utils import constants
from scripts.utils.database import Database
from scripts.api.dataloader import DataLoader
from scripts.api.models.schedule import TeamSchedule
from scripts.api.settings import LeagueSettings, TeamSettings


data = DataLoader(year=constants.SEASON)
params = LeagueSettings(data=data)
teams = TeamSettings(data=data)
week = params.as_of_week
schedules = TeamSchedule.get_all_team_schedules(week=week)

rows = []
for t in teams.team_ids:
    team_matchup = schedules[t][week]
    team_disp = teams._teamid_to_display(team_matchup.team_id)
    row = (
        f'{team_matchup.season}_{team_matchup.week:02}_{team_disp}',
        team_matchup.season,
        team_matchup.week,
        team_disp,
        team_matchup.team_score,
        teams._teamid_to_display(team_matchup.opponent_id),
        team_matchup.opponent_score,
        team_matchup.matchup_result,
        team_matchup.tophalf_result,
        team_matchup.game_type
    )
    rows.append(row)

Database().batch_insert(
    table='matchups',
    columns=constants.MATCHUP_COLUMNS,
    rows=rows
)
