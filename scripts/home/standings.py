from enum import Enum

from scripts.api.dataloader import DataLoader
from scripts.api.models.schedule import TeamResult
from scripts.home.playoff_scenarios import PlayoffScenarios
from scripts.api.settings import LeagueSettings, TeamSettings


class Status(str, Enum):
    CLINCHED = -99
    ELIMINATED = 99
    CLINCHED_DISP = 'c'
    ELIMINATED_DISP = 'x'

class Standings:
    def __init__(self, dataloader: DataLoader, season, week):
        self.dataloader = dataloader
        self.season = season
        self.week = week
        self.league_settings = LeagueSettings(dataloader=self.dataloader)
        self.team_settings = TeamSettings(dataloader=self.dataloader)
        self.matchups: dict = TeamResult.get_all_team_schedules(dataloader=self.dataloader)
        self.playoff_scenarios = PlayoffScenarios(dataloader=self.dataloader)

    @staticmethod
    def _format_points_back(value):
        """
        Points behind formatter for UI
        """
        if value > 0:
            return f'+{value:.2f}'  # points ahead
        elif value == 0:
            return '-'  # current seed or tied
        else:
            return f'{abs(value):.2f}'  # points behind

    def _weeks_back(self,
                    value: float) -> int | None:
        """
        Calculate if a team clinched playoff BYE week (top 2 seed)
        :param value: Team weeks back of bye seed
        :returns: -99 if team clinched, 99 if team is eliminated, or # weeks behind 2 seed
        """
        if self.week-1 <= self.league_settings.regular_season_end:
            if value > 0 and abs(value) > self.league_settings.weeks_left:
                return Status.CLINCHED_DISP.value

            elif value < 0 and abs(value) > self.league_settings.weeks_left:
                return Status.ELIMINATED_DISP.value

            elif value > 0:
                return f'+{value}'  # weeks behind

            elif value < 0:
                return f'{abs(value)}'  # weeks ahead

            else:
                return '-'  # current seed or tied

        return '-'

    def _clinch_scenarios(self,
                          team_id: int,
                          seed: int) -> list:
        """
        Calculate clinching scenarios for the current matchup week
        :param team_id: Team display name to calculate clinching scenarios for
        :param seed: Seed to calculate scenarios for (2=BYE week, 5=playoffs by wins)
        :returns: List of team, scenario (bye or playoffs), wins needed, and team(s) needed for clinch
        """
        clinch_type = 'Bye' if seed == 2 else 'Top 5'
        clinch_weeks_left = self.league_settings.regular_season_end - self.week
        data = sorted(self.format_standings(), key=lambda x: (x['wins'], x['points']), reverse=True)
        data_tm = [d for d in data if d['team_id'] == team_id][0]
        clinched = True if data_tm[f'wb{seed}'] == 'c' else False
        eliminated = True if data_tm[f'wb{seed}'] == 'x' else False

        if not (clinched or eliminated):
            if data_tm['seed'] <= seed:
                # if team is equal to or ahead of seed, need to clear seed+1 and all teams tied
                seed_plus_one_wins = data[seed]['wins']
                for wins in range(-2, 3):
                    wb_added = wins / 2
                    new_wb = ((data_tm['wins'] - seed_plus_one_wins) / 2) + wb_added
                    if new_wb > clinch_weeks_left:
                        clinch_over_teams_w_pts = ','.join([
                            f'{d["team_id"]} ({round(d["points"] - data_tm["points"], 2) if clinch_weeks_left == 0 else ""})'
                            for d in data
                            if d['team_id'] != team_id
                               and d['wins'] == seed_plus_one_wins
                        ])
                        clinch_over_teams_wo_pts = ','.join([
                            f'{d["team_id"]}'
                            for d in data
                            if d['team_id'] != team_id
                               and d['wins'] == seed_plus_one_wins
                        ])
                        row = [team_id, clinch_type, wins,
                               clinch_over_teams_w_pts if clinch_weeks_left == 0 else clinch_over_teams_wo_pts]
                        return row
            else:
                # if team is behind seed, need to clear all teams between them and seed
                team_idx = [i for i, data in enumerate(data) if team_id == data['team_id']][0]
                seed_to_team = data[(seed-1):team_idx]
                for team_to_clear in seed_to_team:
                    seed_wins = team_to_clear['wins']
                    for wins in range(3):
                        wb_added = wins / 2
                        new_wb = ((data_tm['wins'] - seed_wins) / 2) + wb_added
                        if new_wb > clinch_weeks_left:
                            clinch_over_teams_w_pts = ','.join([
                                f'{d["team_id"]} ({round(d["points"] - data_tm["points"], 2) if clinch_weeks_left == 0 else ""})'
                                for d in data
                                if d['team_id'] != team_id
                                   and d['wins'] == seed_wins
                            ])
                            clinch_over_teams_wo_pts = ','.join([
                                f'{d["team_id"]}'
                                for d in data
                                if d['team_id'] != team_id
                                   and d['wins'] == seed_wins
                            ])
                            row = [team_id, clinch_type, wins, clinch_over_teams_w_pts if clinch_weeks_left == 0 else clinch_over_teams_wo_pts]
                            return row

    def _elim_scenarios(self,
                        team_id: int,
                        seed: int) -> list:
        """
        Calculate elimination scenarios for the current matchup week
        :param team_id: Team display name to calculate elimination scenarios for
        :param seed: Seed to calculate scenarios for (2=BYE week, 5=playoffs by wins)
        :returns: List of team, scenario (bye or playoffs), wins needed, and team(s) to be eliminated by
        """
        elim_type = 'Bye' if seed == 2 else 'Top 5'
        clinch_weeks_left = self.league_settings.regular_season_end - self.week
        data = sorted(self.format_standings(), key=lambda x: (x['wins'], x['points']), reverse=True)
        data_tm = [d for d in data if d['team_id'] == team_id][0]
        clinched = True if data_tm[f'wb{seed}'] == 'c' else False
        eliminated = True if data_tm[f'wb{seed}'] == 'x' else False

        if not (clinched or eliminated):
            if data_tm['seed'] > seed:
                # if team is outside seed, eliminated if all teams tied with seed clear them
                # get seed team and any teams tied
                seed_wins = data[seed-1]['wins']
                all_seed_data = [d for d in data if d['wins'] == seed_wins]
                for _ in all_seed_data:
                    for wins in reversed(range(-2, 3)):
                        wb_taken = wins / 2
                        new_wb = ((seed_wins - data_tm['wins']) / 2) - wb_taken
                        if new_wb > clinch_weeks_left:
                            elim_by_teams_w_pts = ','.join([
                                f'{d["team_id"]} ({round(d["points"] - data_tm["points"], 2) if clinch_weeks_left == 0 else ""})'
                                for d in data
                                if d['team_id'] != team_id
                                   and d['wins'] == seed_wins
                            ])
                            elim_by_teams_wo_pts = ','.join([
                                f'{d["team_id"]}'
                                for d in data
                                if d['team_id'] != team_id
                                   and d['wins'] == seed_wins
                            ])
                            row = [team_id, elim_type, wins, elim_by_teams_w_pts if clinch_weeks_left == 0 else elim_by_teams_wo_pts]
                            return row

            else:
                # if team is seed or better, need all teams between them and teams tied with seed+1 to clear them
                team_idx = [i for i, data in enumerate(data) if team_id == data['team_id']][0]
                team_to_seed = data[(team_idx+1):(seed+1)]
                for team_to_clear in team_to_seed:
                    seed_wins = team_to_clear['wins']
                    for wins in range(-2, 3):
                        wb_taken = wins / 2
                        new_wb = ((data_tm['wins'] - seed_wins) / 2) + wb_taken
                        if new_wb > clinch_weeks_left:
                            elim_by_teams_w_pts = ','.join([
                                f'{d["team_id"]} ({round(d["points"] - data_tm["points"], 2) if clinch_weeks_left == 0 else ""})'
                                for d in data
                                if d['team_id'] != team_id
                                   and d['wins'] == seed_wins
                            ])
                            elim_by_teams_wo_pts = ','.join([
                                f'{d["team_id"]}'
                                for d in data
                                if d['team_id'] != team_id
                                   and d['wins'] == seed_wins
                            ])
                            row = [team_id, elim_type, wins, elim_by_teams_w_pts if clinch_weeks_left == 0 else elim_by_teams_wo_pts]
                            return row

    @staticmethod
    def format_prob(p):
        if 0 < p < 0.001:
            return "<0.1%"
        elif .999 < p < 1:
            return ">99.9%"
        else:
            return f"{p*100:.1f}%"

    def format_standings(self) -> list[dict] | None:
        """
        Create standings table for Flask UI
        - 2018-2021: 4 team playoffs by record
        - 2022-present: 6 team playoffs, top 5 by record, 6th seed by most points of remaining teams
        """
        n_playoff_teams = self.league_settings.playoff_teams
        as_of_week = self.league_settings.as_of_week
        standings = []
        for team_id in self.team_settings.team_ids:
            # standings data for each team
            team_results = {w: tr for w, tr in self.matchups[team_id].items() if w <= as_of_week}

            m_wins = sum(d.matchup_result.value for d in team_results.values())
            m_losses = as_of_week - m_wins
            m_record = f'{int(m_wins)}-{int(m_losses)}'

            th_wins = sum(d.tophalf_result.value for d in team_results.values())
            th_losses = as_of_week - th_wins
            th_record = f'{int(th_wins)}-{int(th_losses)}'

            ov_wins = m_wins + th_wins
            ov_losses = m_losses + th_losses
            ov_record = f'{int(ov_wins)}-{int(ov_losses)}'

            try:
                win_pct = f'{(ov_wins / (as_of_week*2)):.3f}'
            except ZeroDivisionError:  # NFL preseason/opening week
                win_pct = '0.000'
            total_points = round(sum(d.team_score for d in team_results.values()), 2)

            standings.append(
                {
                    'team_id': team_id,
                    'record': ov_record,
                    'wins': ov_wins,
                    'win_pct': win_pct,
                    'matchup': m_record,
                    'tophalf': th_record,
                    'points': total_points
                }
            )

        standings = sorted(standings, key=lambda x: (x['wins'], x['points']), reverse=True)
        if self.season >= 2022:  # wild card used after 2021
            final_order = []

            # top by wins, points
            top = [s['team_id'] for s in standings][:n_playoff_teams-1]
            final_order.extend(top)

            # wild card by points
            wc = [s['team_id'] for s in sorted(standings, key=lambda x: (x['points']), reverse=True) if s['team_id'] not in top][0]
            final_order.extend([wc])

            # rest by wins, points
            bottom = [s['team_id'] for s in standings if s['team_id'] not in final_order]
            final_order.extend(bottom)

            by_team = {s['team_id']: s for s in standings}
            standings = [by_team[tid] for tid in final_order if tid in by_team]

            for i, row in enumerate(standings, start=1):
                row['seed'] = i
                row['points_disp'] = f'{row['points']:,.2f}'
                row['wb2'] = self._weeks_back((row['wins'] - standings[1]['wins']) / 2)
                row['wb5'] = self._weeks_back((row['wins'] - standings[4]['wins']) / 2)
                row['pb6'] = self._format_points_back((row['points'] - standings[5]['points']))
                row['bye_magic'] = (
                    (self.league_settings.regular_season_end * 2) + 1
                    - standings[1]['wins']
                    - ((self.league_settings.as_of_week * 2) - row['wins'])
                )
                row['po_magic'] = (
                    (self.league_settings.regular_season_end * 2) + 1
                    - standings[4]['wins']
                    - ((self.league_settings.as_of_week * 2) - row['wins'])
                )
                row['bye_magic_disp'] = (
                    '-' if row['bye_magic'] <= 0
                           or row['bye_magic'] >= self.league_settings.as_of_week-1
                    else f'{int(row['bye_magic'])}'
                )
                row['po_magic_disp'] = (
                    '-' if row['po_magic'] <= 0
                           or row['po_magic'] >= self.league_settings.as_of_week-1
                    else f'{int(row['po_magic'])}'
                )
        return standings

    def get_playoff_scenarios(self, id_map: dict):
        """
        Formatter for clinching and elimination scenarios for the current matchup week
        """
        standings = self.format_standings()
        bye_clinches = self.playoff_scenarios.get_new_clinches(seed=2)
        po_clinches = self.playoff_scenarios.get_new_clinches(seed=5)
        clinch_rows = []
        elim_rows = []
        for team in standings:
            if team['team_id'] in bye_clinches:
                team_bye = bye_clinches[team['team_id']]

                if team_bye['clinched']:
                    bye_scen = self._clinch_scenarios(team_id=team['team_id'], seed=2)
                    bye_scen.extend([self.format_prob(team_bye['p_clinch'])])
                    bye_scen[0] = id_map[bye_scen[0]]
                    teams = bye_scen[3].split(',')
                    put_back = []
                    for t in teams:
                        if '(' in t:
                            left, right = t.split('(')
                            t = id_map[int(left.strip())] + f' ({right}'
                        else:
                            t = ','.join(id_map[int(t)] for t in t.split(','))
                        put_back.append(t)
                    bye_scen[3] = ', '.join(put_back)
                    clinch_rows.append(bye_scen)

                if team_bye['eliminated']:
                    bye_scen = self._elim_scenarios(team_id=team['team_id'], seed=2)
                    bye_scen.extend([self.format_prob(team_bye['p_elim'])])
                    bye_scen[0] = id_map[bye_scen[0]]
                    teams = bye_scen[3].split(',')
                    put_back = []
                    for t in teams:
                        if '(' in t:
                            left, right = t.split('(')
                            t = id_map[int(left.strip())] + f' ({right}'
                        else:
                            t = ','.join(id_map[int(t)] for t in t.split(','))
                        put_back.append(t)
                    bye_scen[3] = ', '.join(put_back)
                    elim_rows.append(bye_scen)

            if team['team_id'] in po_clinches:
                team_po = po_clinches[team['team_id']]

                if team_po['clinched']:
                    po_scen = self._clinch_scenarios(team_id=team['team_id'], seed=5)
                    po_scen.extend([self.format_prob(team_po['p_clinch'])])
                    po_scen[0] = id_map[po_scen[0]]
                    teams = po_scen[3].split(',')
                    put_back = []
                    for t in teams:
                        if '(' in t:
                            left, right = t.split('(')
                            t = id_map[int(left.strip())] + f' ({right}'
                        else:
                            t = ','.join(id_map[int(t)] for t in t.split(','))
                        put_back.append(t)
                    po_scen[3] = ', '.join(put_back)
                    clinch_rows.append(po_scen)

                if team_po['eliminated']:
                    po_scen = self._elim_scenarios(team_id=team['team_id'], seed=5)
                    po_scen.extend([self.format_prob(team_po['p_elim'])])
                    po_scen[0] = id_map[po_scen[0]]
                    teams = po_scen[3].split(',')
                    put_back = []
                    for t in teams:
                        if '(' in t:
                            left, right = t.split('(')
                            t = id_map[int(left.strip())] + f' ({right}'
                        else:
                            t = ','.join(id_map[int(t)] for t in t.split(','))
                        put_back.append(t)
                    po_scen[3] = ', '.join(put_back)
                    elim_rows.append(po_scen)


        clinch_rows.sort(key=lambda x: (x[0], x[1]))
        elim_rows.sort(key=lambda x: (x[0], x[1]))
        return {
            'clinches': clinch_rows,
            'elims': elim_rows
        }

    def final_week_playoff_scenarios(self, seed: int):
        from scripts.utils.database import Database
        db = Database()
        sim_ranks = db.retrieve_data(table='season_sim_ranks', how='week', season=self.season, week=self.week)
        if sim_ranks.empty:
            pass  # run season simulation

        standings = self.format_standings()
        seed_wins = [t for t in standings if t['seed'] == seed][0]['wins']

        team_probs = sim_ranks[sim_ranks.ranks <= seed].groupby('team').p.sum()
        team_probs = team_probs[team_probs < 1]
        for team, p in team_probs.items():
            tm_data = [t for t in standings if t['team_id'] == team][0]
            net_wins = seed_wins - tm_data['wins']

