"""Calibrate the generated archetype reads (Quick reviews) from the reviewed pool, leaving out the configured player.

  python archetype_calibrate.py DB [--dry] [--no-rewrite]

Features per player-set, per round (quick_review_reads.arch_features):
  press_rate      share of after-block / wake-up first actions that were attacks, specials, supers or throws
  drive_pressure  (0.5 x raw Drive Rush + pressure Drive Rush cancels) per round
  jumps_rel       forward jumps per round minus the character's pool average (so a Cammy isn't Aggressive for being Cammy)
  counter         counter hits + punish counters per round
Aggression = the mean of the player-set's pool percentiles on the first three. Throws, anti-airs and Drive Parries per
round are calibrated too, for the lean tags (quick_review_reads.lean_tags: where the player is in the pool's top or
bottom 20%, up to two tags, no numbers). Labels:
  Aggressive      aggression in the pool's top 30%
  Fundamentalist  counter in the pool's top 30% and aggression below the pool's 60th percentile
  Defensive       aggression in the pool's bottom 30% (and not Fundamentalist)
  Balanced        the rest
The pool is every player-set except the configured player's, each other player weighted equally (less below 10 games),
as in spectra_calibrate.py. The cuts are stored in sf6.db (settings 'archetype_cuts'); without --no-rewrite the
generated reads of every Quick set are rewritten with them (Full / Tournament reads are hand-written and kept).
"""
import collections as C, datetime, json, os, sqlite3, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quick_review_reads as W, spectra as SP
from spectra_calibrate import me_id, wpercentiles

DECILES = tuple(i / 10 for i in range(11))


def features(con, key):
    s = con.execute('select focus_player_id, opp_player_id from sets where set_key=?', (key,)).fetchone()
    W.ME = con.execute('select name from players where player_id=?', (s[0],)).fetchone()[0]
    D = W.load_set(con, key)
    W.build_set(key, 0, key, D)
    pid = {W.ME: s[0], D['opp']: s[1]}
    return {pid[n]: f for n, f in W.ARCH_FEATS.items() if n in pid}


def calibrate(db, dry=False, rewrite=True):
    con = sqlite3.connect(db); con.row_factory = sqlite3.Row
    SP.load_cuts(con)
    me = me_id(con)
    keys = [r[0] for r in con.execute('select set_key from sets where excluded is null order by played_date, set_key')]
    games = C.Counter()
    for p1, p2 in con.execute('select p1_player_id, p2_player_id from games'):
        games[p1] += 1; games[p2] += 1
    # pass 1: each character's forward jumps per round (pool, no jump baseline yet)
    W.ARCH = {'jump_base': {}, 'jump_base_all': 0.0}
    raw = {k: features(con, k) for k in keys}
    chars = {}
    for k, f, o, fc, oc in con.execute('select set_key, focus_player_id, opp_player_id, focus_char, opp_char from sets'):
        chars[(k, f)] = W.char(fc); chars[(k, o)] = W.char(oc)
    nsets = C.Counter(p for k in keys for p in raw[k] if p != me)
    wt = {p: min(1.0, games[p] / 10) / nsets[p] for p in nsets}
    jb = C.defaultdict(lambda: [0.0, 0.0])
    for k in keys:
        for p, f in raw[k].items():
            if p == me: continue
            jb[chars.get((k, p))][0] += f['jumps_rel'] * wt[p]; jb[chars.get((k, p))][1] += wt[p]
    tot = [sum(v[0] for v in jb.values()), sum(v[1] for v in jb.values())]
    jump_base = {c: round(v[0] / v[1], 3) for c, v in jb.items() if c and v[1] >= 1.0}
    jump_all = round(tot[0] / tot[1], 3) if tot[1] else 1.5
    for k in keys:
        for p, f in raw[k].items():
            f['jumps_rel'] -= jump_base.get(chars.get((k, p)), jump_all)
    # pass 2: deciles, then the aggression distribution for the cut points
    pool = [(k, p) for k in keys for p in raw[k] if p != me]
    dec = {}
    for ft in ('press_rate', 'drive_pressure', 'jumps_rel', 'counter', 'throws', 'anti_airs', 'parries'):
        vals = [(raw[k][p][ft], wt[p]) for k, p in pool if raw[k][p][ft] is not None]
        dec[ft] = wpercentiles(vals, DECILES)
    W.ARCH = dict(deciles=dec, jump_base=jump_base, jump_base_all=jump_all, cuts=dict(aggressive=1, defensive=0, fundamentals=1, fund_max_agg=0))
    aggv = []
    for k, p in pool:
        _, a, _ = W.classify(raw[k][p]); aggv.append((a, wt[p]))
    q = wpercentiles(aggv, (0.3, 0.6, 0.7))
    W.ARCH['cuts'] = dict(aggressive=q[2], defensive=q[0], fundamentals=0.7, fund_max_agg=q[1])
    meta = dict(calibrated_at=datetime.datetime.now().isoformat(timespec='seconds'), pool_player_sets=len(pool), pool_players=len(nsets),
                excluded_player=con.execute('select name from players where player_id=?', (me,)).fetchone()[0])
    labels = C.Counter(W.classify(raw[k][p])[0] for k, p in pool)
    mine = C.Counter(W.classify(raw[k][me])[0] for k in keys if me in raw[k])
    print(f"pool: {len(pool)} player-sets from {len(nsets)} players; cuts {W.ARCH['cuts']}")
    print('pool labels:', dict(labels.most_common()), '| configured player:', dict(mine.most_common()))
    if dry:
        return W.ARCH
    con.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', ('archetype_cuts', json.dumps(dict(W.ARCH, **meta))))
    con.commit()
    quick = [r[0] for r in con.execute("select s.set_key from sets s where s.excluded is null and (s.review is null or s.review not in ('Full', 'Tournament') "
                                       "or not exists (select 1 from review_docs d where d.set_key = s.set_key and d.dataset = 'archetypes'))")]
    con.close()
    if rewrite:
        out = tempfile.mkdtemp(prefix='arch_')
        for k in quick:
            W.main(db, out, write_reads=True, only=[k])
        print('rewrote generated reads for', len(quick), 'sets')
    return W.ARCH


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    calibrate(a[0], '--dry' in sys.argv, '--no-rewrite' not in sys.argv)
