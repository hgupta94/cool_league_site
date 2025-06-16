import pandas as pd

from scripts.api.Teams import Teams
from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params
from scripts.utils import constants
from scripts.utils import utils


class Standings:
    def __init__(self, season, week):
        self.season = season
        self.week = week
        self.data = DataLoader(year=self.season, week=self.week)
        self.teams = Teams(data=self.data)
        self.params = Params(data=self.data)
        self.standings_df = pd.DataFrame(columns=['team', 'overall', 'overall_wins', 'win_perc',
                                                  'matchup', 'top_half', 'total_points'])

    def _clinch_bye(self,
                    row: pd.Series,
                    three_seed_wins: float) -> int:
        """
        Calculate if a team clinched playoff BYE week (top 2 seed)
        :param row: A team's standings data
        :param three_seed_wins: Overall wins from third seed, to compare top 2 seeds against
        :returns: -99 if team clinched, 99 if team is eliminated, or # weeks behind 2 seed
        """
        weeks_ahead = (row.overall_wins - three_seed_wins) / 2
        weeks_behind = row['wb2']
        if self.week-1 <= self.params.regular_season_end:
            if weeks_ahead > self.params.weeks_left:
                return constants.CLINCHED

            elif weeks_behind > self.params.weeks_left:
                return constants.ELIMINATED

            else:
                return weeks_behind

    def _clinch_playoff(self,
                        row: pd.Series,
                        sixth_wins: float):
        """
        Calculate if a team clinched playoff spot week (top 5 seed by wins)
        :param row: A team's standings data
        :param sixth_wins: Overall wins from sixth seed by wins, to compare top 5 seeds against
        :returns: -99 if team clinched, 99 if team is eliminated, or # weeks behind 2 seed
        """
        weeks_ahead = (row.overall_wins - sixth_wins) / 2
        weeks_behind = row['wb5']
        if self.week-1 <= self.params.regular_season_end:
            if weeks_ahead > self.params.weeks_left:
                return constants.CLINCHED

            elif weeks_behind > self.params.weeks_left:
                return constants.ELIMINATED

            else:
                return weeks_behind

    @staticmethod
    def _format_weeks_back(value):
        """
        Weeks behind formatter for UI
        """
        if value == constants.CLINCHED:
            return constants.CLINCHED_DISP
        elif value == constants.ELIMINATED:
            return constants.ELIMINATED_DISP
        elif value < 0:
            return f'+{abs(value)}'  # weeks ahead
        elif value > 0:
            return f'{value}'  # weeks behind
        else:
            return '-'  # current seed or tied

    @staticmethod
    def _format_points_back(value):
        """
        Points behind formatter for UI
        """
        if value < 0:
            return f'+{abs(value):.2f}'  # points ahead
        elif value == 0:
            return '-'  # current seed or tied
        else:
            return f'{value:.2f}'  # points behind

    @staticmethod
    def _format_points(value):
        """
        Total points formatter for UI
        """
        return f'{value:,.2f}'

    def _clinch_scenarios(self,
                          team_name: str,
                          seed: int) -> list:
        """
        Calculate clinching scenarios for the current matchup week
        :param team_name: Team display name to calculate clinching scenarios for
        :param seed: Seed to calculate scenarios for (2=BYE week, 5=playoffs by wins)
        :returns: List of team, scenario (bye or playoffs), wins needed, and team(s) needed for clinch
        """
        clinch_type = 'Bye' if seed == 2 else 'Playoffs'
        clinch_weeks_left = self.params.weeks_left
        data = (
            self.standings_df
            .sort_values(['overall_wins', 'total_points'],
                         ascending=[False, False])
            .to_dict(orient='records')
        )
        data_tm = [d for d in data if d['team'] == team_name][0]
        clinched = True if data_tm[f'wb{seed}'] == -99 else False
        eliminated = True if data_tm[f'wb{seed}'] == 99 else False

        if not (clinched or eliminated):
            rows = []
            if data_tm['seed'] <= seed:
                # if team is equal to or ahead of seed, need to clear seed+1 and all teams tied
                seed_plus_one_wins = data[seed]['overall_wins']
                for wins in range(3):
                    wb_added = wins / 2
                    new_wb = ((data_tm['overall_wins'] - seed_plus_one_wins) / 2) + wb_added
                    if new_wb > (clinch_weeks_left - 1):
                        clinch_over_teams = ', '.join([
                            d['team']
                            for d in data
                            if d['team'] != team_name
                               and d['overall_wins'] == seed_plus_one_wins
                        ])
                        row = [team_name, clinch_type, wins, clinch_over_teams]
                        if row[-1] not in utils.flatten_list(rows):
                            rows.append(row)
            else:
                # if team is behind seed, need to clear all teams between them and seed
                team_idx = [i for i, data in enumerate(data) if team_name in data['team']][0]
                seed_to_team = data[(seed-1):team_idx]
                rows = []
                for team_to_clear in seed_to_team:
                    seed_wins = team_to_clear['overall_wins']
                    for wins in range(3):
                        wb_added = wins / 2
                        new_wb = ((data_tm['overall_wins'] - seed_wins) / 2) + wb_added
                        if new_wb > (clinch_weeks_left - 1):
                            clinch_over_teams = ', '.join([
                                d['team']
                                for d in data
                                if d['team'] != team_name
                                   and d['overall_wins'] == seed_wins
                            ])
                            row = [team_name, clinch_type, wins, clinch_over_teams]
                            if row[-1] not in utils.flatten_list(rows):
                                rows.append(row)
            return rows

    def _elim_scenarios(self,
                        team_name: str,
                        seed: int) -> list:
        """
        Calculate elimination scenarios for the current matchup week
        :param team_name: Team display name to calculate elimination scenarios for
        :param seed: Seed to calculate scenarios for (2=BYE week, 5=playoffs by wins)
        :returns: List of team, scenario (bye or playoffs), wins needed, and team(s) to be eliminated by
        """
        elim_type = 'Bye' if seed == 2 else 'Playoffs'
        clinch_weeks_left = self.params.weeks_left
        data = (
            self.standings_df
            .sort_values(['overall_wins', 'total_points'],
                         ascending=[False, False])
            .to_dict(orient='records')
        )
        data_tm = [d for d in data if d['team'] == team_name][0]
        clinched = True if data_tm[f'wb{seed}'] == -99 else False
        eliminated = True if data_tm[f'wb{seed}'] == 99 else False

        if not (clinched or eliminated):
            rows = []
            if data_tm['seed'] > seed:
                # if team is outside seed, eliminated if all teams tied with seed clear them
                # get seed team and any teams tied
                seed_wins = data[seed-1]['overall_wins']
                all_seed_data = [d for d in data if d['overall_wins'] == seed_wins]
                for _ in all_seed_data:
                    for wins in reversed(range(3)):
                        wb_taken = wins / 2
                        new_wb = ((seed_wins - data_tm['overall_wins']) / 2) - wb_taken
                        if abs(new_wb) > (clinch_weeks_left - 1):
                            elim_by_teams = ', '.join([
                                d['team']
                                for d in data
                                if d['team'] != team_name
                                   and d['overall_wins'] == seed_wins
                            ])
                            row = [team_name, elim_type, wins, elim_by_teams]
                            if row[-1] not in utils.flatten_list(rows):
                                rows.append(row)

            else:
                # if team is seed or better, need all teams between them and teams tied with seed+1 to clear them
                team_idx = [i for i, data in enumerate(data) if team_name in data['team']][0]
                team_to_seed = data[(team_idx+1):(seed+1)]
                rows = []
                for team_to_clear in team_to_seed:
                    seed_wins = team_to_clear['overall_wins']
                    for wins in range(3):
                        wb_taken = wins / 2
                        new_wb = ((seed_wins - data_tm['overall_wins']) / 2) + wb_taken
                        if new_wb > (clinch_weeks_left-1):
                            clinch_over_teams = ', '.join([
                                d['team']
                                for d in data
                                if d['team'] != team_name
                                   and d['overall_wins'] == seed_wins
                            ])
                            row = [team_name, elim_type, wins, clinch_over_teams]
                            if row[-1] not in utils.flatten_list(rows):
                                rows.append(row)
            return rows

    def get_matchup_results(self,
                            week: int,
                            team_id: int) -> list[dict]:
        """
        A team's matchup results for a given week
        :param week: The week to get results for
        :param team_id: Fantasy team to get results for
        :returns: Dictionaries of matchup results:
        [
            team,
            season,
            week,
            opponent,
            matchup result,
            top half result,
            week median score,
            team's score
        ]
        """
        week_median = self.teams.week_median(week)

        display_name = constants.TEAM_IDS[self.teams.teamid_to_primowner[team_id]]['name']['display']
        db_id = f'{self.season}_{str(self.week).zfill(2)}_{display_name}'

        matchups = self.teams.team_schedule(team_id)
        matchups_filter = [{k: v for k, v in d.items()} for d in matchups if d.get('week') == week][0]
        opponent_display_name = constants.TEAM_IDS[self.teams.teamid_to_primowner[matchups_filter['opp']]]['name']['display']
        matchup_result = matchups_filter['result']
        th_result = 1.0 if matchups_filter['score'] > week_median else 0.5 if matchups_filter['score'] == week_median else 0.0
        score = matchups_filter['score']

        return {
            'id': db_id,
            'season': self.season,
            'week': week,
            'team': display_name,
            'opponent': opponent_display_name,
            'matchup_result': matchup_result,
            'top_half_result': th_result,
            'median_score': week_median,
            'score': score
        }

    def format_standings(self) -> pd.DataFrame:
        """
        Create standings table for Flask UI
        - 2018-2021: 4 team playoffs by record
        - 2022-present: 6 team playoffs, top 5 by record, 6th seed by most points of remaining teams
        """
        n_playoff_teams = self.params.playoff_teams
        as_of_week = self.params.as_of_week

        for team_id in self.teams.team_ids:
            # results = []
            # for wk in range(1, as_of_week+1):
            #     results.append(self.get_matchup_results(week=wk, team_id=team_id))
            results = [self.get_matchup_results(week=wk, team_id=team_id) for wk in range(1, as_of_week+1)]
                
            # standings data for each team
            display_name = constants.TEAM_IDS[self.teams.teamid_to_primowner[team_id]]['name']['display']
            team_matchups = [m for m in results if m['team'] == display_name]

            m_wins = sum(d['matchup_result'] for d in team_matchups)
            m_losses = as_of_week - m_wins
            m_record = f'{int(m_wins)}-{int(m_losses)}'

            th_wins = sum(d['top_half_result'] for d in team_matchups)
            th_losses = as_of_week - th_wins
            th_record = f'{int(th_wins)}-{int(th_losses)}'

            ov_wins = m_wins + th_wins
            ov_losses = m_losses + th_losses
            ov_record = f'{int(ov_wins)}-{int(ov_losses)}'

            win_pct = f'{(ov_wins / (as_of_week*2)):.3f}'
            total_points = round(sum(d['score'] for d in team_matchups), 2)

            row = [display_name, ov_record, ov_wins, win_pct, m_record, th_record, total_points]
            self.standings_df.loc[len(self.standings_df)] = row

        self.standings_df.sort_values(['win_perc', 'total_points'], ascending=[False, False], inplace=True)

        if self.season >= 2000:
            playoff_list = []

            top5 = self.standings_df.head(n_playoff_teams-1)
            playoff_list.extend(top5.team.to_list())

            sixth = self.standings_df[~self.standings_df.team.isin(playoff_list)].sort_values('total_points', ascending=False).head(1)
            playoff_list.extend(sixth.team.values)

            rest = (
                self.standings_df[~self.standings_df.team.isin(playoff_list)]
                .sort_values(['overall_wins', 'total_points'], ascending=[False, False])
            )

            self.standings_df = pd.concat([top5, sixth, rest], axis=0)
            self.standings_df['seed'] = range(1, len(self.standings_df)+1)

            # for weeks back
            two_seed_wins = self.standings_df.iloc[1].overall_wins
            five_seed_wins = self.standings_df.iloc[4].overall_wins
            six_seed_points = self.standings_df.iloc[5].total_points

            # for clinching/eliminations
            three_seed_wins = self.standings_df.iloc[2].overall_wins
            sixth_wins = self.standings_df.sort_values(['overall_wins', 'total_points'], ascending=False).iloc[5].overall_wins

            self.standings_df['wb2'] = (two_seed_wins - self.standings_df.overall_wins) / 2
            self.standings_df['wb5'] = (five_seed_wins - self.standings_df.overall_wins) / 2
            self.standings_df['pb6'] = round(float(six_seed_points) - self.standings_df.total_points.astype(float), 2)

            self.standings_df['total_points_disp'] = self.standings_df.total_points.apply(lambda x: self._format_points(x))
            self.standings_df['wb2'] = self.standings_df.apply(lambda x: self._clinch_bye(x, three_seed_wins=three_seed_wins), axis=1)
            self.standings_df['wb2_disp'] = self.standings_df.wb2.apply(lambda x: self._format_weeks_back(x))
            self.standings_df['wb5'] = self.standings_df.apply(lambda x: self._clinch_playoff(x, sixth_wins=sixth_wins), axis=1)
            self.standings_df['wb5_disp'] = self.standings_df.wb5.apply(lambda x: self._format_weeks_back(x))
            self.standings_df['pb6_disp'] = self.standings_df.pb6.apply(lambda x: self._format_points_back(x))

            return self.standings_df.reset_index(drop=True)

    def clinching_scenarios(self):
        """
        Formatter for clinching and elimination scenarios for the current matchup week
        """
        clinch_rows = []
        elim_rows = []
        for team in self.teams.owner_ids:
            tm = constants.TEAM_IDS[team]['name']['display']
            bye_clinches = self._clinch_scenarios(team_name=tm,
                                                  seed=2)
            bye_elims = self._elim_scenarios(team_name=tm,
                                             seed=2)

            playoffs_clinches = self._clinch_scenarios(team_name=tm,
                                                       seed=5)
            playoffs_elims = self._elim_scenarios(team_name=tm,
                                                  seed=5)

            if bye_clinches:
                for bc_row in bye_clinches:
                    clinch_rows.append(bc_row)

            if bye_elims:
                for be_row in bye_elims:
                    elim_rows.append(be_row)

            if playoffs_clinches:
                for pc_row in playoffs_clinches:
                    clinch_rows.append(pc_row)

            if playoffs_elims:
                for pe_row in playoffs_elims:
                    elim_rows.append(pe_row)

        return {
            'clinches': clinch_rows,
            'eliminations': elim_rows
        }
