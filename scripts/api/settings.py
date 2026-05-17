from scripts.api.dataloader import DataLoader
from scripts.utils import constants as const


class LeagueSettings:
    def __init__(self, data):
        settings = data.settings()

        self.league_size = settings['settings']['size']
        self.roster_size = sum(settings['settings']['rosterSettings']['lineupSlotCounts'].values())
        self.regular_season_end = settings['settings']['scheduleSettings']['matchupPeriodCount']
        self.current_week = settings['scoringPeriodId']
        self.as_of_week = 0 if self.current_week-1 < 0 else self.current_week-1  # just finished
        self.playoff_teams = settings['settings']['scheduleSettings']['playoffTeamCount']
        self.playoff_matchup_length = settings['settings']['scheduleSettings']['playoffMatchupPeriodLength']
        self.has_bonus_win = 1 if settings['settings']['scoringSettings'].get('scoringEnhancementType') else 0
        has_ppr = [s['points'] for s in settings['settings']['scoringSettings']['scoringItems'] if s['statId'] == 53]
        self.ppr_type = 0 if not has_ppr else has_ppr[0]
        self.weeks_left = 0 if self.as_of_week > self.regular_season_end else self.regular_season_end - self.as_of_week
        self.team_map = const.TEAM_IDS

class RosterSettings:
    def __init__(self, year=const.SEASON):
        self.data = DataLoader(year=year)
        settings = self.data.settings()
        slot_limits = settings['settings']['rosterSettings']['lineupSlotCounts']
        roster_limits = settings['settings']['rosterSettings']['positionLimits']

        self.player_stats_map = const.PLAYER_STATS_MAP
        self.slotcodes = const.SLOTCODES
        self.nfl_team_map = const.NFL_TEAM_MAP
        self.espn_tonfl_position_map = const.POSITION_MAP
        self.slot_limits = {int(k): v for k, v in slot_limits.items() if v > 0}
        self.roster_limits = {int(k): v for k, v in roster_limits.items() if v > 0}
        self.positions = [v for v in self.espn_tonfl_position_map.values()] + ['FLEX']

    # def get_player_week_actual(self, player_id):
    #     player_id = 4374302
    #     players = self.data.players()
    #     teams = Teams(self.data)
    #
    # def get_player_week_projected(self, player_id):
    #     players = self.data.players()

class TeamSettings:
    def __init__(self, data):
        self._data = data
        self.settings = self._data.settings()
        self.teams = self._data.teams()

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

        self.matchups = self._fetch_matchups()
        self.teams = []
        for team in self.teamid_to_primowner:
            self.teams.append(self._teamid_to_display(team))
        self.faab_budget = self.settings['settings']['acquisitionSettings']['acquisitionBudget']
        self.faab_remaining = None

    def _teamid_to_display(self, teamid: int) -> str:
        """Convert ESPN team ID to display name"""
        return const.TEAM_IDS[self.teamid_to_primowner[teamid]]['name']['display']

    def _fetch_matchups(self) -> list[dict]:
        """
        Fetch and format all matchups for the current season
        :returns: Dictionary containing matchup data
        """
        matchups = []
        for m in self._data.matchups()['schedule']:
            week = m['matchupPeriodId']
            game_type = 'REG' if week <= self.settings['settings']['scheduleSettings']['matchupPeriodCount'] else 'POST'
            matchup_id = m['id']
            matchup = {
                'matchup_id': matchup_id,
                'week': week,
                'game_type': game_type
            }
            teams = []
            for i, tm in enumerate(['home', 'away']):
                try:
                    team_id = m[tm]['teamId']
                    team_disp = self._teamid_to_display(team_id)
                    score = m[tm]['totalPoints']
                    team = {
                        'team_id': team_id,
                        'team_disp': team_disp,
                        'score': score
                    }
                    teams.append(team)
                except KeyError:
                    continue
            matchup['teams'] = teams
            matchups.append(matchup)
        return matchups

    def team_schedule(self, team_id: int) -> dict:
        """
        Get full schedule and results for a team for the current season
        :param team_id: ESPN fantasy team ID
        :returns: Dictionary containing a team's matchup results
        """
        matchups_list = self._fetch_matchups()
        matchups = []
        for matchup in matchups_list:
            teams = matchup['teams']
            if len(teams) != 2:
                continue  # skip incomplete matchups
            if teams[0]['team_id'] == team_id or teams[1]['team_id'] == team_id:
                if teams[0]['team_id'] == team_id:
                    team_score = teams[0]['score']
                    team_disp = teams[0]['team_disp']
                    opp_id = teams[1]['team_id']
                    opp_score = teams[1]['score']
                    opp_disp = teams[1]['team_disp']
                else:
                    team_score = teams[1]['score']
                    team_disp = teams[1]['team_disp']
                    opp_id = teams[0]['team_id']
                    opp_score = teams[0]['score']
                    opp_disp = teams[0]['team_disp']

                # get matchup result
                if team_score > opp_score:
                    result = 1
                elif team_score < opp_score:
                    result = 0
                else:
                    result = 0.5
                matchups.append({
                    'week': matchup['week'],
                    'team_id': team_id,
                    'team_disp': team_disp,
                    'team_score': team_score,
                    'opponent_id': opp_id,
                    'opponent_disp': opp_disp,
                    'opponent_score': opp_score,
                    'result': result
                })

        return matchups

    def team_scores(self, team_id: int) -> list[float]:
        """
        Get all scores for a given team for the current season
        :param team_id: ESPN fantasy team ID
        :returns: All scores for a fantasy team
        """
        team_schedule = self.team_schedule(team_id=team_id)
        team_scores = [d['team_score'] for d in team_schedule if 'team_score' in d]
        return team_scores

    def week_median(self, week: int) -> float:
        """
        Calculate median score for a given week
        :param week: current league week
        :returns: League median score used to calculate top half results
        """
        matchups = self._fetch_matchups()
        scores = []
        for m in matchups:
            if m['week'] == week:
                for tm in m['teams']:
                    if 'score' in tm:
                        scores.append(tm['score'])

        return sum(sorted(scores)[(len(scores) // 2) - 1: (len(scores) // 2) + 1]) / 2

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