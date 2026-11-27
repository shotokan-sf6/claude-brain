"""Fill whiff punishes (whiff_windows) and jump-ins (jump_ins) for sets already in sf6.db, straight from their captures,
plus their set_stats / game_stats totals (shared_core_db.defense_metrics). Nothing else in a set changes.

  python defense_backfill.py DB [--set KEY]

Players are matched to the capture by side (games.p1_player_id / p2_player_id), so renamed players still line up.
"""
import os, sqlite3, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shared_core_analyze as A, shared_core_whiffs as W, shared_core_antiair as J, shared_core_db as D, paths



def game_rows(path):
    d = A.load_capture(path); fr = d['frames']; names = d.get('move_names', {}); info = d['info']
    rid = info.get('replay_id') or os.path.basename(path).split('.')[0]
    side_name = {'p1': 'p1', 'p2': 'p2'}   # sides stand in for names; mapped to player ids below
    side_char = {s: A._CHAR_ALIAS.get(A._norm(info.get(s + '_char')), info.get(s + '_char')) for s in ('p1', 'p2')}
    other = {'p1': 'p2', 'p2': 'p1'}
    return (W.whiff_windows(fr, names, side_name, side_char, other, A.frame_data, A.mname, A.pretty, rid),
            J.jump_ins(fr, names, side_name, side_char, other, A.mname, A.pretty, rid))


def backfill(db, only=None):
    con = sqlite3.connect(db)
    for ddl in D.SCHEMA.split(';'):
        if 'whiff_windows' in ddl or 'jump_ins' in ddl: con.execute(ddl)
    q = 'SELECT g.set_key, g.replay_id, g.capture_file, g.p1_player_id, g.p2_player_id, g.p1_char, g.p2_char FROM games g JOIN sets s USING (set_key)' + (' WHERE g.set_key = ?' if only else '') + ' ORDER BY g.set_key, g.game_no'
    games = con.execute(q, (only,) if only else ()).fetchall()
    per_set, done, miss = {}, 0, 0
    for k, rid, cap, p1, p2, c1, c2 in games:
        path = cap if cap and os.path.exists(cap) else paths.find_capture(cap or rid) or paths.find_capture(rid)
        if not path: miss += 1; continue
        try:
            whf, jin = game_rows(path)
        except Exception as e:
            print('skip', rid, type(e).__name__, e); miss += 1; continue
        pid = {'p1': p1, 'p2': p2}
        con.execute('DELETE FROM whiff_windows WHERE replay_id=?', (rid,)); con.execute('DELETE FROM jump_ins WHERE replay_id=?', (rid,))
        con.executemany('INSERT INTO whiff_windows VALUES (' + ','.join('?' * 16) + ')', [(k, rid, x['round'], x['round_timer'], pid[x['whiffer']], pid[x['punisher']], x['move'], x['window'], x['distance'],
                        x['punisher_state'], x['result'], x['why'], x['punish'], x['pressed'], x['best'], int(x['chance'])) for x in whf])
        con.executemany('INSERT INTO jump_ins VALUES (' + ','.join('?' * 15) + ')', [(k, rid, x['round'], x['round_timer'], pid[x['jumper']], pid[x['defender']], x['direction'], x['jump_attack'], x['result'],
                        int(x['defender_free']), x['pressed'], x['anti_air_with'], None if x['opened'] is None else int(x['opened']), x['distance'], x['land_distance']) for x in jin])
        # per game: each side's metrics under its player id
        char = {p1: c1, p2: c2}
        for side in ('p1', 'p2'):
            m = D.defense_metrics(whf, jin, side)
            con.execute('DELETE FROM game_stats WHERE set_key=? AND replay_id=? AND player_id=? AND metric IN (%s)' % ','.join('?' * len(m)), (k, rid, pid[side], *m))
            con.executemany('INSERT OR REPLACE INTO game_stats VALUES (?,?,?,?,?,?)', [(k, rid, pid[side], char.get(pid[side]), a, b) for a, b in m.items()])
        # relabel sides as player ids for the set totals
        for x in whf: x['whiffer'], x['punisher'] = pid[x['whiffer']], pid[x['punisher']]
        for x in jin: x['jumper'], x['defender'] = pid[x['jumper']], pid[x['defender']]
        s = per_set.setdefault(k, ([], [], set())); s[0].extend(whf); s[1].extend(jin); s[2].update((p1, p2))
        done += 1
        if done % 50 == 0: con.commit(); print(done, 'games')
    for k, (whf, jin, pids) in per_set.items():
        for p in pids:
            m = D.defense_metrics(whf, jin, p)
            con.execute('DELETE FROM set_stats WHERE set_key=? AND player_id=? AND metric IN (%s)' % ','.join('?' * len(m)), (k, p, *m))
            con.executemany('INSERT INTO set_stats VALUES (?,?,?,?)', [(k, p, a, b) for a, b in m.items()])
    con.commit(); con.close()
    print(f'defense backfill: {done} games, {miss} without a capture, {len(per_set)} sets')


if __name__ == '__main__':
    a = sys.argv[1:]
    backfill(a[0], a[a.index('--set') + 1] if '--set' in a else None)
