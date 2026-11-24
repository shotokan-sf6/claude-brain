"""Resolve labels relabel_moves.py left ambiguous, per row, by re-running the current analyzer on a set's captures.
  python relabel_resolve.py DB TOOLS_DIR REPLAYS_DIR CHAR "label1|label2" SETKEY [SETKEY ...] [--dry]
Touches only that character's rows whose label is one of the ambiguous labels (hits.starter / victim_move, timings.action)
and that character's usage rows for each game (replaced from the new report)."""
import ast, json, os, re, sqlite3, subprocess, sys, tempfile
args = [a for a in sys.argv[1:] if not a.startswith('--')]; dry = '--dry' in sys.argv
db, tools, reps, char, labs = args[:5]; keys = args[5:]
amb = set(labs.split('|')); amb |= {a + ' (OD)' for a in amb}
con = sqlite3.connect(db); cur = con.cursor()
name_of = dict(cur.execute('select player_id, name from players'))
tot = {'hits': 0, 'victim': 0, 'timings': 0, 'unmatched': 0, 'usage_games': 0}
for k in keys:
    games = cur.execute('select replay_id, p1_player_id, p2_player_id, p1_char, p2_char from games where set_key=? order by game_no', (k,)).fetchall()
    caps = [os.path.join(reps, g[0] + '.json.gz') for g in games]
    out = tempfile.mkdtemp()
    focus = name_of.get(games[0][1]) or '.shog'
    r = subprocess.run([sys.executable, os.path.join(tools, 'shared_core_analyze.py'), out, focus, 'FT5'] + caps, capture_output=True, text=True)
    if r.returncode: print(k, 'analyzer failed', r.stderr[-400:]); continue
    nh = json.load(open(os.path.join(out, 'hits.json'))); nt = json.load(open(os.path.join(out, 'timings.json')))
    hk = {}
    for h in nh: hk.setdefault((h['game_id'], h['round'], h['round_timer'], h['damage'], h['hits_in_combo']), []).append(h)
    pid_char = {}
    for rid, p1, p2, c1, c2 in games: pid_char[(rid, p1)] = c1; pid_char[(rid, p2)] = c2
    for hid, rid, rnd, tm, dmg, n, ac, vc, st, vm in cur.execute('select hit_id, replay_id, round, round_timer, damage, hits_in_combo, attacker_char, victim_char, starter, victim_move from hits where set_key=?', (k,)).fetchall():
        fix_s = ac == char and st in amb; fix_v = vc == char and vm in amb
        if not (fix_s or fix_v): continue
        c = hk.get((rid, rnd, tm, dmg, n), [])
        if len(c) != 1: tot['unmatched'] += 1; print('  unmatched hit', hid, rid, rnd, tm, st, vm, len(c)); continue
        s2 = c[0]['starter'] if fix_s else st; v2 = c[0]['victim_move'] if fix_v else vm
        if s2 != st: tot['hits'] += 1; print('  hit', rid, rnd, '@', tm, st, '->', s2)
        if v2 != vm: tot['victim'] += 1; print('  victim', rid, rnd, '@', tm, vm, '->', v2)
        if (s2, v2) != (st, vm) and not dry: cur.execute('update hits set starter=?, victim_move=? where hit_id=?', (s2, v2, hid))
    tk = {}
    for t in nt: tk.setdefault((t['game_id'], t['round'], t['round_timer'], t['player'], t['event'], t['frames_until']), []).append(t['action'])
    for tid, rid, rnd, tm, pid, ev, act, fu in cur.execute('select timing_id, replay_id, round, round_timer, player_id, event, action, frames_until from timings where set_key=?', (k,)).fetchall():
        if pid_char.get((rid, pid)) != char or not act or not any(a in act for a in amb): continue
        c = tk.get((rid, rnd, tm, name_of.get(pid), ev, fu), [])
        if len(set(c)) != 1: tot['unmatched'] += 1; print('  unmatched timing', rid, rnd, tm, act, c); continue
        if c[0] != act:
            tot['timings'] += 1; print('  timing', rid, rnd, '@', tm, act, '->', c[0])
            dry or cur.execute('update timings set action=? where timing_id=?', (c[0], tid))
    gi = -1; pids = {name_of.get(p): p for rid, p1, p2, c1, c2 in games for p, ch in ((p1, c1), (p2, c2)) if ch == char}
    for line in open(os.path.join(out, 'report.md'), encoding='utf-8'):
        if line.startswith('# Game'): gi += 1
        m = re.match(r'\s+usage (.+?): (\[.*\])$', line)
        if m and 0 <= gi < len(games) and m.group(1) in pids:
            rid, pid = games[gi][0], pids[m.group(1)]
            if pid_char.get((rid, pid)) != char: continue
            tot['usage_games'] += 1
            if not dry:
                cur.execute('delete from usage where set_key=? and replay_id=? and player_id=?', (k, rid, pid))
                cur.executemany('insert or replace into usage values (?,?,?,?,?)', [(k, rid, pid, mv, n) for mv, n in ast.literal_eval(m.group(2))])
print(tot)
dry or con.commit()
