"""Time each player spends cornered, per round, from a replay capture.

  python corner_time.py CAPTURE [CAPTURE ...]          print per-round corner time
  python corner_time.py --backfill DB [--set KEY]      fill the corner_time table (and set_stats / game_stats) for sets in sf6.db

A player is CORNERED on a frame when they stand within CORNER_ZONE of the wall (|posX| >= STAGE_EDGE - CORNER_ZONE) and the
opponent is on the inner side of them (between them and the rest of the stage). A zoner who backs into the corner by
choice counts as cornered too: the capture can't tell pinned from parked. Only live-play frames count
(fight_st == 4: not the round intro, KO or outro). Positions are the capture's posX; the wall is at |posX| 7.65.
The opponent of a cornered player is CORNERING them, so one player's cornered time is the other's cornering time.

Per round and player: active_frames, cornered_frames, cornered_entries (times they got cornered, a stint ending when
they leave the zone or the opponent crosses over), longest_cornered (frames). Seconds = frames / 60.
"""
import json, os, sqlite3, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STAGE_EDGE = 7.65      # |posX| at the wall (shared_core_analyze.STAGE_EDGE)
CORNER_ZONE = 1.5      # within this of the wall counts as cornered
LIVE = 4               # fight_st during live play
MIN_STINT = 6          # frames: shorter stints (a jump grazing the zone) don't count as an entry

SCHEMA = """CREATE TABLE IF NOT EXISTS corner_time (
  set_key TEXT, replay_id TEXT, round INTEGER, player_id INTEGER,
  active_frames INTEGER, cornered_frames INTEGER, cornered_entries INTEGER, longest_cornered INTEGER,
  PRIMARY KEY (replay_id, round, player_id))"""


def cornered(me, opp):
    """Near the wall with the opponent on the inner side (between this player and the rest of the stage)."""
    x, o = me.get('posX'), opp.get('posX')
    if x is None or o is None or abs(x) < STAGE_EDGE - CORNER_ZONE: return False
    return o < x if x > 0 else o > x


def corner_rows(frames, side_name):
    """[{round, player, active_frames, cornered_frames, cornered_entries, longest_cornered}] per round (1-based) and side."""
    out = {}
    run = {'p1': 0, 'p2': 0}
    for f in frames:
        if f.get('fight_st') != LIVE: run = {'p1': 0, 'p2': 0}; continue
        rnd = (f.get('round') or 0) + 1
        for s, o in (('p1', 'p2'), ('p2', 'p1')):
            r = out.setdefault((rnd, s), dict(round=rnd, player=side_name[s], active_frames=0, cornered_frames=0, cornered_entries=0, longest_cornered=0))
            r['active_frames'] += 1
            if cornered(f[s], f[o]):
                r['cornered_frames'] += 1; run[s] += 1
                if run[s] == MIN_STINT: r['cornered_entries'] += 1
                r['longest_cornered'] = max(r['longest_cornered'], run[s])
            else:
                run[s] = 0
    return [out[k] for k in sorted(out)]


def from_capture(path):
    import shared_core_analyze as A
    cap = A.load_capture(path)
    inf = cap['info']
    names = {s: inf.get(f'{s}_name') or s for s in ('p1', 'p2')}
    return corner_rows(cap['frames'], names)


def store(con, set_key, replay_id, rows, pid_of):
    con.execute(SCHEMA)
    con.execute('DELETE FROM corner_time WHERE replay_id = ?', (replay_id,))
    con.executemany('INSERT INTO corner_time VALUES (?,?,?,?,?,?,?,?)',
                    [(set_key, replay_id, r['round'], pid_of[r['player']], r['active_frames'], r['cornered_frames'], r['cornered_entries'], r['longest_cornered'])
                     for r in rows if r['player'] in pid_of])


def stat_rows(rows):
    """Totals for set_stats / game_stats, by player name: cornered and cornering frames, entries, active frames."""
    tot = {}
    by_round = {}
    for r in rows: by_round.setdefault((r.get('game_id'), r['round']), []).append(r)
    for rs in by_round.values():
        for r in rs:
            t = tot.setdefault(r['player'], dict(active_frames=0, cornered_frames=0, cornering_frames=0, cornered_entries=0))
            t['active_frames'] += r['active_frames']; t['cornered_frames'] += r['cornered_frames']; t['cornered_entries'] += r['cornered_entries']
            t['cornering_frames'] += sum(o['cornered_frames'] for o in rs if o['player'] != r['player'])
    return tot


