"""Re-score hit damage in sf6.db with the current analyzer (white / recoverable health, Nov 2026), without re-ingesting.

For every game in the database it re-runs shared_core_analyze.analyze() on the game's capture, matches the analyzer's hits to the
stored hits (same round, round timer and attacker, in order), and updates damage, recoverable and white_cashed. Then it
recomputes the damage-based stats (damage_dealt, damage_taken, taken_share / taken_dmg / taken_situation_share) in set_stats
and game_stats. Everything else (reads, habits, review docs, press counts, labels) is left as it is.
Back up the database first. SQLite writes fail on some network / VM mounts: run it on a copy on a local disk.

usage: python rescore_damage.py DB CAPTURE_DIR [--set SET_KEY ...] [--dry-run]
"""
import collections as C, os, sqlite3, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shared_core_analyze as A
import shared_core_db

DMG_PREFIX = ('taken_share: ', 'taken_dmg: ', 'taken_situation_share: ')


def capture_path(cdir, rid):
    for ext in ('.json.gz', '.json'):
        p = os.path.join(cdir, rid + ext)
        if os.path.exists(p): return p
    return None


def damage_metrics(hits, pids):
    """Just the damage-based metrics of shared_core_db.set_stats, keyed by player id."""
    out = {}
    for pid in pids:
        mine = [h for h in hits if h['attacker'] == pid]; took = [h for h in hits if h['victim'] == pid]
        taken = sum(h['damage'] for h in took)
        m = dict(damage_dealt=sum(h['damage'] for h in mine), damage_taken=taken)
        lens, sit = C.Counter(), C.Counter()
        for h in took: lens[h['lens'] or 'Unclear / super'] += h['damage']; sit[h['situation']] += h['damage']
        for k, v in lens.items(): m['taken_share: ' + k] = round(v / taken, 4) if taken else 0; m['taken_dmg: ' + k] = v
        for k, v in sit.items(): m['taken_situation_share: ' + k] = round(v / taken, 4) if taken else 0
        out[pid] = m
    return out


def write_metrics(con, table, keycols, keyvals, pid, m, extra=()):
    w = ' AND '.join(f'{c}=?' for c in keycols)
    con.execute(f"DELETE FROM {table} WHERE {w} AND player_id=? AND (metric IN ('damage_dealt','damage_taken') OR "
                + ' OR '.join("metric LIKE ?" for _ in DMG_PREFIX) + ')', (*keyvals, pid, *[p + '%' for p in DMG_PREFIX]))
    for k, v in m.items():
        if table == 'set_stats': con.execute('INSERT OR REPLACE INTO set_stats VALUES (?,?,?,?)', (*keyvals, pid, k, v))
        else: con.execute('INSERT OR REPLACE INTO game_stats VALUES (?,?,?,?,?,?)', (extra[0], keyvals[0], pid, extra[1], k, v))


def main():
    args = sys.argv[1:]; dry = '--dry-run' in args; args = [a for a in args if a != '--dry-run']
    only = set()
    if '--set' in args:
        i = args.index('--set'); only = set(args[i + 1:]); args = args[:i]
    db, cdir = args
    con = shared_core_db.connect(db); con.row_factory = sqlite3.Row
    pname = {r['player_id']: r['name'] for r in con.execute('SELECT player_id, name FROM players')}
    games = con.execute('SELECT * FROM games ORDER BY set_key, game_no').fetchall()
    stats = C.Counter(); missing = []; touched = set()
    for g in games:
        k, rid = g['set_key'], g['replay_id']
        if only and k not in only: continue
        p = capture_path(cdir, rid)
        if not p: missing.append(rid); continue
        try:
            res = A.analyze(p, g['game_no'], pname.get(g['p1_player_id'], ''))
        except Exception as e:   # one bad capture shouldn't stop the run
            print('analyze failed', rid, e); stats['failed'] += 1; continue
        name_of = {'p1': res['side_name']['p1'], 'p2': res['side_name']['p2']}
        id_of = {res['side_name']['p1']: g['p1_player_id'], res['side_name']['p2']: g['p2_player_id']}
        pool = C.defaultdict(list)
        for r in res['rows']: pool[(r['round'], r['round_timer'], id_of.get(r['attacker']))].append(r)
        db_hits = con.execute('SELECT hit_id, round, round_timer, attacker_id, damage FROM hits WHERE replay_id=? ORDER BY hit_id', (rid,)).fetchall()
        for h in db_hits:
            cand = pool.get((h['round'], h['round_timer'], h['attacker_id']))
            if not cand:   # older analyzer versions could put the hit a second off
                for dt in (1, -1, 2, -2):
                    cand = pool.get((h['round'], (h['round_timer'] or 0) + dt, h['attacker_id']))
                    if cand: break
            if not cand: stats['unmatched'] += 1; continue
            r = cand.pop(0)
            if r['damage'] != h['damage']: stats['changed'] += 1; stats['delta'] += r['damage'] - (h['damage'] or 0)
            stats['matched'] += 1
            if not dry:
                con.execute('UPDATE hits SET damage=?, recoverable=?, white_cashed=? WHERE hit_id=?',
                            (r['damage'], r.get('recoverable') or 0, r.get('white_cashed') or 0, h['hit_id']))
        stats['games'] += 1; touched.add(k)
    if not dry:
        for k in touched:
            rows = [dict(r) for r in con.execute('SELECT replay_id, attacker_id AS attacker, victim_id AS victim, damage, lens, situation FROM hits WHERE set_key=?', (k,))]
            for r in rows: r['damage'] = r['damage'] or 0
            gs = con.execute('SELECT replay_id, p1_player_id, p2_player_id, p1_char, p2_char FROM games WHERE set_key=?', (k,)).fetchall()
            pids = {x for g in gs for x in (g['p1_player_id'], g['p2_player_id'])}
            for pid, m in damage_metrics(rows, pids).items(): write_metrics(con, 'set_stats', ('set_key',), (k,), pid, m)
            for g in gs:
                gr = [r for r in rows if r['replay_id'] == g['replay_id']]
                for pid, ch in ((g['p1_player_id'], g['p1_char']), (g['p2_player_id'], g['p2_char'])):
                    m = damage_metrics(gr, {pid})[pid]
                    write_metrics(con, 'game_stats', ('replay_id',), (g['replay_id'],), pid, m, extra=(k, ch))
        con.commit()
    print(dict(stats), 'sets', len(touched), 'missing captures', len(missing), missing[:20])


if __name__ == '__main__':
    main()
