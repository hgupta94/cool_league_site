from scripts.api.Settings import Params
from scripts.utils import utils

import numpy as np


class Teams:
    def __init__(self, data):
        self.settings = data.settings()
        self.teams = data.teams()
        self.matchups = data.matchups()
        self.params = Params(data)

        self.team_ids = []
        self.owner_ids = []
        self.primowner_to_teamid = {}
        self.teamid_to_primowner = {}
        for team in self.teams['teams']:
            t_id = team['id']
            o_id = team['primaryOwner']
            self.team_ids.append(t_id)
            self.owner_ids.append(o_id)
            self.primowner_to_teamid[o_id] = t_id
            self.teamid_to_primowner[t_id] = o_id

        self.faab_budget = self.settings['settings']['acquisitionSettings']['acquisitionBudget']
        self.faab_remaining = None

    def _fetch_matchups(self) -> dict:
        """
        Fetch and format all matchups for the current season
        :returns: Dictionary containing matchup data
        """
        matchups_list = []
        for m in self.matchups['schedule']:
            if all(name in m.keys() for name in ['home', 'away']):
                # checks if a matchup has a home and away team
                # playoff bye weeks do not have both
                week = m['matchupPeriodId']
                matchup_id = m['id']
                team1 = m['home']['teamId']
                score1 = m['home']['totalPoints']
                team2 = m['away']['teamId']
                score2 = m['away']['totalPoints']
                game_type = 'REG' if week <= self.params.regular_season_end else 'POST'

                temp = {
                    'week': week,
                    'matchup_id': matchup_id,
                    'team1': team1,
                    'score1': score1,
                    'team2': team2,
                    'score2': score2,
                    'type': game_type
                }
                matchups_list.append(temp)
        return matchups_list

    def team_schedule(self, team_id: int) -> dict:
        """
        Get full schedule and results for a team for the current season
        :param team_id: ESPN fantasy team ID
        :returns: Dictionary containing a team's matchup results
        """
        matchups_list = self._fetch_matchups()
        home_remap = {'team1': 'team',
                      'score1': 'score',
                      'team2': 'opp',
                      'score2': 'opp_score'}
        away_remap = {'team2': 'team',
                      'score2': 'score',
                      'team1': 'opp',
                      'score1': 'opp_score'}
        team_schedule_home = [x for x in matchups_list if x['team1'] == team_id]
        team_schedule_home = [{home_remap.get(k, k): v for k, v in d.items()} for d in team_schedule_home]
        team_schedule_away = [x for x in matchups_list if x['team2'] == team_id]
        team_schedule_away = [{away_remap.get(k, k): v for k, v in d.items()} for d in team_schedule_away]
        team_schedule_home.extend(team_schedule_away)
        team_schedule = sorted(team_schedule_home, key=lambda d: d['week'])
        for d in team_schedule:
            d['result'] = 1.0 if d['score'] > d['opp_score'] else 0.5 if d['score'] == d['opp_score'] else 0.0
        return team_schedule

    def team_scores(self, team_id: int) -> list[float]:
        """
        Get all scores for a given team for the current season
        :param team_id: ESPN fantasy team ID
        :returns: All scores for a fantasy team
        """
        team_schedule = self.team_schedule(team_id=team_id)
        team_scores = [d['score'] for d in team_schedule if 'score' in d]
        return team_scores

    def week_median(self, week: int) -> float:
        """
        Calculate median score for a given week
        :param week: current league week
        :returns: League median score used to calculate top half results
        """
        matchups = self._fetch_matchups()
        scores = utils.flatten_list(
            [
                list({
                    d[k] for k in ['score1', 'score2'] if k in d
                })
                for d in matchups if d['week'] == week
            ]
        )
        return float(round(np.median(scores), 2))

    def get_all_faab_remaining(self):
        """
        Get Free Agent Acquisition Budget (FAAB) remaining for all teams
        """
        self.faab_remaining = {}
        for tm in self.teams['teams']:
            teamid = tm['id']
            remaining = self.faab_budget - tm['transactionCounter']['acquisitionBudgetSpent']
            self.faab_remaining[teamid] = remaining
        return self.faab_remaining

    def get_team_faab_remaining(self, teamid: int):
        """
        Get Free Agent Acquisition Budget (FAAB) remaining for a given team
        """
        if not self.faab_remaining:
            faab = self.get_all_faab_remaining()
            return faab[teamid]
        else:
            return self.faab_remaining[teamid]