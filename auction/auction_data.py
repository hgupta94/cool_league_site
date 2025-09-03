from scripts.api.DataLoader import DataLoader
from scripts.api.Teams import Teams
from scripts.utils.constants import TEAM_IDS, POSITION_MAP
import pandas as pd
import math


def get_draft_data(season):
    data = DataLoader(season)
    teams = Teams(data)
    draft = data.draft()
    players = data.players_info()

    players_dict = {}
    for pick in draft['draftDetail']['picks']:
        pick_number = pick['id']
        player_id = pick['playerId']
        the_player = [p for p in players['players'] if p['id'] == player_id][0]
        player_name = the_player['player']['fullName']
        ov_rank = the_player['player']['draftRanksByRankType']['PPR']['rank']

        bid_amt = pick['bidAmount']
        ppr_value = the_player['player']['draftRanksByRankType']['PPR']['auctionValue']
        avg_value = the_player['player']['ownership']['auctionValueAverage']

        # teams
        winning_team_id = pick['teamId']
        winning_team = TEAM_IDS[teams.teamid_to_primowner[winning_team_id]]['name']['first']
        nom_team_id = pick['nominatingTeamId']
        nom_team = TEAM_IDS[teams.teamid_to_primowner[nom_team_id]]['name']['first']

        for pos in the_player['player']['eligibleSlots']:
            # player position
            if pos in POSITION_MAP.keys():
                position = POSITION_MAP[pos]

        projection_total = 0
        projection_ppg = 0
        for stat in the_player['player']['stats']:
            if (stat['seasonId'] == season) and (stat['statSourceId'] == 1) and (stat['statSplitTypeId'] == 0):
                projection_total = stat['appliedTotal']
                projection_ppg = stat['appliedAverage']

        try:
            draft_value = (bid_amt - ((ppr_value + avg_value) / 2)) / math.log(projection_total)
        except ValueError:
            draft_value = 0

        players_dict[player_id] = {
            'pick_number': pick_number,
            'nominating_team': nom_team,
            'winning_team': winning_team,
            'name': player_name,
            'position': position,
            'rank_ov': ov_rank,
            'bid_amount': bid_amt,
            'ppr_value': ppr_value,
            'avg_value': avg_value,
            'projection_season': projection_total,
            'projection_ppg': projection_ppg,
            'draft_value': draft_value
        }

    return players_dict

    # return pd.DataFrame(players_dict).transpose()

    # cols = ['season', 'pick', 'nominating_team', 'winning_team', 'bid', 'player_id', 'player', 'position', 'proj_ssn', 'proj_ppg', 'ppr_value']
    # temp = pd.DataFrame(rows, columns=cols).sort_values(['winning_team', 'bid'], ascending=[True, False])
    # temp['team_pick'] = temp.groupby('winning_team').cumcount() + 1
    # temp['perc_of_budget'] = temp.bid / 200
    # temp['cumul_spend'] = temp.groupby('winning_team').bid.cumsum()
    # temp['cumul_perc_of_budget'] = temp.groupby('winning_team').perc_of_budget.cumsum()
    # temp['id'] = temp.winning_team + '_' + temp.season.astype(str)
    # draft_df = pd.concat([draft_df, temp])


data = get_draft_data(season=2025)
draft_df = pd.DataFrame(data).transpose()

# import matplotlib.pyplot as plt
# draft_df.groupby('id').plot(x='team_pick', y='perc_of_budget', ylim=[0,0.5], kind='line', ax=plt.gca())
# plt.show()
