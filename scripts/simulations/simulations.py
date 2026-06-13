from scripts.api.dataloader import DataLoader
from scripts.api.fantasy_pros import FantasyPros
from scripts.api.models.schedule import (
    Result,
    Matchup,
    GameType,
    TeamResult
)
from scripts.api.models.team import Team
from scripts.api.models.player import (
    Player,
    ParseContext,
    PlayerView
)
from scripts.api.settings import (
    LeagueSettings,
    RosterSettings,
    TeamSettings
)
from scripts.utils import constants

import scipy.stats as st


class Simulation:
    def __init__(self, dataloader: DataLoader, fpros: FantasyPros):
        print('Starting simulations')
        # TODO: add fantasypros projections
        self.dataloader = dataloader
        self.fpros = fpros

        self.league_settings = LeagueSettings(dataloader=self.dataloader)
        self.roster_settings = RosterSettings(dataloader=self.dataloader)
        self.team_settings = TeamSettings(dataloader=self.dataloader)

        self.ctx = ParseContext(view=PlayerView.WEEK, week=self.league_settings.current_week)
        self.players_obj = self.dataloader.players_info()['players']
        self.teams_obj = self.dataloader.teams()
        self.fpros_proj = self.fpros.get_projections()
        self.rosters_obj = self.dataloader.rosters()

        self.players = Player.get_players(dataloader=self.dataloader, fpros=self.fpros, obj=self.players_obj, ctx=self.ctx)
        self.teams = Team.get_teams(dataloader=self.dataloader, fpros=self.fpros, obj=self.teams_obj, roster_obj=self.rosters_obj, ctx=self.ctx)
        self.matchups = Matchup.get_season_matchups(params=self.league_settings)
        self.results = TeamResult.get_all_team_schedules(dataloader=self.dataloader)

        self.league_size = self.league_settings.league_size
        self.midpoint = self.league_size // 2
        self.playoff_teams = self.league_settings.playoff_teams
        self.gamma_map = constants.GAMMA_VALUES


    def simulate_week(self, n_sims: int) -> dict[str, dict]:
        """
        Simulate a week `n` times and calculate number of occurrences for each category below

        Args:
            n: Number of simulations to run

        Returns:
            Dictionary containing simulation results. For each team,
                - `scores`: total score across all simulations
                - `n_wins`: number of matchup wins
                - `n_tophalf`: number of tophalf wins
                - `n_highest`: number of times with the highest score
                - `n_lowest`: number of times with the lowest score`
        """
        lineups = {k: self._get_best_lineup(v, n_sims=n_sims) for k, v in self.teams.items()}

        # initialize counters
        results = {
            'scores': {key: 0 for key in self.teams},
            'n_wins': {key: 0 for key in self.teams},
            'n_tophalf': {key: 0 for key in self.teams},
            'n_highest': {key: 0 for key in self.teams},
            'n_lowest': {key: 0 for key in self.teams},
        }

        for sim in range(n_sims):
            if sim % 1000 == 0:
                print(f'{sim+1}/{n_sims}', end='\r')
            matchup_sim = self._simulate_matchups(lineups=lineups)

            scores = sorted(m.team_score for m in matchup_sim)
            max_score = max(scores)
            min_score = min(scores)
            median_score = sum(scores[self.midpoint-1 : self.midpoint+1]) / 2
            for team in matchup_sim:
                results['scores'][team.team_id] += team.team_score
                results['n_wins'][team.team_id] += team.matchup_result.value
                results['n_tophalf'][team.team_id] += (
                    Result.WIN.value if team.team_score > median_score
                    else Result.LOSS.value if team.team_score < median_score
                    else Result.TIE.value
                )
                results['n_highest'][team.team_id] += 1 if team.team_score == max_score else 0
                results['n_lowest'][team.team_id] += 1 if team.team_score == min_score else 0

        return results

    def simulate_full_season(
            self,
            results: dict[int, dict],
            n_sims: int,
    ) -> list[dict]:
        """
        Simulate a full regular season + playoffs

        Args:
            results: Up-to-date results for the regular season
            n: Numer of simulations to run

        Returns:
            List of player objects representing the team's best projected lineup
        """
        # get playoff weeks
        current_week = self.league_settings.current_week
        end = self.league_settings.regular_season_end
        start_wk = end + 1 if current_week <= end else current_week  # check if currently in playoffs
        champ_wk = end + self.league_settings.playoff_length
        playoff_wks_left = champ_wk - start_wk + 1
        playoff_weeks = list(range(end + 1, champ_wk + 1))

        lineups = self._build_season_lineups(n_sims=n_sims)

        all_results = []
        for sim in range(n_sims):
            if sim % 100 == 0:
                print(f'{sim+1}/{n_sims}', end='\r')
            # initialize sim counter
            sim_results = {  # initialize sim counter
                o: {
                    'rank': 0,
                    'matchup_wins': 0,
                    'tophalf_wins': 0,
                    'total_wins': 0,
                    'total_points': 0,
                    'most_wins': 0,
                    'most_points': 0,
                    'top_scores': 0,
                    'playoffs': 0,
                    'third': 0,
                    'finals': 0,
                    'champion': 0
                }
                for o in self.teams
            }

            sim_data = self._simulate_regular_season(results=results, lineups=lineups)
            standings = self._get_final_standings(standings=sim_data)
            for rank, (tid, stats) in enumerate(standings.items(), start=1):
                stats['rank'] = rank
            playoff_teams = list(standings)[:self.league_settings.playoff_teams]

            qf_teams = set(playoff_teams.copy())
            sf_teams = None
            third_place_matchup = None
            third = None
            finals_matchup = None
            champion = None
            for i, week in enumerate(playoff_weeks[-playoff_wks_left:]):
                n_bye = 2 if week == start_wk else None
                playoff_teams = self._simulate_round(lineups=lineups, round_teams=playoff_teams, week=week, n_bye=n_bye)
                if week == start_wk:  # quarterfinals
                    sf_teams = set(playoff_teams)
                if week == champ_wk - 1:  # semifinals
                    finals_matchup = set(playoff_teams)
                    third_place_matchup = set(t for t in sf_teams if t not in finals_matchup)
                if week == champ_wk:  # championship
                    # sim third place matchup
                    third_place_lineups = {tid: l for tid, l in lineups[week].items() if tid in third_place_matchup}
                    third_place_sim = {tid: self._simulate_lineup(l) for tid, l in third_place_lineups.items()}
                    third = {max(third_place_sim.items(), key=lambda x: x[1])[0]}
                    champion = set(playoff_teams.copy())

            # update sim stats
            most_wins = max(s['total_wins'] for s in standings.values())
            most_points = max(s['total_points'] for s in standings.values())
            n_most_wins = len([s['total_wins'] for s in standings.values() if s['total_wins'] == most_wins])  # in case there's a tie
            n_most_points = len([s['total_points'] for s in standings.values() if s['total_points'] == most_points])  # in case there's a tie

            for tid in self.teams:
                sim_results[tid]['rank'] += standings[tid]['rank']
                sim_results[tid]['matchup_wins'] += standings[tid]['matchup_wins']
                sim_results[tid]['tophalf_wins'] += standings[tid]['tophalf_wins']
                sim_results[tid]['total_wins'] += standings[tid]['total_wins']
                sim_results[tid]['total_points'] += standings[tid]['total_points']
                sim_results[tid]['top_scores'] += standings[tid]['top_scores']

                if sim_data[tid]['total_points'] == most_points:
                    sim_results[tid]['most_points'] += 1 / n_most_points

                if sim_data[tid]['total_wins'] == most_wins:
                    sim_results[tid]['most_wins'] += 1 / n_most_wins

                # playoffs
                if tid in qf_teams:
                    sim_results[tid]['playoffs'] += 1

                if tid in finals_matchup:
                    sim_results[tid]['finals'] += 1

                if tid in third:
                    sim_results[tid]['third'] += 1

                if tid in champion:
                    sim_results[tid]['champion'] += 1
            all_results.append(sim_results)
        return all_results

    def _get_best_lineup(
            self,
            team: Team,
            n_sims: int,
            n_flex: int = 1
    ) -> list[Player]:
        """
        Calculate the best projected line up for a single team. Uses free agents if a team cannot fill a lineup

        Args:
            team: Team object to calculate a best lineup for
            n_sims: Number of simulations to run
            n_flex: number of flex starters in a lineup

        Returns:
            List of player objects representing the team's best projected lineup
        """
        # lineup settings
        position_map = self.roster_settings.slotcodes
        nfl_starter_limits = {i: v for i, v in self.roster_settings.roster_limits.items() if i in self.roster_settings.positions}  # QB, RB, WR, TE, DST. add position ids if needed
        starter_limits = {i: v for i, v in self.roster_settings.roster_limits.items() if i not in {19, 20, 21, 22, 24, 25}}  # 23 is FLEX
        flex_positions = []
        for i in {3, 5, 23}:  # ESPN flex positions
            if i in starter_limits.keys():
                for pos in position_map[i].split(' ')[1].split('_'):
                    p = next((k for k, v in position_map.items() if v == pos), None)
                    flex_positions.append(p)

        lineup = []
        flex_pool = []
        for position_id, limit in nfl_starter_limits.items():
            # loop thru positions to get best projected lineup
            position_played = {k: v for k, v in team.roster.items() if v.lineup_slot_id == position_id and v.is_locked == True}  # take out players who played
            if position_played:
                lineup.extend(position_played.values())

            pool = {k: v for k, v in team.roster.items() if v.position_id == position_id and v.is_locked == False and (v.pts_proj_fp or v.pts_proj)}
            remaining = limit-len(position_played)
            if remaining:
                selector = sorted(
                    pool.values(),
                    key=lambda i: (i.pts_proj_fp or i.pts_proj or 0.0),
                    reverse=True
                )  # highest projected player(s)

                if len(selector) >= remaining:
                    # add player to lineup
                    lineup.extend(selector[:remaining])
                else:
                    # add all players
                    lineup.extend(selector)

                    # team needs a free agent
                    needed = limit - len(selector)
                    if needed:
                        for i in range(1, needed+1):
                            lineup.extend([
                                Player(
                                    id=int(str(-1 * i) + str(team.team_id) + str(position_id)),
                                    name='Free Agent',
                                    team_id=team.team_id,
                                    position_id=position_id,
                                    position=self.roster_settings.positions[position_id],
                                    lineup_slot_id=position_id,
                                    status='ACTIVE',
                                    pts_proj=self.roster_settings.replacement_players[position_id],
                                    pts_act=None, pts_act_breakdown={}, eligible_slots=[], is_locked=False, is_injured=False,
                                    pts_proj_breakdown={}, percent_owned=None, percent_start=None, source_view=None,
                                )
                            ])

                if position_id in flex_positions:
                    flex_pool.extend(selector[remaining:])
            else:
                continue

        # get flex player
        flex_played = {k: v for k, v in team.roster.items() if v.lineup_slot_id == 23 and v.is_locked == True}
        if flex_played:
            lineup.extend(flex_played.values())
        else:
            flex_selector = sorted(
                flex_pool,
                key=lambda i: (i.pts_proj_fp or i.pts_proj),
                reverse=True
            )
            if flex_selector:
                lineup.extend(flex_selector[:n_flex])
            else:
                flex_id = 23
                fas = {k: v for k, v in self.roster_settings.replacement_players.items() if k in flex_positions}
                the_fa = max(fas.items(), key=lambda i: i[1])
                for i in range(1, n_flex+1):
                    lineup.extend([
                        Player(
                            id=int(str(-1 * i) + str(team.team_id) + str(flex_id)),
                            name='Free Agent',
                            team_id=team.team_id,
                            lineup_slot_id=flex_id,
                            position_id=the_fa[0],
                            status='ACTIVE',
                            pts_proj=the_fa[1],
                            position=None, pts_act=None, pts_act_breakdown={},
                            eligible_slots=[], is_locked=False, is_injured=False, pts_proj_breakdown={},
                            percent_owned=None, percent_start=None, source_view=None,
                        )
                    ])

        # pre-compute gamma parameters for each player
        for player in lineup:
            if not player.is_locked:
                gamma_values = self.gamma_map[player.position_id]
                shape = gamma_values['shape']
                max_val = gamma_values['max']
                proj = (player.pts_proj_fp or player.pts_proj)
                scale = proj / shape
                cdf_max = st.gamma.cdf(max_val, a=shape, loc=0, scale=scale)

                u = st.uniform.rvs(loc=0, scale=cdf_max, size=n_sims)
                player.sim_scores = (s for s in st.gamma.ppf(u, a=shape, scale=scale))
        return lineup

    @staticmethod
    def _simulate_lineup(
            lineup: list[Player]
    ) -> float:
        """
        Simulate a team's total score using their best projected lineup.
        Simulated scores use a gamma distribution

        Args:
            lineup: Starting lineup of the team to simulate

        Returns:
            List of player objects representing the team's best projected lineup
        """
        # add players who played
        projected = 0.0
        for player in lineup:
            if player.is_locked:
                # add if player played
                projected += player.pts_act
            else:
                # simulate if not
                sim = next(player.sim_scores)
                projected += float(sim)
        return projected

    def _simulate_matchups(
            self,
            lineups: dict[int, list[Player]],
            season: int = None,
            week: int = None
    ) -> list[TeamResult]:
        """
        Simulate all matchups for a given week

        Args:
            lineups: Best projected lineup for each team
            season: Season to simulate in
            week: Week to simulate in

        Returns:
            List of TeamResult matchup objects, with the tophalf_wins and wins fields empty
        """

        season = self.league_settings.season if not season else season
        week = self.league_settings.current_week if not week else week
        week_matchups = self.matchups[week]
        matchups_sim = []
        for i, matchup in enumerate(week_matchups):
            game_id = i + 1  # used to group matchups for website

            sim_scores = {}
            for tid, team in matchup.teams.items():
                score = self._simulate_lineup(lineup=lineups[tid])
                sim_scores[tid] = score

            teams = list(sim_scores.keys())
            if len(teams) < 2:
                # team in on bye
                continue

            t1, t2 = teams
            s1, s2 = sim_scores[t1], sim_scores[t2]

            # matchup result
            game_type = (
                GameType.POST
                if self.league_settings.current_week > self.league_settings.regular_season_end
                else GameType.REG
            )
            r1 = Result.WIN if s1 > s2 else Result.LOSS
            r2 = Result.WIN if s2 > s1 else Result.LOSS
            if s1 == s2:
                r1 = r2 = Result.TIE

            matchups_sim.extend([
                TeamResult(
                    season=season,
                    week=week,
                    game_id=game_id,
                    game_type=game_type,
                    team_id=t1,
                    team_score=s1,
                    opponent_id=t2,
                    opponent_score=s2,
                    matchup_result=r1,
                    tophalf_result=None,
                ),
                TeamResult(
                    season=season,
                    week=week,
                    game_id=game_id,
                    game_type=game_type,
                    team_id=t2,
                    team_score=s2,
                    opponent_id=t1,
                    opponent_score=s1,
                    matchup_result=r2,
                    tophalf_result=None,
                ),
            ])
        return matchups_sim

    def _build_season_lineups(self, n_sims: int) -> dict:
        """
        Build the best projected lineup for all remaining weeks, including playoffs
        """
        ros_lineups = {}
        end = self.league_settings.regular_season_end + self.league_settings.playoff_length
        for week in range(self.league_settings.current_week, end+1):
            dataloader = DataLoader(week=week)
            ctx = ParseContext(view=PlayerView.WEEK, week=week)
            teams_obj = dataloader.teams()
            rosters_obj = dataloader.rosters()
            teams = Team.get_teams(dataloader=self.dataloader, fpros=self.fpros, obj=teams_obj, roster_obj=rosters_obj, ctx=ctx)
            lineups = {i: self._get_best_lineup(team=t, n_sims=n_sims) for i, t in teams.items()}
            ros_lineups[week] = lineups
        return ros_lineups

    def _simulate_regular_season(
            self,
            results: dict[int, dict],
            lineups: dict,
    ) -> dict[int, dict]:
        """
        Simulate a full regular season

        Args:
            results: Dictionary of season results up to the current week
            lineups: Rest of season best projected lineup for each team

        Returns:
            List of TeamResult matchup objects, with the tophalf_wins and wins fields empty
        """
        # initialize counters
        ros_results = {
            tid: {
                'matchup_wins': 0,
                'tophalf_wins': 0,
                'total_wins': 0,
                'total_points': 0,
                'top_scores': 0,
            }
            for tid in self.teams.keys()
        }
        for week in range(self.league_settings.current_week, 17+1):
            if week <= self.league_settings.regular_season_end:
                week_sim = {}
                wk_lineups = lineups[week]
                matchups_sim = self._simulate_matchups(lineups=wk_lineups, week=week)
                scores = sorted(m.team_score for m in matchups_sim)
                max_score = max(scores)
                median_score = sum(scores[self.midpoint-1 : self.midpoint+1]) / 2
                for team in matchups_sim:
                    team.tophalf_result = (
                        Result.WIN if team.team_score > median_score
                        else Result.LOSS if team.team_score < median_score
                        else Result.TIE
                    )
                    team.wins = team.tophalf_result.value + team.matchup_result.value
                    team.top_score = 1 if team.team_score == max_score else 0
                    week_sim[team.team_id] = team

                for tid, team in week_sim.items():
                    ros_results[tid]['matchup_wins'] += team.matchup_result.value
                    ros_results[tid]['tophalf_wins'] += team.tophalf_result.value
                    ros_results[tid]['total_wins'] += (team.matchup_result.value + team.tophalf_result.value)
                    ros_results[tid]['total_points'] += team.team_score
                    ros_results[tid]['top_scores'] += team.top_score

        if results:
            merged = {tid: stats.copy() for tid, stats in results.items()}
            for tid, add_stats in ros_results.items():
                if tid not in merged:
                    merged[tid] = {}

                for k, v in add_stats.items():
                    merged[tid][k] = merged[tid].get(k, 0) + v
            return merged
        else:
            return ros_results

    def _get_final_standings(
            self,
            standings: dict[int, dict],
            wild_card: bool = True
    ) -> dict:
        """
        Calculate playoff teams (top 5 by total wins, 6th seed by points)

        Args:
            standings: Dictionary of season simulation and actual results
            wild_card: True (default) if league uses a wild card for the last playoff spot earned by total points

        Returns:
            List of team IDs advancing to the playoffs
        """
        ordered = [
            t[0] for t
            in sorted(
                standings.items(),
                key=lambda x: (x[1]['total_wins'], x[1]['total_points']),
                reverse=True
            )
        ]
        if wild_card:
            final_order = []
            # top by wins, points
            top = ordered[:self.playoff_teams-1]
            final_order.extend(top)

            # wild card by points
            wc = [t[0] for t in sorted(standings.items(), key=lambda x: (x[1]['total_points']), reverse=True) if t[0] not in top][0]
            final_order.extend([wc])

            # rest by wins, points
            bottom = [t for t in ordered if t not in final_order]
            final_order.extend(bottom)
            return {tid: standings[tid] for tid in final_order if tid in standings}
        else:
            # all playoff teams by total wins, points
            standings = ordered[:self.playoff_teams]
            return standings

    def _simulate_round(
            self,
            lineups: dict,
            round_teams: list[int],
            week: int,
            n_bye: int | None = None,
    ):
        advances = []
        if n_bye:
            advances.extend(round_teams[:n_bye])

        remaining_teams = [t for t in round_teams if t not in advances]
        n_advance = len(remaining_teams) // 2
        round_lineups = {t: l for t, l in lineups[week].items() if t in remaining_teams}

        if self.league_settings.current_week > self.league_settings.regular_season_end:
            # if in the playoffs, simulate current matchup
            results = self._simulate_matchups(lineups=round_lineups)
            winners = [r.team_id for r in results if r.matchup_result.value == 1 and r.team_id in round_teams]
            advances.extend(winners)
            return advances
        else:
            # if not in the playoffs, simulate lineup and get tophalf winners
            scores = {}
            for tid, lineup in round_lineups.items():
                scores[tid] = self._simulate_lineup(lineup=lineup)

            to_advance = [t[0] for t in sorted(scores.items(), key=lambda x: x[1], reverse=True)][:n_advance]
            advances.extend(to_advance)
        return advances
