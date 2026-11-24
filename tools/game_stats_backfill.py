"""Fill game_stats (per-game metrics, with the character played) for sets ingested before it existed.

Works from what sf6db.py already stored (hits, events, timings, games), so no captures or analyzer output are needed.
Press counts (presses / decision presses) aren't stored per game for old sets, so those metrics are left out here;
a re-ingest adds them. Back up the database first.

usage: python game_stats_backfill.py DB [--all]     (--all also rebuilds sets that already have game_stats)
"""
import sqlite3, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sf6db


def main(db, redo=False):
    con = sf6db.connect(db); con.row_factory = sqlite3.Row
    done = {r[0] for r in con.execute('SELECT DISTINCT set_key FROM game_stats')}
    games = con.execute('SELECT replay_id, set_key, p1_player_id, p2_player_id, p1_char, p2_char FROM games').fetchall()
    n_sets, n_rows = set(), 0
    for g in games:
        k, gid = g['set_key'], g['replay_id']
        if k in done and not redo:
            continue
        hits = [dict(game_id=gid, attacker=r['attacker_id'], victim=r['victim_id'], damage=r['damage'] or 0, hit_kind=r['hit_kind'],
                     anti_air=r['anti_air'], lens=r['lens'], situation=r['situation'])
                for r in con.execute('SELECT * FROM hits WHERE replay_id=?', (gid,))]
        events = [dict(game_id=gid, player=r['player_id'], type=r['type']) for r in con.execute('SELECT * FROM events WHERE replay_id=?', (gid,))]
        timings = [dict(game_id=gid, player=r['player_id'], event=r['event'], action=r['action'] or '', frames_until=r['frames_until'])
                   for r in con.execute('SELECT * FROM timings WHERE replay_id=?', (gid,))]
        con.execute('DELETE FROM game_stats WHERE replay_id=?', (gid,))
        for pid, ch in ((g['p1_player_id'], g['p1_char']), (g['p2_player_id'], g['p2_char'])):
            m = sf6db.set_stats(hits, events, timings, [g], {pid: pid})[pid]
            con.executemany('INSERT OR REPLACE INTO game_stats VALUES (?,?,?,?,?,?)', [(k, gid, pid, ch, a, b) for a, b in m.items()])
            n_rows += len(m)
        n_sets.add(k)
    con.commit()
    print(f'game_stats: {len(n_sets)} sets, {n_rows} rows')


if __name__ == '__main__':
    main(sys.argv[1], '--all' in sys.argv)
