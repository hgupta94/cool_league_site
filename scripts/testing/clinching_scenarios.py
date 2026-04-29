from scripts.api.DataLoader import DataLoader
from scripts.utils.database import Database
from scripts.api.Settings import Params
from scripts.api.Teams import Teams
from scripts.utils import constants

import math
from collections import defaultdict
from itertools import product, combinations


def teamid_to_display(teams: Teams, teamid: int):
    return constants.TEAM_IDS[teams.teamid_to_primowner[teamid]]['name']['display']


def sort_standings(standings: dict[str, float]):
    return sorted(standings, key=lambda x: (x['wins'], x['score']), reverse=True)


def get_teams(standings: dict[str, float], seed: int, weeks_left: int):
    """Calculate which teams clinched or are eliminated"""
    clinched = {}
    eliminated = {}
    for tm in standings:
        clinched[tm['team']] = tm['wins'] - standings[seed]['wins'] > weeks_left * 2  # 2 results per week
        eliminated[tm['team']] = standings[seed-1]['wins'] - tm['wins'] > weeks_left * 2

    clinched_tms = [k for k, v in clinched.items() if v]
    eliminated_tms = [k for k, v in eliminated.items() if v]
    return clinched_tms, eliminated_tms


season = 2025
data = DataLoader(season)
params = Params(data)
teams = Teams(data)

week = 13  # just finished previous week
weeks_left = params.regular_season_end - week + 1
standings_df = Database(table='matchups', season=season, week=week).retrieve_data(how='season')
standings_df['wins'] = standings_df.matchup_result + standings_df.tophalf_result
standings = standings_df[['team', 'score', 'wins']].groupby('team').sum().reset_index()
standings = sort_standings(standings.to_dict(orient='records'))

betting_table = standings_df = Database(table='betting_table', season=season, week=week).retrieve_data(how='week')
betting_table = betting_table[betting_table.id.str.contains('Thu')][['team', 'p_win', 'p_tophalf']].to_dict(orient='records')
already_clinched, already_elim = get_teams(standings=standings, seed=5, weeks_left=weeks_left)





