from scripts.api.DataLoader import DataLoader
from scripts.api.Settings import Params


class Teams:
    def __init__(self):
        data = DataLoader()
        params = Params(data)
        teams = data.teams()
        matchups = data.matchups()

        self.m_dict = {}
        self.primowner_to_teamid = {}
        self.teamid_to_primowner = {}
        for team in teams['teams']:
            o_id = team['primaryOwner']
            t_id = team['id']
            self.primowner_to_teamid[o_id] = t_id
            self.teamid_to_primowner[t_id] = o_id

    def schedule(self, params, matchups):
        for tmid in params.teamid_to_primowner.keys():
            temp = {}
            opps = []
            for m in matchups['schedule']:
                if m['matchupPeriodId'] <= params.regular_season_end:
                    teams = [m['away']['teamId'], m['home']['teamId']]
                    if tmid in teams:
                        oppid = [t for t in teams if t != tmid][0]
                        opps.append(oppid)
            temp[tmid] = opps
            self.m_dict.update(temp)
        return self.m_dict
