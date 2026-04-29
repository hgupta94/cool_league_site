from scripts.api.DataLoader import DataLoader
from scripts.utils.database import Database
from scripts.api.Settings import Params
from scripts.api.Teams import Teams
from scripts.utils import constants

import math
from collections import defaultdict
from itertools import product, combinations


def teamid_to_display(teamid):
    return constants.TEAM_IDS[teams.teamid_to_primowner[teamid]]['name']['display']


def sort_standings(standings: dict[str, float]):
    return sorted(standings, key=lambda x: (x['wins'], x['score']), reverse=True)


def get_teams(standings: dict[str, float], seed: int, weeks_left: int):
    clinched = {}
    eliminated = {}
    for tm in standings:
        clinched[tm['team']] = tm['wins'] - standings[seed]['wins'] > weeks_left * 2
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
matchups = [(teamid_to_display(m['home']['teamId']), teamid_to_display(m['away']['teamId'])) for m in data.matchups()['schedule'] if m['matchupPeriodId'] == week]
standings_df = Database(table='matchups', season=season, week=week).retrieve_data(how='season')
standings_df['wins'] = standings_df.matchup_result + standings_df.tophalf_result
standings = standings_df[['team', 'score', 'wins']].groupby('team').sum().reset_index()
standings = sort_standings(standings.to_dict(orient='records'))

betting_table = standings_df = Database(table='betting_table', season=season, week=week).retrieve_data(how='week')[['team', 'p_win', 'p_tophalf']]
betting_table = betting_table.to_dict(orient='records')

team_names = set(standings_df.team)
h2h_outcomes = list(product([0, 1], repeat=len(matchups)))
median_outcomes = list(combinations(team_names, len(team_names)//2))
already_clinched, already_elim = get_teams(standings=standings, seed=5, weeks_left=weeks_left)



# get all scenarios
# 2**n_teams = 32 h2h scenarios
# 10 choose 5 = 252 tophalf scenarios
# 32 * 252 = 8064 total scenarios
def get_scenarios(h2h_outcomes, median_outcomes):
    # TODO: keep tophalf winning teams in final results
    seen = set()
    counts = defaultdict(int)
    scenarios = []
    for h2h in h2h_outcomes:
        for median_winners in median_outcomes:
            week_wins = {name: 0 for name in team_names}

            # H2H results
            for i, (home, away) in enumerate(matchups):
                if h2h[i] == 0:
                    week_wins[home] += 1
                else:
                    week_wins[away] += 1

            # Median results — exactly half the teams get +1
            for name in median_winners:
                week_wins[name] += 1

            key = tuple(week_wins[name] for name in team_names)
            counts[key] += 1
            if key not in seen:
                seen.add(key)
                scenarios.append(week_wins)
    return [
        ({name: key[i] for i, name in enumerate(team_names)}, count)
        for key, count in counts.items()
    ]


# calculate all clinch/elim results
scenarios = get_scenarios(h2h_outcomes, median_outcomes)
for i, (s, n) in enumerate(scenarios):
    s_probs = []
    for team, wins in s.items():
        tm_odds = [o for o in betting_table if o['team'] == team][0]
        if wins == 2:
            p = tm_odds['p_win'] * tm_odds['p_tophalf']
        if wins == 0:
            p = (1 - tm_odds['p_win']) * (1 - tm_odds['p_tophalf'])
        if wins == 1:
            p = (tm_odds['p_win'] * (1 - tm_odds['p_tophalf'])) + ((1 - tm_odds['p_win']) * tm_odds['p_tophalf'])
        s_probs.append(p)

    s['p'] = math.prod(s_probs) * n


winners = ('Aaro', 'Adit', 'Aide', 'Aksh', 'Arju')
losers = ('Ayaz', 'Char', 'Hirs', 'Nick', 'Varu')
p_median_map = {k: v for k, v in betting_table[0].items() if k!='p_win'}

def grouping_weight(winners, losers):
    w = 1.0
    for t in winners:
        w *= [b for b in betting_table if b['team'] == t][0]['p_tophalf']
    for t in losers:
        w *= (1 - [b for b in betting_table if b['team'] == t][0]['p_tophalf'])
    return w

for s in scenarios:

    total_weight = sum(
        grouping_weight(group, [t for t in team_names if t not in group])
        for group in combinations(team_names, len(team_names)//2)
    )
    this_weight = grouping_weight(winners, losers)
    this_weight / total_weight

results = {
    name: {'clinched': 0, 'eliminated': 0, 'clinch_scenarios': [], 'elim_scenarios': []}
    for name in team_names
}
for week_wins, n in scenarios:
    new_standings = []
    for team in standings:
        name = team['team']
        new_wins = team['wins'] + week_wins[name]
        new_standings.append({
            'team': name,
            'wins': new_wins,
            'score': round(team['score'], 2),  # points don't change for scenario purposes
        })

    new_clinched, new_elim = get_teams(standings=sort_standings(new_standings), seed=5, weeks_left=weeks_left-1)
    for tm in team_names:
        if tm in new_clinched:
            results[tm]['clinched'] += n
            results[tm]['clinch_scenarios'].append(week_wins)
        if tm in new_elim:
            results[tm]['eliminated'] += n
            results[tm]['elim_scenarios'].append(week_wins)


for team, res in results.items():
    wins_needed = {t:[] for t in team_names}
    if res['elim_scenarios']:
        print(team, 'elim_p', sum(elim['p'] for elim in res['elim_scenarios'])/sum(s[0]['p'] for s in scenarios))

    if res['clinch_scenarios']:
        print(team, 'clinch_p', sum(cl['p'] for cl in res['clinch_scenarios'])/sum(s[0]['p'] for s in scenarios))





# describe a scenario
parts = []
for home, away in matchups:
    h2h_winner = home if week_wins[home] > week_wins[away] else away
    parts.append(f"{h2h_winner} beats {away if h2h_winner == home else home}")  # handle ties in week_wins (both beat/lost median equally)
median_winners = [name for name, w in week_wins.items() if w == 2]
median_losers  = [name for name, w in week_wins.items() if w == 0]
parts.append(f"tophalf winners: {', '.join(median_winners) or 'none'}")
final = " | ".join(parts)


# get a full summary
for team in standings:
    name = team['team']
    r = results[name]
    makes = r['clinched']
    misses = r['eliminated']

    print(f"{name} (currently {int(team['wins'])}-{(week*2)-int(team['wins'])}, {team['score']} pts)")

    pct = 100 * makes / len(scenarios)
    print(f"Clinches BYE in {makes}/{len(scenarios)} scenarios ({pct:.1f}%)")
    print()

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

get_magic_number(standings=standings, team='Ayaz', spots=2)