from scripts.api.DataLoader import DataLoader


class Teams:
    def __init__(self):
        teams = DataLoader().teams()

        self.primowner_to_teamid = {}
        self.teamid_to_primowner = {}
        for team in teams['teams']:
            o_id = team['primaryOwner']
            t_id = team['id']
            self.primowner_to_teamid[o_id] = t_id
            self.teamid_to_primowner[t_id] = o_id

    def schedule(self):
        pass