# get all scenarios
# 2**n_teams = 32 h2h scenarios
# 10 choose 5 = 252 tophalf scenarios for 10 teams
# 32 * 252 = 8064 total scenarios
def get_scenarios(team_names, matchups):
    """Calculate all possible combinations of matchup and tophalf wins"""
    h2h_outcomes = list(product([0, 1], repeat=len(matchups)))
    median_outcomes = list(combinations(team_names, len(team_names) // 2))
    all_scenarios = []

    for h2h in h2h_outcomes:
        for med_winners in median_outcomes:
            week_winners = {
                'matchup': {name: 0 for name in team_names},
                'tophalf': {name: 0 for name in team_names},
            }

            # H2H results
            for i, (hm, aw) in enumerate(matchups):
                if h2h[i] == 0:
                    week_winners['matchup'][hm] += 1
                else:
                    week_winners['matchup'][aw] += 1

            # Median results — exactly half the teams get +1
            for name in med_winners:
                week_winners['tophalf'][name] += 1

            all_scenarios.append(week_winners)
    return all_scenarios


team_names = [x['name']['display'] for x in params.team_map.values() if x['active']]
matchups = [
    (
        teamid_to_display(teams=teams, teamid=m['home']['teamId']),
        teamid_to_display(teams=teams, teamid=m['away']['teamId'])
    ) for m in data.matchups()['schedule'] if m['matchupPeriodId'] == week
]
scenarios = get_scenarios(team_names=team_names, matchups=matchups)





### calculate all clinch/elim results and find the probability of each scenario occurring
def matchup_weight(scenario, betting_table):
    """Calculate the likelihood that a set of matchup winners occurs
    Only need to find the product of the winners"""

    matchup_set_prob = 1.0
    for team, result in scenario['matchup'].items():
        if result == 1:
            winner_prob = [o for o in betting_table if o['team'] == team][0]['p_win']
            matchup_set_prob *= winner_prob
    return matchup_set_prob


def normalized_tophalf_weight(scenario, betting_table):
    """Calculate the likelihood that the set of tophalf winners occurs
    Need to find the joint probability of winners and losers and normalize"""

    tophalf_outcomes = combinations(team_names, len(team_names)//2)
    th_winners = tuple([t for t, r in scenario['tophalf'].items() if r == 1])
    th_losers = tuple([t for t, r in scenario['tophalf'].items() if r == 0])

    def grouping_weight(winners, losers):
        tophalf_set_prob = 1.0
        for t in winners:
            tophalf_set_prob *= [b for b in betting_table if b['team'] == t][0]['p_tophalf']
        for t in losers:
            tophalf_set_prob *= (1 - [b for b in betting_table if b['team'] == t][0]['p_tophalf'])
        return tophalf_set_prob

    total_weight = sum(
        grouping_weight(group, [t for t in team_names if t not in group])
        for group in tophalf_outcomes
    )
    this_weight = grouping_weight(winners=th_winners, losers=th_losers)
    return this_weight / total_weight if total_weight > 0 else 0.0


# assign probability to each scenario
for s in scenarios:
    matchup_prob = matchup_weight(s, betting_table)
    tophalf_prob = normalized_tophalf_weight(s, betting_table)
    s['p'] = matchup_prob * tophalf_prob

# clinching/elimination scenarios and probabilities
results = {
    name: {'clinched': 0, 'eliminated': 0, 'p_clinch': 0, 'p_elim': 0, 'clinch_scenarios': [], 'elim_scenarios': []}
    for name in team_names
}
for s in scenarios:
    matchup_winners = [t for t, r, in s['matchup'].items() if r == 1]
    tophalf_winners = [t for t, r, in s['tophalf'].items() if r == 1]
    new_standings = []
    for team in standings:
        name = team['team']
        new_wins = team['wins'] + s['matchup'][team['team']] + s['tophalf'][team['team']]
        new_standings.append({
            'team': name,
            'wins': new_wins,
            'score': round(team['score'], 2),  # points don't change for scenario purposes
        })

    new_clinched, new_elim = get_teams(standings=sort_standings(new_standings), seed=5, weeks_left=weeks_left-1)
    for tm in team_names:
        if tm in new_clinched:
            results[tm]['clinched'] += 1
            results[tm]['p_clinch'] += s['p']
            results[tm]['clinch_scenarios'].append(s)
        if tm in new_elim:
            results[tm]['eliminated'] += 1
            results[tm]['p_elim'] += s['p']
            results[tm]['elim_scenarios'].append(s)

for team, res in results.items():
    wins_needed = {t:[] for t in team_names}
    if res['eliminated']:
        print(f'{team} has a {round(res['p_elim'] * 100, 1)}% chance of being ELIMINATED')

    if res['clinched']:
        print(f'{team} has a {round(res['p_clinch'] * 100, 1)}% chance of CLINCHING a playoff spot')





# describe a scenario
def describe_scenario(scenario: dict) -> str:
    parts = []
    m_winners = [t for t, r, in scenario['matchup'].items() if r == 1]
    th_winners = [t for t, r, in scenario['tophalf'].items() if r == 1]
    for home, away in matchups:
        h2h_winner = home if home in m_winners else away
        parts.append(f"{h2h_winner} beats {away if h2h_winner == home else home}")  # handle ties in week_wins (both beat/lost median equally)
    parts.append(f"Top Half winners: {', '.join(th_winners) or 'none'}")
    final = "\n".join(parts)
    return final
print(describe_scenario(s))


# get a full summary
for team in standings:
    name = team['team']
    r = results[name]
    makes = r['clinched']
    misses = r['eliminated']
    print(f"{name} (currently {int(team['wins'])}-{(week*2)-int(team['wins'])}, {team['score']} pts)")

    pct = 100 * makes / len(scenarios)
    prob = r['p_clinch']
    print(f"Clinches BYE in {makes}/{len(scenarios)} scenarios ({pct:.1f}%) -- {prob*100:.1f}% probability")

    their_matchup = next(
        ((h, a) for h, a in matchups if name in (h, a))
    )
    opponent = their_matchup[1] if their_matchup[0] == name else their_matchup[0]


# calculate magic numbers
def get_magic_number(standings: list[dict], team: str, spots: int):
    _, already_elim = get_teams(standings=standings, seed=spots, weeks_left=weeks_left)
    is_elim = True if team in already_elim else False

    the_team = [s for s in standings if s['team'] == team][0]
    current_wins = int(the_team['wins'])
    best_case = int(current_wins + (weeks_left * 2))
    others_best = [int(t['wins']) + (weeks_left * 2) for t in standings if t['team'] != team]

    if is_elim:
        magic = None
    else:
        magic = weeks_left * 2  # default case need to win every game
        for w in range(current_wins, best_case + 1):
            teams_that_can_surpass = sum(1 for bc in others_best if bc > w)
            if teams_that_can_surpass < spots:
                magic = max(0, w - current_wins)  # additional wins needed
                break

    return magic

get_magic_number(standings=standings, team='Aide', spots=2)