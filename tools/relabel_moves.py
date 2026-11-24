"""Bring an existing sf6.db's move labels up to date after the analyzer learns new move names, without re-ingesting.

  python relabel_moves.py DB OLD_ANALYZER.py MOVES_DIR [--chars "Cammy,M Bison"] [--dry]

OLD_ANALYZER.py is the previous analyze_capture.py (e.g. `git show <commit>:tools/analyze_capture.py > old.py`); the
current one is this folder's. MOVES_DIR is the move export folder (reframework/data/sf6_moves, or SF6_MOVES). For each
character, every internal move name in its export is labelled by both versions; where the label changed, the old label
is replaced by the new one. An old label that maps to more than one new label is ambiguous and left alone (reported).
A trailing " (OD)" added by the Drive-drain check is kept.

Touched, for that character's side only: hits.starter (attacking) and hits.victim_move (being hit), timings.action,
resources.supers (the "L<n> <move>" entries) and usage.move (merged where two old labels become one). Hand-written
text (reads, habits, review_docs) is left as written.
"""
import glob, importlib.util, json, os, re, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_capture as NEW


def load_old(path):
    spec = importlib.util.spec_from_file_location('old_analyzer', path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def mapping(old, moves_dir, char):
    files = [f for f in glob.glob(os.path.join(moves_dir, '*.json')) if re.match(r'\d+_', os.path.basename(f))]
    raw = set()
    for f in files:
        try:
            d = json.load(open(f, encoding='utf-8'))
        except Exception:
            continue
        if d.get('char_name', '').replace('.', '').replace('_', ' ') != char.replace('.', ''):
            continue
        raw |= {v if isinstance(v, str) else v.get('name', '') for v in d['moves'].values()}
    cand = {}
    for n in raw:
        a, b = old.pretty(n, char), NEW.pretty(n, char)
        if a != b: cand.setdefault(a, set()).add(b)
    good = {a: next(iter(b)) for a, b in cand.items() if len(b) == 1}
    bad = {a: sorted(b) for a, b in cand.items() if len(b) > 1}
    return good, bad, len(raw)


def relabel(m, label):
    if not label: return label
    if label in m: return m[label]
    if label.endswith(' (OD)') and label[:-5] in m: return m[label[:-5]] + ' (OD)'
    return label


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    db, old_path, moves_dir = args[:3]
    dry = '--dry' in sys.argv
    chars = sys.argv[sys.argv.index('--chars') + 1].split(',') if '--chars' in sys.argv else None
    old = load_old(old_path)
    con = sqlite3.connect(db)
    if not chars:
        chars = sorted({c for row in con.execute('select p1_char, p2_char from games') for c in row if c})
    maps = {}
    for c in chars:
        good, bad, n = mapping(old, moves_dir, c)
        if not n: continue
        if good or bad: print(f'{c}: {len(good)} labels change' + (f'; ambiguous, left alone: {bad}' if bad else ''))
        if good: maps[c] = good
    side = {}   # replay_id -> {player_id: char}
    for rid, p1, p2, c1, c2 in con.execute('select replay_id, p1_player_id, p2_player_id, p1_char, p2_char from games'):
        side[rid] = {p1: c1, p2: c2}
    n = {}
    def bump(k): n[k] = n.get(k, 0) + 1
    for hid, ac, vc, st, vm in con.execute('select hit_id, attacker_char, victim_char, starter, victim_move from hits').fetchall():
        s2 = relabel(maps.get(ac, {}), st); v2 = relabel(maps.get(vc, {}), vm)
        if (s2, v2) != (st, vm):
            bump('hits'); dry or con.execute('update hits set starter=?, victim_move=? where hit_id=?', (s2, v2, hid))
    for tid, rid, pid, act in con.execute('select timing_id, replay_id, player_id, action from timings').fetchall():
        m = maps.get(side.get(rid, {}).get(pid), {})
        if m and act:
            a2 = re.sub(r'^([a-z]+: )(.*)$', lambda x: x.group(1) + relabel(m, x.group(2)), act)
            if a2 != act: bump('timings'); dry or con.execute('update timings set action=? where timing_id=?', (a2, tid))
    for rowid, rid, pid, sup in con.execute('select rowid, replay_id, player_id, supers from resources').fetchall():
        m = maps.get(side.get(rid, {}).get(pid), {})
        if m and sup:
            s2 = re.sub(r'(L\d )(.+?)( \(\d+ bars)', lambda x: x.group(1) + relabel(m, x.group(2)) + x.group(3), sup)
            if s2 != sup: bump('resources'); dry or con.execute('update resources set supers=? where rowid=?', (s2, rowid))
    rows = con.execute('select set_key, replay_id, player_id, move, n from usage').fetchall()
    merged, changed = {}, False
    for sk, rid, pid, mv, cnt in rows:
        m2 = relabel(maps.get(side.get(rid, {}).get(pid), {}), mv)
        if m2 != mv: changed = True; bump('usage')
        key = (rid, pid, m2)
        if key in merged: merged[key][4] += cnt
        else: merged[key] = [sk, rid, pid, m2, cnt]
    if changed and not dry:
        con.execute('delete from usage')
        con.executemany('insert into usage values (?,?,?,?,?)', [tuple(v) for v in merged.values()])
    if not dry: con.commit()
    print(('would change ' if dry else 'changed ') + (', '.join(f'{k} {v}' for k, v in n.items()) or 'nothing'))


if __name__ == '__main__':
    main()
