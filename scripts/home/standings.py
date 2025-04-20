import pandas as pd

from scripts.api.Teams import Teams
from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params
from scripts.utils import constants


class Standings:
    def __init__(self, season, week):
        self.season = season
        self.week = week
        self.data = DataLoader(year=self.season, week=self.week)
        self.teams = Teams(data=self.data)
        self.params = Params(data=self.data)

    def _clinch_bye(self, row, week, three_seed_wins):
        weeks_ahead = (row.overall_wins - three_seed_wins) / 2
        weeks_behind = row['wb2']
        if week < self.params.regular_season_end:
            if weeks_ahead > self.params.weeks_left:
                return constants.CLINCHED

            elif weeks_behind > self.params.weeks_left:
                return constants.ELIMINATED

            else:
                return weeks_behind

    def _clinch_playoff(self, row, week, sixth_wins):
        weeks_ahead = (row.overall_wins - sixth_wins) / 2
        weeks_behind = row['wb5']
        if week < self.params.regular_season_end:
            if weeks_ahead > self.params.weeks_left:
                return constants.CLINCHED

            elif weeks_behind > self.params.weeks_left:
                return constants.ELIMINATED

            else:
                return weeks_behind

    @staticmethod
    def _format_weeks_back(value):
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
        if value < 0:
            return f'+{abs(value):.2f}'  # points ahead
        elif value == 0:
            return '-'  # current seed or tied
        else:
            return f'{value:.2f}'  # points behind

    @staticmethod
    def _format_points(value):
        return f'{value:,.2f}'

    def _calculate_clinches(self,
                            team_name: str,
                            standings_df: pd.DataFrame,
                            wb_col: str,
                            wins_dict: dict) -> dict:
        clinch_weeks_left = self.params.weeks_left - 1
        standings_tm = standings_df[standings_df['team'] == team_name]
        clinched = True if standings_tm[wb_col].values[0] == -99 else False

        if not clinched:
            for wins in range(3):
                wb_added = wins / 2
                new_wb = ((standings_tm.overall_wins.values[0] - wins_dict['seed_plus_one']) / 2) + wb_added
                if new_wb > clinch_weeks_left:
                    return {'wins_needed': wins, 'type': constants.CLINCHED}

    def _calculate_elims(self,
                         team_name: str,
                         standings_df: pd.DataFrame,
                         wb_col: str,
                         wins_dict: dict) -> dict:
        clinch_weeks_left = self.params.weeks_left - 1
        standings_tm = standings_df[standings_df['team'] == team_name]
        eliminated = True if standings_tm[wb_col].values[0] == 99 else False

        if not eliminated:
            for wins in range(3):
                wb_added = wins / 2
                new_wb = ((wins_dict['seed'] - standings_tm.overall_wins.values[0]) / 2) + wb_added
                if new_wb > clinch_weeks_left:
                    return {'wins_needed': -wins, 'type': constants.ELIMINATED}

    def get_matchup_results(self, week) -> list[dict]:
        tm_ids = self.teams.team_ids

        # get median for the week
        median = self.teams.week_median(self.week)

        rows = []
        for tm in tm_ids:
            display_name = constants.TEAM_IDS[self.teams.teamid_to_primowner[tm]]['name']['display']
            db_id = f'{self.season}_{str(self.week).zfill(2)}_{display_name}'

            matchups = self.teams.team_schedule(tm)
            matchups_filter = [{k: v for k, v in d.items()} for d in matchups if d.get('week') == week][0]
            opponent_display_name = constants.TEAM_IDS[self.teams.teamid_to_primowner[matchups_filter['opp']]]['name']['display']
            matchup_result = matchups_filter['result']
            th_result = 1.0 if matchups_filter['score'] > median else 0.5 if matchups_filter['score'] == median else 0.0
            score = matchups_filter['score']

            row = {
                'id': db_id,
                'season': self.season,
                'week': self.week,
                'team': display_name,
                'opponent': opponent_display_name,
                'matchup_result': matchup_result,
                'top_half_result': th_result,
                'score': score
            }
            rows.append(row)
        return rows

    def format_standings(self) -> pd.DataFrame:
        n_playoff_teams = self.params.playoff_teams

        results = []
        for wk in range(1, self.week+1):
            results.extend(self.get_matchup_results(week=wk))

        rows = []
        for team in self.teams.team_ids:
            # standings data for each team
            display_name = constants.TEAM_IDS[self.teams.teamid_to_primowner[team]]['name']['display']
            team_matchups = [m for m in results if m['team'] == display_name]

            m_wins = sum(d['matchup_result'] for d in team_matchups)
            m_losses = self.week - m_wins
            m_record = f'{int(m_wins)}-{int(m_losses)}'

            th_wins = sum(d['top_half_result'] for d in team_matchups)
            th_losses = self.week - th_wins
            th_record = f'{int(th_wins)}-{int(th_losses)}'

            ov_wins = m_wins + th_wins
            ov_losses = m_losses + th_losses
            ov_record = f'{int(ov_wins)}-{int(ov_losses)}'

            win_pct = f'{(ov_wins / (self.week*2)):.3f}'
            total_points = round(sum(d['score'] for d in team_matchups), 2)

            rows.append([display_name, ov_record, ov_wins, win_pct, m_record, th_record, total_points])

        cols = ['team', 'overall', 'overall_wins', 'win_perc', 'matchup', 'top_half', 'total_points']
        standings = pd.DataFrame(rows, columns=cols)
        standings.sort_values(['win_perc', 'total_points'], ascending=[False, False], inplace=True)

        if self.season >= 2021:
            playoff_list = []

            top5 = standings.head(n_playoff_teams-1)
            playoff_list.extend(top5.team.to_list())

            sixth = standings[~standings.team.isin(playoff_list)].sort_values('total_points', ascending=False).head(1)
            playoff_list.extend(sixth.team.values)

            rest = (
                standings[~standings.team.isin(playoff_list)]
                .sort_values(['overall_wins', 'total_points'], ascending=[False, False])
            )

            standings = pd.concat([top5, sixth, rest], axis=0)
            standings['rank'] = range(1, len(standings)+1)

            # for weeks back
            two_seed_wins = standings.iloc[1].overall_wins
            five_seed_wins = standings.iloc[4].overall_wins
            six_seed_points = standings.iloc[5].total_points

            # for clinching/eliminations
            three_seed_wins = standings.iloc[2].overall_wins
            sixth_wins = standings.sort_values(['overall_wins', 'total_points'], ascending=False).iloc[5].overall_wins

            standings['wb2'] = (two_seed_wins - standings.overall_wins) / 2
            standings['wb5'] = (five_seed_wins - standings.overall_wins) / 2
            standings['pb6'] = round(float(six_seed_points) - standings.total_points.astype(float), 2)

            standings['total_points_disp'] = standings.total_points.apply(lambda x: self._format_points(x))
            standings['wb2'] = standings.apply(lambda x: self._clinch_bye(x, week=self.week, three_seed_wins=three_seed_wins), axis=1)
            standings['wb2_disp'] = standings.wb2.apply(lambda x: self._format_weeks_back(x))
            standings['wb5'] = standings.apply(lambda x: self._clinch_playoff(x, week=self.week, sixth_wins=sixth_wins), axis=1)
            standings['wb5_disp'] = standings.wb5.apply(lambda x: self._format_weeks_back(x))
            standings['pb6_disp'] = standings.pb6.apply(lambda x: self._format_points_back(x))

            return standings

    def clinching_scenarios(self, standings_df: pd.DataFrame):
        bye_seed_wins = {
            'seed': standings_df.iloc[1].overall_wins,
            'seed_plus_one': standings_df.iloc[2].overall_wins
        }

        playoff_seed_wins = {
            'seed': standings_df.iloc[4].overall_wins,
            'seed_plus_one': standings_df.sort_values(['overall_wins', 'total_points'], ascending=False).iloc[5].overall_wins}

        rows = []
        for team in self.teams.owner_ids:
            tm = constants.TEAM_IDS[team]['name']['display']
            bye_clinches = self._calculate_clinches(team_name=tm,
                                                    standings_df=standings_df,
                                                    wb_col='wb2',
                                                    wins_dict=bye_seed_wins)
            bye_elims = self._calculate_elims(team_name=tm,
                                              standings_df=standings_df,
                                              wb_col='wb2',
                                              wins_dict=bye_seed_wins)

            playoffs_clinches = self._calculate_clinches(team_name=tm,
                                                         standings_df=standings_df,
                                                         wb_col='wb5',
                                                         wins_dict=playoff_seed_wins)
            playoffs_elims = self._calculate_elims(team_name=tm,
                                                   standings_df=standings_df,
                                                   wb_col='wb5',
                                                   wins_dict=playoff_seed_wins)
            if bye_clinches:
                bc_row = [
                    tm,
                    'bye',
                    bye_clinches['wins_needed'],
                    'clinched' if bye_clinches['type'] == -99 else 'eliminated',
                ]
                print(bc_row)
                rows.append(bc_row)

            if bye_elims:
                be_row = [
                    tm,
                    'bye',
                    bye_elims['wins_needed'],
                    'eliminated' if bye_elims['type'] == 99 else 'clinched',
                ]
                print(be_row)
                rows.append(be_row)

            if playoffs_clinches:
                pc_row = [
                    tm,
                    'playoffs',
                    playoffs_clinches['wins_needed'],
                    'clinched' if playoffs_clinches['type'] == -99 else 'eliminated',
                ]
                print(pc_row)
                rows.append(pc_row)

            if playoffs_elims:
                pe_row = [
                    tm,
                    'playoffs',
                    playoffs_elims['wins_needed'],
                    'eliminated' if playoffs_elims['type'] == 99 else 'clinched',
                ]
                print(pe_row)
                rows.append(pe_row)
        return rows
