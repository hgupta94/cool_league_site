from scripts.api.DataLoader import DataLoader
from scripts.api.Teams import Teams
from scripts.utils.constants import TEAM_IDS, POSITION_MAP
import pandas as pd

draft_df = pd.DataFrame()
for season in range (2023, 2025):
    print(season)
    data = DataLoader(season)
    teams = Teams(data)
    draft = data.draft()
    players = data.players_info()
    players_wl = data.players_wl()
    players_card = data.players_card()

    players_dict = {}
    rank_ov = 1
    rank_pos = {
        'QB': 1,
        'RB': 1,
        'WR': 1,
        'TE': 1,
        'DST': 1
    }
    for player in players['players']:
        full_name = player['player']['fullName']

        for pos in player['player']['eligibleSlots']:
            if pos in POSITION_MAP.keys():
                position = POSITION_MAP[pos]
        ppr_value = player['player']['draftRanksByRankType']['PPR']['auctionValue']
        standard_value = 0
        try:
            standard_value = player['player']['draftRanksByRankType']['STANDARD']['auctionValue']
        except KeyError:
            standard_value = 0

        # get overall and position ranks
        pl_rank_ov = rank_ov
        rank_ov +=1
        pl_rank_pos = rank_pos[position]
        rank_pos[position] += 1

        projection_total = 0
        projection_ppg = 0
        for stat in player['player']['stats']:
            if (stat['seasonId'] == season) and (stat['statSourceId'] == 1) and (stat['statSplitTypeId'] == 0):
                projection_total = stat['appliedTotal']
                projection_ppg = stat['appliedAverage']
        players_dict[player['id']] = {
            'name': full_name,
            'position': position,
            'rank_ov': pl_rank_ov,
            'rank_pos': pl_rank_pos,
            'ppr_value': ppr_value,
            'standard_value': standard_value,
            'projection_total': projection_total,
            'projection_ppg': projection_ppg
        }

    rows = []
    for p in draft['draftDetail']['picks']:
        player_id = p['playerId']
        player_name = players_dict[player_id]['name']
        position = players_dict[player_id]['position']
        projection = players_dict[player_id]['projection_total']
        projection_ppg = players_dict[player_id]['projection_ppg']
        ppr_value = players_dict[player_id]['ppr_value']
        standard_value = players_dict[player_id]['standard_value']

        pick = p['overallPickNumber']
        winning_team_id = p['teamId']
        winning_team = TEAM_IDS[teams.teamid_to_primowner[winning_team_id]]['name']['display']
        nom_team_id = p['nominatingTeamId']
        nom_team = TEAM_IDS[teams.teamid_to_primowner[nom_team_id]]['name']['display']
        bid = p['bidAmount']
        rows.append([season, pick, nom_team, winning_team, bid, player_id, player_name, position, projection, projection_ppg, ppr_value, standard_value])

    cols = ['season', 'pick', 'nominating_team', 'winning_team', 'bid', 'player_id', 'player', 'position', 'proj_ssn', 'proj_ppg', 'ppr_value', 'standard_value']
    temp = pd.DataFrame(rows, columns=cols).sort_values(['winning_team', 'bid'], ascending=[True, False])
    temp['team_pick'] = temp.groupby('winning_team').cumcount() + 1
    temp['perc_of_budget'] = temp.bid / 200
    temp['cumul_spend'] = temp.groupby('winning_team').bid.cumsum()
    temp['cumul_perc_of_budget'] = temp.groupby('winning_team').perc_of_budget.cumsum()
    temp['id'] = temp.winning_team + '_' + temp.season.astype(str)
    draft_df = pd.concat([draft_df, temp])


import matplotlib.pyplot as plt
draft_df.groupby('id').plot(x='team_pick', y='perc_of_budget', ylim=[0,0.5], kind='line', ax=plt.gca())
plt.show()
