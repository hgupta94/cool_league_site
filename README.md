# [Link to website](https://www.thechillff.com/)

A website for my personal Fantasy Football league, created using Python and Flask. Includes a power ranking, simulation results, what-if record scenarios, and team efficiency, and historical recordkeeping.

# Standings
Tracks standings tailored to our league rules: two results per week (matchup and median), top 5 by wins make the playoffs, top 2 by wins earn a bye, and last (sixth) playoff seed is a wild card determined by points.

## Playoff Scenarios
Playoff clinching/elimination scenarios are also tracked. For the upcoming league week, every possible matchup and tophalf winners are calculated and scenarios that lead to a team clinching or being eliminated are counted. Current week simulations are used to determine each team's probability of clinching/elmination.

# Power Ranking
A combination of five factors are used to calcuate a weekly Power Score for each team, which is then normalized so that 100 is an average team.
1. **Season Performance**: Total points scored on the season.
2. **Recent Performance**: Total points scored over the past three weeks.
3. **Consistency**: How consistent each team is at scoring, weighted by average points per week so consistent low scoring teams are penalized more than consistent high scoring teams.
4. **Manager**: How efficient each manager is at setting their lineups.
5. **Luck**: Actual weekly result (win/loss) compared to how many teams you outscored each week. 

# Simulations
A monte carlo simulation is ran at the individual player level to simulate current week matchups, final standings, and playoff outcomes.
## Current Week
Current week matchups are simulated 100,000 times. The following steps are taken to arrive at the final outcome:
1. Each team's optimal lineup is selected based on aggregate projections from FantasyPros.
2. Player scores are then drawn from a gamma distribution, using roster data from 2022-2025 to determine the relevant parameters by position.

A summarized betting table is created displaying the projected score and odds of each team winning and being the highest and lowest scorer.

## Regular Season and Playoffs
The regular season and playoffs are also simulated 100,000 times.
1. Optimal lineups are selected using rest-of-season projections from ESPN. Bye weeks and injuries are taken into account. If a lineup slot cannot be filled, an average of the top 3 current free agents are used.
2. Player scores are simulated using a gamma distribution.

Each remaining regular season matchup is simulated and standings are calculated using current league rules. Each playoff week is simulated until a champion is determined. Each team's regular season final rank, win, and point totals are counted, along with the number of playoff and finals appearances and the number of first, second, and third place finishes. Expected payout is calculated based on our league rules.

# What If Scenarios
## Record vs League
Rather than a matchup-based schedule, this scenario aims to see how each team would fare if they played every team each week. 

## Schedule Switcher
Unlike the NFL schedule, fantasy football schedules are randomly generated. As a result, luck plays a large part in every team's success (or failure). Score the second most points and lose? Tough luck. Score the second *least* points and win? Well, a win's a win! This table shows what each team's record would be if they instead had another team's schedule.

# Team Efficiencies
A perfect lineup is tough to achieve. This page displays each team's overall lineup efficiency.
