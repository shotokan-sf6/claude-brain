"""Backfill: a burnout that starts inside the player's own combo that kills is a 'lethal burnout', not a burnout (Sean, 2026-11-22).
Re-reads each game that has burnout events with the analyzer and relabels the matching events; fixes resources.burnouts and set_stats.
usage: lethal_backfill.py WORK_DB LOG.json [FOCUS_PLAYER]"""
import json, os, sqlite3, sys, collections as C
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_capture as A, paths
db, logp = sys.argv[1], sys.argv[2]
FOCUS = sys.argv[3] if len(sys.argv) > 3 else ''
con = sqlite3.connect(db); con.row_factory = sqlite3.Row
done = json.load(open(logp)) if os.path.exists(logp) else {}
games = con.execute("SELECT DISTINCT e.set_key, e.replay_id, g.game_no FROM events e JOIN games g ON g.replay_id=e.replay_id AND g.set_key=e.set_key WHERE e.type='burnout'").fetchall()
name = {r['player_id']: r['name'] for r in con.execute('SELECT player_id, name FROM players')}
pid = {v: k for k, v in name.items()}
for g in games:
    key = g['set_key'] + '|' + g['replay_id']
    if key in done: continue
    path = paths.find_capture(g['replay_id'])
    if not path: done[key] = 'no capture'; continue
    try: res = A.analyze(path, g['game_no'], FOCUS)
    except Exception as ex: done[key] = f'error {ex}'; continue
    leth = [e for e in res['events'] if e['type'] == 'lethal burnout']
    n = 0
    for e in leth:
        p = pid.get(e['player'])
        row = con.execute("SELECT event_id FROM events WHERE set_key=? AND replay_id=? AND round=? AND round_timer=? AND player_id=? AND type='burnout'",
                          (g['set_key'], g['replay_id'], e['round'], e['round_timer'], p)).fetchone()
        if not row: continue
        con.execute("UPDATE events SET type='lethal burnout', note=? WHERE event_id=?", (e['note'], row['event_id']))
        con.execute("UPDATE resources SET burnouts=MAX(0, burnouts-1) WHERE set_key=? AND replay_id=? AND round=? AND player_id=?", (g['set_key'], g['replay_id'], e['round'], p))
        n += 1
    con.commit(); done[key] = n
    json.dump(done, open(logp, 'w'))
    print(key, n, flush=True)
# set_stats: burnouts = burnout events per set and player
for s in con.execute("SELECT DISTINCT set_key, player_id FROM set_stats WHERE metric='burnouts'").fetchall():
    n = con.execute("SELECT COUNT(*) FROM events WHERE set_key=? AND player_id=? AND type='burnout'", (s['set_key'], s['player_id'])).fetchone()[0]
    con.execute("UPDATE set_stats SET value=? WHERE set_key=? AND player_id=? AND metric='burnouts'", (n, s['set_key'], s['player_id']))
con.commit(); print('ALL DONE', sum(v for v in done.values() if isinstance(v, int)))
