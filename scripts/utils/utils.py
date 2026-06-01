import pandas as pd
from scripts.api.settings import TeamSettings


def flask_get_columns(data: pd.DataFrame) -> tuple[list[str]]:
    """
    Return columns for Flask front end table
    """
    return tuple(data.columns)


def flask_get_data(data) -> list[tuple]:
    """
    Return data formated for Flask front end table
    """
    if type(data) == pd.DataFrame:
        return [tuple(x) for x in data.to_numpy()]

    if type(data) == list:
        return [tuple(x) for x in data]


def flatten_list(lst: list) -> list:
    """
    Flattens a list of lists into a single list
    Only works for 2D lists
    """
    return [
        x
        for xs in lst
        for x in xs
    ]


def teamid_to_name(ids: dict[str, str],
                   teams,
                   teamid: int) -> str:
    """
    Converts an ESPN team ID to the owner's display name for Flask
    """
    return ids[teams.teamid_to_primowner[teamid]]['name']['display']


def calculate_odds(init_prob: dict) -> dict:
    """Convert counters from simulation into american odds"""

    # round off very likely and unlikely events, less than 10/100,000
    if init_prob >= 0.9999:
        return '&#x2713;'  # check mark
    elif init_prob <= 0.0001:
        return '-'
    else:
        try:
            if init_prob >= 0.5:
                odds = (-1 * init_prob / (1 - init_prob)) * 100
                return f'{max(-10000, round(odds / 5) * 5)}'  # round to nearest 5
            else:
                odds = (1 * (1 - init_prob) / init_prob) * 100
                return f'+{min(10000, round(odds / 5) * 5)}'  # round to nearest 5
        except ZeroDivisionError:  # init_prob = 1 or 0
            if init_prob == 1:
                return '&#x2713;'  # check mark
            else:
                return '-'


def get_matchup_id(teams: TeamSettings,
                   week: int,
                   team_id: int):
    """Create a matchup ID for a team's matchup to display in UI table"""
    matchups = [m for m in teams.matchups if m['week'] == week]
    for m in matchups:
        if any([t['team_id'] == team_id for t in m['teams']]):  # the current team name is present in the matchup
            return int((len(teams.team_ids) // 2) - ((week * len(teams.team_ids) / 2) - m['matchup_id']))
    return None
