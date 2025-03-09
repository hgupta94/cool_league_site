from scripts.utils import constants as const

import pandas as pd
import numpy as np


class Params:
    def __init__(self, data):
        settings = data.settings()
        matchups = data.matchups()

        # general settings
        self.league_size = settings['settings']['size']
        self.roster_size = sum(settings['settings']['rosterSettings']['lineupSlotCounts'].values())
        self.regular_season_end = settings['settings']['scheduleSettings']['matchupPeriodCount']
        self.current_week = settings['scoringPeriodId']
        self.as_of_week = self.current_week - 1
        self.playoff_teams = settings['settings']['scheduleSettings']['playoffTeamCount']
        self.playoff_matchup_length = settings['settings']['scheduleSettings']['playoffMatchupPeriodLength']
        self.has_bonus_win = 1 if settings['settings']['scoringSettings'].get('scoringEnhancementType') else 0
        has_ppr = [s['points'] for s in settings['settings']['scoringSettings']['scoringItems'] if s['statId'] == 53]
        self.ppr_type = 0 if not has_ppr else has_ppr[0]
        self.weeks_left = 0 if self.as_of_week > self.regular_season_end else self.regular_season_end - self.as_of_week
        self.slotcodes = const.SLOTCODES
        self.team_map = const.TEAM_IDS

        # roster construction
        self.lineup_slots = settings['settings']['rosterSettings']['lineupSlotCounts']
        self.lineup_slots_df = pd.DataFrame \
            .from_dict(self.lineup_slots, orient='index') \
            .rename(columns={0: 'limit'})
        self.lineup_slots_df['posID'] = self.lineup_slots_df.index.astype('int')
        self.lineup_slots_df = self.lineup_slots_df[self.lineup_slots_df.limit > 0]
        self.lineup_slots_df['pos'] = self.lineup_slots_df.replace({'posID': const.SLOTCODES}).posID
        self.position = self.lineup_slots_df.pos.str.lower().to_list()
        self.position = np.setdiff1d(self.position, ['bench', 'ir']).tolist()
        self.teams = list(self.primowner_to_teamid.keys())

        # schedules
        self.matchups_df = pd.DataFrame()
        for game in matchups['schedule']:
            if game['matchupPeriodId'] <= self.regular_season_end:
                week = game['matchupPeriodId']
                team1 = self.teamid_to_primowner[game['home']['teamId']]
                score1 = game['home']['totalPoints']
                team2 = self.teamid_to_primowner[game['away']['teamId']]
                score2 = game['away']['totalPoints']
                matchups = pd.DataFrame([[week, team1, score1, team2, score2]],
                                        columns=['week', 'team1_id', 'score1', 'team2_id', 'score2'])
                self.matchups_df = pd.concat([self.matchups_df, matchups])
        self.matchups_df['team1_result'] = np.where(self.matchups_df['score1'] > self.matchups_df['score2'], 1.0, 0.0)
        self.matchups_df['team2_result'] = np.where(self.matchups_df['score2'] > self.matchups_df['score1'], 1.0, 0.0)
        mask = (self.matchups_df.score1 == self.matchups_df.score2)\
               & (self.matchups_df.score1 > 0)\
               & (self.matchups_df.score2 > 0)  # Account for ties
        self.matchups_df.loc[mask, ['team1_result', 'team2_result']] = 0.5
        home = self.matchups_df.iloc[:, [0, 1, 2, 5]].rename(columns={
            'team1_id': 'team',
            'score1': 'score',
            'team1_result': 'result'
        })
        home['id'] = home['team'].astype(str) + home['week'].astype(str)
        away = self.matchups_df.iloc[:, [0, 3, 4, 6]].rename(columns={
            'team2_id': 'team',
            'score2': 'score',
            'team2_result': 'result'
        })
        away['id'] = away['team'].astype(str) + away['week'].astype(str)
        self.scores_df = pd.concat([home, away]).sort_values(['week', 'id']).drop('id', axis=1).reset_index(drop=True)
