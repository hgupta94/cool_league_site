from scripts.utils.database import Database
from scripts.utils import constants

from itertools import product, combinations


class PlayoffScenarios:
    def __init__(self, data, params, teams):
        self.data = data
        self.params = params
        self.teams = teams

        self.season = constants.SEASON
        self.team_names = [x['name']['display'] for x in self.params.team_map.values() if x['active']]

        self.matchups = [
            (
                self._teamid_to_display(teamid=m['home']['teamId']),
                self._teamid_to_display(teamid=m['away']['teamId'])
            ) for m in self.data.matchups()['schedule'] if m['matchupPeriodId'] == self.params.current_week
        ]

        self.standings = self._load_standings()
        self.betting_table = self._load_betting_table()

        self.scenarios = self._get_scenarios()

    @staticmethod
    def _sort_standings(standings: list[dict]) -> list[dict]:
        """Sort standings by wins and points"""
        return sorted(standings, key=lambda x: (x['wins'], x['score']), reverse=True)

    def _load_standings(self) -> list[dict]:
        """Load standings from database"""
        df = Database(table='matchups', season=self.season, week=self.params.as_of_week).retrieve_data(how='season')
        df['wins'] = df.matchup_result + df.tophalf_result
        standings = df[['team', 'score', 'wins']].groupby('team').sum().reset_index()
        standings['losses'] = (df.week.max() * 2) - standings.wins
        standings = standings.to_dict(orient='records')
        return self._sort_standings(standings)

    def _load_betting_table(self) -> list[dict]:
        """Load betting table from database for scenario probabilities"""
        df = (
            Database(table='betting_table', season=self.season, week=self.params.current_week)
            .retrieve_data(how='season')
            .sort_values('created').head(len(self.team_names))
        )
        return df[['team', 'matchup_id', 'p_win', 'p_tophalf']].to_dict(orient='records')

    def _teamid_to_display(self, teamid: int) -> str:
        """Convert ESPN team ID to display name"""
        return constants.TEAM_IDS[self.teams.teamid_to_primowner[teamid]]['name']['display']

    def _get_scenarios(self) -> list[dict]:
        """Calculate all possible combinations of matchup and tophalf winners
            for 10 teams:
            - 2**n_teams = 32 h2h scenarios
            - n_teams choose (n_teams / 2) = 252 tophalf scenarios
            - 32 * 252 = 8064 max scenarios
        """
        h2h_outcomes = list(product([0, 1], repeat=len(self.matchups)))
        median_outcomes = list(combinations(self.team_names, len(self.team_names) // 2))
        all_scenarios = []

        for h2h in h2h_outcomes:
            for med_winners in median_outcomes:
                week_winners = {
                    'matchup': {name: 0 for name in self.team_names},
                    'tophalf': {name: 0 for name in self.team_names},
                }

                # H2H results
                for i, (hm, aw) in enumerate(self.matchups):
                    if h2h[i] == 0:
                        week_winners['matchup'][hm] += 1
                    else:
                        week_winners['matchup'][aw] += 1

                # Median results — exactly half the teams get +1
                for name in med_winners:
                    week_winners['tophalf'][name] += 1

                all_scenarios.append(week_winners)

        # assign probability to each scenario and only return possible ones
        for s in all_scenarios:
            matchup_prob = self._matchup_weight(s)
            tophalf_prob = self._normalized_tophalf_weight(s)
            s['p'] = matchup_prob * tophalf_prob

        return [s for s in all_scenarios if s['p'] > 0]

    def _matchup_weight(self, scenario: dict[str, dict]) -> float:
        """Calculate the probability that a set of matchup winners occurs
        Only need to find the product of the winners"""
        matchup_set_prob = 1.0
        for team, result in scenario['matchup'].items():
            if result == 1:
                winner_prob = [o for o in self.betting_table if o['team'] == team][0]['p_win']
                matchup_set_prob *= winner_prob
        return matchup_set_prob

    def _normalized_tophalf_weight(self, scenario: dict[str, dict]) -> float:
        """Calculate the probability that a set of tophalf winners occurs
        Need to find the joint probability of winners and losers and normalize"""

        tophalf_outcomes = combinations(self.team_names, len(self.team_names) // 2)
        th_winners = tuple([t for t, r in scenario['tophalf'].items() if r == 1])
        th_losers = tuple([t for t, r in scenario['tophalf'].items() if r == 0])

        def grouping_weight(winners, losers):
            tophalf_set_prob = 1.0
            for t in winners:
                tophalf_set_prob *= [b for b in self.betting_table if b['team'] == t][0]['p_tophalf']
            for t in losers:
                tophalf_set_prob *= (1 - [b for b in self.betting_table if b['team'] == t][0]['p_tophalf'])
            return tophalf_set_prob

        total_weight = sum(
            grouping_weight(group, [t for t in self.team_names if t not in group])
            for group in tophalf_outcomes
        )
        this_weight = grouping_weight(winners=th_winners, losers=th_losers)
        return this_weight / total_weight if total_weight > 0 else 0.0

    def get_teams(self, standings: list[dict], seed: int) -> tuple[str, str]:
        """Calculate which teams clinched or are eliminated"""
        weeks_left = self.params.regular_season_end - ((standings[0]['wins'] + standings[0]['losses']) // 2)
        clinched = {}
        eliminated = {}
        for tm in standings:
            clinched[tm['team']] = tm['wins'] - standings[seed if seed==2 else seed+1]['wins'] > weeks_left * 2  # 2 results per week. +1 to get 7th seed
            eliminated[tm['team']] = standings[seed-1]['wins'] - tm['wins'] > (weeks_left * 2)  # -1 to get team in that seed

        clinched_tms = [k for k, v in clinched.items() if v]
        eliminated_tms = [k for k, v in eliminated.items() if v]
        return clinched_tms, eliminated_tms

    def get_new_clinches(self, seed: int) -> list[dict]:
        """Calculate new clinching and elimination scenarios based on the current/upcoming week"""
        clinched, eliminated = self.get_teams(standings=self.standings, seed=seed)
        results = {
            name: {
                'clinched': 0,
                'eliminated': 0,
                'p_clinch': 0,
                'p_elim': 0,
                'clinch_scenarios': [],
                'elim_scenarios': []
            }
            for name in self.team_names
        }
        for s in self.scenarios:
            new_standings = []
            for team in self.standings:
                name = team['team']
                new_wins = team['wins'] + s['matchup'][team['team']] + s['tophalf'][team['team']]
                new_standings.append({
                    'team': name,
                    'wins': new_wins,
                    'losses': ((self.params.as_of_week + 1) * 2) - new_wins,  # losses after the current week
                    'score': round(team['score'], 2),  # points don't change for scenario purposes
                })

            # order standings with wild card
            new_standings.sort(key=lambda x: [x['wins'], x['score']], reverse=True)
            top5 = new_standings[:5]
            wc = sorted([s for s in new_standings if s['team'] not in [t['team'] for t in top5]], key=lambda x: x['score'], reverse=True)[0]
            bot4 = [s for s in new_standings if s['team'] not in [t['team'] for t in top5] and s['team'] != wc['team']]
            new_standings = top5 + [wc] + bot4

            new_clinched, new_elim = self.get_teams(standings=new_standings, seed=seed)
            new_clinched = [t for t in new_clinched if t not in clinched]
            new_elim = [t for t in new_elim if t not in eliminated]
            for tm in self.team_names:
                if tm in new_clinched:
                    results[tm]['clinched'] += 1
                    results[tm]['p_clinch'] += s['p']
                    results[tm]['clinch_scenarios'].append(s)
                if tm in new_elim:
                    results[tm]['eliminated'] += 1
                    results[tm]['p_elim'] += s['p']
                    results[tm]['elim_scenarios'].append(s)
        return {k: v for k, v in results.items() if v['clinched'] > 0 or v['eliminated'] > 0}

    def team_magic_number(self, team: str, playoff_spots: int) -> int | None:
        """Calculate magic number to clinch"""
        team = team.title()[:4]  # ensure name is a valid display name (first 4 letters)

        the_team = [s for s in self.standings if s['team'] == team][0]
        current_losses = int(the_team['losses'])
        leading_team_wins = self.standings[playoff_spots-1]['wins']  # -1 to get team in that seed
        if the_team['wins'] >= leading_team_wins:
            return None
        return (
            (self.params.regular_season_end * 2) + 1
            - leading_team_wins
            - current_losses
        )

    def get_magic_numbers(self) -> dict[str, dict[str, int]]:
        magic_numbers = {
            tm: {
                'bye': None,
                'playoff': None
            } for tm in self.teams.teams
        }
        for tm in self.teams.teams:
            for seed in [2, 5]:
                cat = 'bye' if seed == 2 else 'playoff'
                magic = self.team_magic_number(team=tm, playoff_spots=seed)
                if magic is None or magic <= 0:  # clinched or eliminated
                    magic_numbers[tm][cat] = '-'
                else:
                    magic_numbers[tm][cat] = int(magic)
        return magic_numbers