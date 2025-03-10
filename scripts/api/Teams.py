from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params


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
        self.faab_remaining = {}
        for tm in self.teams['teams']:
            teamid = tm['id']
            remaining = self.faab_budget - tm['transactionCounter']['acquisitionBudgetSpent']
            self.faab_remaining[teamid] = remaining

    def _fetch_matchups(self):
        matchups_list = []
        for m in self.matchups['schedule']:
            if all(name in m.keys() for name in ['home', 'away']):
                # checks if a matchup has a home and away team
                # playoff bye weeks do not have both
                week = m['matchupPeriodId']
                team1 = m['home']['teamId']
                score1 = m['home']['totalPoints']
                team2 = m['away']['teamId']
                score2 = m['away']['totalPoints']
                type = 'REG' if week <= self.params.regular_season_end else 'POST'

                temp = {
                    'week': week,
                    'team1': team1,
                    'score1': score1,
                    'team2': team2,
                    'score2': score2,
                    'type': type
                }
                matchups_list.append(temp)
        return matchups_list

    def team_schedule(self, team_id):
        matchups_list = self._fetch_matchups()
        home_remap = {'team1': 'team',
                      'score1': 'score',
                      'team2': 'opp',
                      'score2': 'opp_score'}
        away_remap = {'team2': 'team',
                      'score2': 'score',
                      'team1': 'opp',
                      'score1': 'opp_score',
                      }
        team_schedule_home = [x for x in matchups_list if x['team1'] == team_id]
        team_schedule_home = [{home_remap.get(k, k): v for k, v in d.items()} for d in team_schedule_home]
        team_schedule_away = [x for x in matchups_list if x['team2'] == team_id]
        team_schedule_away = [{away_remap.get(k, k): v for k, v in d.items()} for d in team_schedule_away]
        team_schedule_home.extend(team_schedule_away)
        team_schedule = sorted(team_schedule_home, key=lambda d: d['week'])
        for d in team_schedule:
            d['result'] = 1.0 if d['score'] > d['opp_score'] else 0.5 if d['score'] == d['opp_score'] else 0.0
        return team_schedule

    def team_scores(self, team_id):
        team_schedule = self.team_schedule(team_id=team_id)
        team_scores = [d['score'] for d in team_schedule if 'score' in d]
        return team_scores

    def team_faab_remaining(self, team_id):
        return self.faab_remaining[team_id]
