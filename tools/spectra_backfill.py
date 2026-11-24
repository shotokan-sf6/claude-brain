"""Fill the spectra table (and the spectra in review_docs archetypes) for sets that have none.

shared_core_db.py ingest runs this for the set it just ingested. Four axes (Composure, Initiative, Resource use,
Temperament (offense)) read behaviour counts from beh_cache.json; replays missing from the cache are added first,
from the captures (META captures_local, else the capture folders in paths.py: SHOTOKAN_REPLAYS / SHOTOKAN_CAPTURE_DIRS).

  python spectra_backfill.py DB              # every set without spectra
  python spectra_backfill.py DB SET_KEY ...  # these sets (recomputed even if present)
"""
import json, sqlite3, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quick_review_reads as W, spectra as SP, paths

HERE = os.path.dirname(os.path.abspath(__file__))


def _find(rid, cf, local):
    if local and local.get(rid) and os.path.exists(local[rid]):
        return local[rid]
    return paths.find_capture(cf or rid) or paths.find_capture(rid)


def ensure_behavior(con, key, local=None):
    """Add the set's replays to beh_cache.json (and spectra's in-memory copy) if they're missing."""
    import behavior
    added = 0
    for rid, cf in con.execute('select replay_id, capture_file from games where set_key=?', (key,)).fetchall():
        if rid in SP.BEH: continue
        path = _find(rid, cf, local)
        if not path: print('no capture for', rid, '(spectra from behaviour counts will be missing)', file=sys.stderr); continue
        SP.BEH[rid] = behavior.counts(path); added += 1
    if added:
        json.dump(SP.BEH, open(SP._CACHE, 'w'))
    return added


def backfill(db, keys=None, me=None, local=None):
    con = sqlite3.connect(db); con.row_factory = sqlite3.Row
    SP.load_cuts(con)   # calibrated cut points (spectra_calibrate.py), else the built-in ones
    con.execute('CREATE TABLE IF NOT EXISTS spectra_raw (set_key TEXT, player_id INTEGER, axis_key TEXT, raw REAL, PRIMARY KEY (set_key, player_id, axis_key))')
    if not keys:
        keys = [r[0] for r in con.execute('select set_key from sets s where not exists (select 1 from spectra p where p.set_key = s.set_key)')]
    for key in keys:
        ensure_behavior(con, key, local)
        s = con.execute('select focus_player_id from sets where set_key=?', (key,)).fetchone()
        W.ME = con.execute('select name from players where player_id=?', (s['focus_player_id'],)).fetchone()['name'] or me or paths.PLAYER   # the set's own focus player
        D = W.load_set(con, key); d, _ = W.build_set(key, 0, key, D)
        hw = con.execute("select rows from review_docs where set_key=? and dataset='archetypes'", (key,)).fetchone()
        ovs = {r.get('player'): r.get('spectra_override') for r in (json.loads(hw['rows']) if hw else []) if r.get('spectra_override')}
        for a in d['archetypes']:   # a Full review's reviewer's-call overrides (review_docs archetypes) apply to the computed spectra
            if ovs.get(a.get('player')): a['spectra_override'] = ovs[a['player']]
        SP.attach(d['archetypes'], key, D['games'], D['hits'], D['tim'], D['ev'], D['use'])
        pid = {W.ME: D['s']['focus_player_id'], D['opp']: D['s']['opp_player_id']}
        by_player = {}
        for a in d['archetypes']:
            by_player[a['player']] = a['spectra']
            for sp in a['spectra']:
                con.execute('INSERT OR REPLACE INTO spectra VALUES (?,?,?,?,?,?)', (key, pid[a['player']], sp['axis'], sp['score'], sp['label'], sp['evidence']))
                con.execute('DELETE FROM spectra_raw WHERE set_key=? AND player_id=? AND axis_key=?', (key, pid[a['player']], sp['key']))
                if sp.get('raw') is not None:   # the raw value behind the score (personal baseline, recalibration)
                    con.execute('INSERT INTO spectra_raw VALUES (?,?,?,?)', (key, pid[a['player']], sp['key'], sp['raw']))
        r = con.execute("select rows from review_docs where set_key=? and dataset='archetypes'", (key,)).fetchone()
        if r:   # hand-written reads: keep them, attach the computed spectra
            rows = json.loads(r['rows'])
            for a in rows:
                if a.get('player') in by_player and (not a.get('spectra') or a.get('spectra_override')): a['spectra'] = by_player[a['player']]
            con.execute("update review_docs set rows=? where set_key=? and dataset='archetypes'", (json.dumps(rows), key))
        con.commit()
        print('spectra', key, {p: [x['score'] for x in v] for p, v in by_player.items()})


if __name__ == '__main__':
    backfill(sys.argv[1], sys.argv[2:] or None)
