from scripts.api.DataLoader import DataLoader
from scripts.utils import constants as const
import pandas as pd
import difflib


def get_week_projections(week):
    """Return current week's projections for all positions"""
    positions = ['qb', 'rb', 'wr', 'te', 'dst']

    projections = pd.DataFrame()
    for pos in positions:
        print(pos)
        url = f"https://www.fantasypros.com/nfl/projections/{pos}.php?scoring=HALF&week={week}"
        df = pd.read_html(url)[0]

        # drop multi index column
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel()

        df['POSITION'] = pos
        df = df[['Player', 'FPTS', 'POSITION']]

        # remove team from player name
        if pos != 'dst':
            df['TEAM'] = df.Player.str[-3:].str.strip()
            df['Player'] = df['Player'].str[:-3]
            df['Player'] = df['Player'].str.rstrip()

        if pos == 'dst':
            df['Player'] = df['Player'].str.split().str[-1] + ' DST'
            df['TEAM'] = ''

        projections = pd.concat([projections, df])

    projections['season'] = const.SEASON
    projections['week'] = week
    projections.columns = [c.lower() for c in projections.columns]

    return projections


projections = pd.DataFrame()
for w in range(1, 19):
    w = 1
    print(w)
    temp = get_week_projections(w)
    projections = pd.concat([projections, temp])

qb_mask = (projections.position == 'qb') & (projections.fpts > 10)
rb_mask = (projections.position == 'rb') & (projections.fpts > 5)
wr_mask = (projections.position == 'wr') & (projections.fpts > 5)
te_mask = (projections.position == 'te') & (projections.fpts > 3)
dst_mask = (projections.position == 'dst') & (projections.fpts > 3)
projections = projections[qb_mask | rb_mask | wr_mask | te_mask | dst_mask]
projections['match_on'] = projections.player + '|' + projections.team
projections['id'] = (projections.player.str.replace(' ', '')
                     + '_' + projections.season.astype(str)
                     + '_' + projections.week.astype(str).str.zfill(2))


data = DataLoader()
players = data.players()



player_lookup = [f"{p['player']['fullName']}|{const.NFL_TEAM_MAP[p['player']['proTeamId']]}" for p in players]
def match_player_to_espn(the_player: str,
                         player_lookup: list):
    calc = [difflib.SequenceMatcher(None, the_player, m).ratio() for m in player_lookup]
    if max(calc) > 0.8:
        match_idx = calc.index(max(calc))
        # print(f'{the_player} --- {player_lookup[match_idx]} --- {max(calc)}')
        return match_idx
    else:
        return None


match_player_to_espn(the_player='Joe Burrow', player_lookup=player_lookup)
projections['espn_id'] = projections.apply(lambda x: match_player_to_espn(x['match_on'], player_lookup), axis=1)