from scripts.api.DataLoader import DataLoader
from scripts.utils import constants as const
import difflib
import pandas as pd
pd.options.mode.chained_assignment = None


def match_player_to_espn(the_player: str,
                         players: list):
    player_lookup = [f"{p['player']['fullName']}|{const.NFL_TEAM_MAP[p['player']['proTeamId']]}" for p in players]

    calc = [difflib.SequenceMatcher(None, the_player, m).ratio() for m in player_lookup]
    if max(calc) > 0.8:
        match_idx = calc.index(max(calc))

        return players[match_idx]['id']
    else:
        return None


def get_week_projections(week):
    """Return current week's projections for all positions"""
    data = DataLoader()
    players = data.players()['players']

    positions = ['qb', 'rb', 'wr', 'te', 'dst']

    projections = pd.DataFrame()
    for pos in positions:
        # print(pos)
        url = f"https://www.fantasypros.com/nfl/projections/{pos}.php?scoring=HALF&week={week}"
        # url = f"https://www.fantasypros.com/nfl/rankings/half-point-ppr-{pos}.php?scoring=HALF&week={week}"
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

    projections['season'] = const.SEASON
    projections['week'] = week
    projections.columns = [c.lower() for c in projections.columns]

    qb_mask = (projections.position == 'QB') & (projections.fpts > 10)
    rb_mask = (projections.position == 'RB') & (projections.fpts > 5)
    wr_mask = (projections.position == 'WR') & (projections.fpts > 5)
    te_mask = (projections.position == 'TE') & (projections.fpts > 3)
    dst_mask = (projections.position == 'DST') & (projections.fpts > 3)
    projections = projections[qb_mask | rb_mask | wr_mask | te_mask | dst_mask]
    projections['match_on'] = projections.player + '|' + projections.team
    projections['id'] = (projections.player.str.replace(' ', '')
                         + '_' + projections.season.astype(str)
                         + '_' + projections.week.astype(str).str.zfill(2))
    projections['espn_id'] = projections.apply(lambda x: match_player_to_espn(x['match_on'], players), axis=1)

    return projections[~projections.espn_id.isnull()]