def backfill(db, only=None):
    con = sqlite3.connect(db)
    con.execute(SCHEMA)
    q = 'SELECT g.set_key, g.replay_id, g.capture_file FROM games g JOIN sets s USING (set_key)' + (' WHERE g.set_key = ?' if only else '')
    games = con.execute(q, (only,) if only else ()).fetchall()
    done = miss = 0
    per_set = {}
    for k, rid, cap in games:
        path = cap if cap and os.path.exists(cap) else None
        if not path:
            import paths   # SHOTOKAN_REPLAYS / SHOTOKAN_CAPTURE_DIRS
            path = paths.find_capture(cap or rid) or paths.find_capture(rid)
        if not path: miss += 1; continue
        try:
            rows = from_capture(path)
        except Exception as e:
            print('skip', rid, e); miss += 1; continue
        ids = dict(con.execute('SELECT p.name, p.player_id FROM players p WHERE p.player_id IN (SELECT p1_player_id FROM games WHERE replay_id=? UNION SELECT p2_player_id FROM games WHERE replay_id=?)', (rid, rid)).fetchall())
        ids.update(dict(con.execute('SELECT n.name, n.player_id FROM player_names n WHERE n.player_id IN (SELECT p1_player_id FROM games WHERE replay_id=? UNION SELECT p2_player_id FROM games WHERE replay_id=?)', (rid, rid)).fetchall()))
        p1, p2 = con.execute('SELECT p1_player_id, p2_player_id FROM games WHERE replay_id=?', (rid,)).fetchone()
        ids.setdefault('p1', p1); ids.setdefault('p2', p2)   # local captures with no player names: match by side
        store(con, k, rid, rows, ids)
        for r in rows: r['game_id'] = rid
        per_set.setdefault(k, []).append((rid, rows, ids))
        done += 1
    for k, gl in per_set.items():
        allrows = [r for _, rows, _ in gl for r in rows]
        ids = {}
        for _, _, i in gl: ids.update(i)
        write_stats(con, k, allrows, ids, per_game={rid: rows for rid, rows, _ in gl})
    con.commit(); con.close()
    print(f'corner_time: {done} games stored, {miss} without a capture, {len(per_set)} sets')


METRICS = ('active_frames', 'cornered_frames', 'cornering_frames', 'cornered_entries')


def write_stats(con, set_key, rows, pid_of, per_game=None):
    con.execute('DELETE FROM set_stats WHERE set_key = ? AND metric IN (%s)' % ','.join('?' * len(METRICS)), (set_key, *METRICS))
    for name, t in stat_rows(rows).items():
        if name in pid_of:
            con.executemany('INSERT INTO set_stats VALUES (?,?,?,?)', [(set_key, pid_of[name], m, t[m]) for m in METRICS])
    for rid, grows in (per_game or {}).items():
        con.execute('DELETE FROM game_stats WHERE set_key = ? AND replay_id = ? AND metric IN (%s)' % ','.join('?' * len(METRICS)), (set_key, rid, *METRICS))
        char = dict(con.execute('SELECT p1_player_id, p1_char FROM games WHERE replay_id=? UNION SELECT p2_player_id, p2_char FROM games WHERE replay_id=?', (rid, rid)).fetchall())
        for name, t in stat_rows(grows).items():
            if name in pid_of:
                pid = pid_of[name]
                con.executemany('INSERT OR REPLACE INTO game_stats VALUES (?,?,?,?,?,?)', [(set_key, rid, pid, char.get(pid), m, t[m]) for m in METRICS])


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == '--backfill':
        backfill(a[1], a[a.index('--set') + 1] if '--set' in a else None)
    else:
        for p in a:
            for r in from_capture(p):
                print(f"{os.path.basename(p)} R{r['round']} {r['player']}: cornered {r['cornered_frames'] / 60:.1f}s of {r['active_frames'] / 60:.1f}s "
                      f"({r['cornered_entries']} times, longest {r['longest_cornered'] / 60:.1f}s)")
