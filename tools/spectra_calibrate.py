"""Recalibrate the spectra cut points from the reviewed pool, leaving out the configured player.

  python spectra_calibrate.py DB [--min-games 10] [--dry]

The cut points are the 20/40/60/80th percentiles of each axis's raw value over every player-set in sf6.db except
the configured player's (settings 'me', else shotokan.json / SHOTOKAN_PLAYER), so a 1-5 score compares a player
with everyone else, not with a pool that is mostly the player being coached.

Each other player counts equally: a player's sets share one weight, min(1, games / --min-games). Players with
fewer than 10 games (a couple of FT2 sets) count for less until there is enough of them to trust.

Without --dry it stores the cut points in sf6.db (settings 'spectra_cuts'), re-scores every set with them
(spectra_backfill.py, which also stores the raw values in spectra_raw) and refreshes the personal baseline
(player_baseline.py). It prints the old and new cut points and how many scores moved.
"""
import collections as C, datetime, json, os, sqlite3, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths, spectra as SP, spectra_backfill as BF, quick_review_reads as W


def me_id(con):
    """player_id of the configured player: settings 'me', then the CFN ID, then the name from shotokan.json."""
    row = con.execute("select value from settings where key='me'").fetchone()
    names = [row[0]] if row and row[0] else []
    if paths.PLAYER_CFN:
        r = con.execute('select player_id from players where cfn_id=?', (str(paths.PLAYER_CFN),)).fetchone()
        if r: return r[0]
    for n in names + list(paths.PLAYER_NAMES or []):
        r = con.execute('select player_id from players where name=?', (n,)).fetchone() or \
            con.execute('select player_id from player_names where name=?', (n,)).fetchone()
        if r: return r[0]
    return None


def set_raws(con, key):
    """{player_id: {axis_key: raw}} for both players of one set (behaviour counts added to beh_cache if missing)."""
    BF.ensure_behavior(con, key)
    s = con.execute('select focus_player_id, opp_player_id from sets where set_key=?', (key,)).fetchone()
    W.ME = con.execute('select name from players where player_id=?', (s[0],)).fetchone()[0]
    D = W.load_set(con, key)
    out = {}
    for name, pid in ((W.ME, s[0]), (D['opp'], s[1])):
        vals, _ = SP.raw(name, D['games'], D['hits'], D['tim'], D['ev'], D['use'])
        out[pid] = {a['key']: vals.get(a['key']) for a in SP.AXES}
    return out


def wpercentiles(vals, qs=(0.2, 0.4, 0.6, 0.8)):
    """weighted percentiles: vals = [(value, weight)]"""
    vals = sorted(v for v in vals if v[1] > 0)
    tot = sum(w for _, w in vals)
    out = []
    for q in qs:
        acc = 0.0
        for v, w in vals:
            acc += w
            if acc >= q * tot - 1e-9:
                out.append(round(v, 4)); break
    return out


def calibrate(db, min_games=10, dry=False):
    con = sqlite3.connect(db); con.row_factory = sqlite3.Row
    me = me_id(con)
    if me is None:
        sys.exit('No configured player found (settings "me", shotokan.json or SHOTOKAN_PLAYER): can\'t leave them out.')
    keys = [r[0] for r in con.execute('select set_key from sets order by played_date, set_key')]
    games = C.Counter()
    for p1, p2 in con.execute('select p1_player_id, p2_player_id from games'):
        games[p1] += 1; games[p2] += 1
    raws = {}
    for k in keys:
        raws[k] = set_raws(con, k)
    nsets = C.Counter(pid for k in keys for pid in raws[k] if pid != me)
    w_player = {pid: min(1.0, games[pid] / min_games) for pid in nsets}
    cuts = {}
    for a in SP.AXES:
        ax = a['key']
        vals = [(raws[k][pid][ax], w_player[pid] / nsets[pid]) for k in keys for pid in raws[k] if pid != me and raws[k][pid].get(ax) is not None]
        cuts[ax] = wpercentiles(vals) if len(vals) >= 10 else SP.DEFAULT_CUTS[ax]
    name = con.execute('select name from players where player_id=?', (me,)).fetchone()[0]
    meta = dict(calibrated_at=datetime.datetime.now().isoformat(timespec='seconds'), excluded_player=name,
                pool_players=len(nsets), pool_player_sets=sum(nsets.values()), effective_players=round(sum(w_player.values()), 1),
                min_games=min_games, source='pool without the configured player, each other player weighted equally')
    old = {k: list(v) for k, v in SP.CUTS.items()}
    print(f"pool: {meta['pool_player_sets']} player-sets from {meta['pool_players']} players (effective weight {meta['effective_players']}), {name} left out")
    for a in SP.AXES:
        print(f"  {a['axis']:24} old {old[a['key']]}  new {cuts[a['key']]}")
    if dry:
        return cuts, meta
    before = {(r[0], r[1], r[2]): r[3] for r in con.execute('select set_key, player_id, axis, score from spectra')}
    con.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', ('spectra_cuts', json.dumps(dict(meta, cuts=cuts))))
    con.commit(); con.close()
    BF.backfill(db, keys)
    con = sqlite3.connect(db)
    after = {(r[0], r[1], r[2]): r[3] for r in con.execute('select set_key, player_id, axis, score from spectra')}
    moved = C.Counter()
    for k, v in after.items():
        if k in before and before[k] is not None and v is not None and v != before[k]:
            moved['me' if k[1] == me else 'others'] += 1
    print(f"re-scored {len(keys)} sets; scores that moved: {moved['me']} of the configured player's, {moved['others']} of everyone else's")
    con.close()
    import player_baseline
    player_baseline.update(db)
    return cuts, meta


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    mg = int(sys.argv[sys.argv.index('--min-games') + 1]) if '--min-games' in sys.argv else 10
    if '--min-games' in sys.argv: a = [x for x in a if x != str(mg)]
    calibrate(a[0], mg, '--dry' in sys.argv)
