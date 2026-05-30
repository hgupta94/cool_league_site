from scripts.api.models.schedule import Matchup
from scripts.utils.utils import teamid_to_name
from scripts.api.dataloader import DataLoader
from scripts.utils.database import Database
from scripts.api.models.schedule import (
    Matchup,
    TeamSchedule
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
import pandas as pd
import difflib


class Simulation:
    def __init__(self, dataloader: DataLoader):
        self.league_settings = LeagueSettings(dataloader=dataloader)
        self.roster_settings = RosterSettings(dataloader=dataloader)
        self.team_settings = TeamSettings(dataloader=dataloader)

        ctx = ParseContext(view=PlayerView.WEEK)
        players_obj = dataloader.players_info()['players']
        teams_obj = dataloader.teams()
        rosters_obj = dataloader.rosters()
        self.players = Player.get_players(obj=players_obj, ctx=ctx)
        self.teams = Team.get_teams(obj=teams_obj, roster_obj=rosters_obj, ctx=ctx)
        self.matchups = Matchup.get_season_matchups(params=self.league_settings)
        self.results = TeamSchedule.get_all_team_schedules(week=constants.WEEK)

    def _match_player_to_espn(
            self,
            the_player: str,
    ) -> int | None:
        """
        Matches a name to ESPN's database and returns a player ID

        Args:
            the_player: a player's full name, position, and team abbreviation (ex: Full Name|Pos|TM)

        Returns:
            matching ESPN player ID
        """

        player_lookup = []
        for p in self.players:
            try:
                pl_name = p['player']['fullName']
                pl_pos = constants.POSITION_MAP[list(set(constants.POSITION_MAP) & set(p['player']['eligibleSlots']))[0]]
                pl_team = constants.NFL_TEAM_MAP[p['player']['proTeamId']]
                pl_lookup = f"{pl_name}|{pl_pos}|{pl_team}"
            except (KeyError, IndexError):
                continue
            player_lookup.append(pl_lookup)

        calc = [difflib.SequenceMatcher(None, the_player, m).ratio() for m in player_lookup]
        if max(calc) > 0.8:
            match_idx = calc.index(max(calc))
            return self.players[match_idx]['id']
        else:
            return None


    def get_week_projections(self) -> pd.DataFrame:
        """Return Fantasy Pros projections for all positions"""
        projections = pd.DataFrame()
        for pos in self.roster_settings.positions:
            url = f"https://www.fantasypros.com/nfl/projections/{pos}.php?scoring=HALF&week={self.league_settings.current_week}"
            df = pd.read_html(url)[0]

            # drop multi index column
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel()

            df['POSITION'] = pos.upper()
            try:
                df = df[['Player', 'FPTS', 'REC', 'POSITION']]
            except:
                df = df[['Player', 'FPTS', 'POSITION']]
                df['REC'] = 0

            # remove team from player name
            if pos != 'dst':
                df['TEAM'] = df.Player.str[-3:].str.strip()
                df['Player'] = df['Player'].str[:-3]
                df['Player'] = df['Player'].str.rstrip()

            if pos == 'dst':
                df['Player'] = df['Player'].str.split().str[-1] + ' DST'
                df['TEAM'] = ''

            projections = pd.concat([projections, df])

        projections['season'] = constants.SEASON
        projections['week'] = self.league_settings.current_week
        projections.columns = [c.lower() for c in projections.columns]

        qb_mask = (projections.position == 'QB') & (projections.fpts > 10)
        rb_mask = (projections.position == 'RB') & (projections.fpts > 5)
        wr_mask = (projections.position == 'WR') & (projections.fpts > 5)
        te_mask = (projections.position == 'TE') & (projections.fpts > 3)
        dst_mask = (projections.position == 'DST') & (projections.fpts > 3)
        projections = projections[qb_mask | rb_mask | wr_mask | te_mask | dst_mask]

        # match player to ESPN
        projections['match_on'] = projections.player + '|' + projections.position + '|' + projections.team
        projections['id'] = (projections.player.str.replace(r'[^a-zA-Z0-9]', '', regex=True)
                             + '_' + projections.season.astype(str)
                             + '_' + projections.week.astype(str).str.zfill(2))

        projections['espn_id'] = projections.apply(
            lambda x: self._match_player_to_espn(x['match_on']), axis=1
        ).astype('Int64')

        return projections[~projections.espn_id.isnull()]


dataloader = DataLoader(week=constants.WEEK)
Simulation(dataloader).get_week_projections()