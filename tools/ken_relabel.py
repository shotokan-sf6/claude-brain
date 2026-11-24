"""One-off (2026-11-24): bring Ken's move labels in an existing sf6.db up to the analyzer's new names, without re-ingesting.
Touches only machine-written fields of the Ken player in games where Ken played: hits.starter (Ken attacking),
hits.victim_move (Ken being hit), timings.action, resources.supers and usage.move (merged where two old labels
become one). Hand-written text (reads, habits, review_docs) is left as written.

  python ken_relabel.py DB [--dry]
"""
import re, sqlite3, sys

EXACT = {'HK_SHIDEN': 'Quick Dash > Thunder Kick', 'MK_FUMIKOMI': 'Quick Dash > Forward Step Kick',
         '5MP_HP': 'Chin Buster (5MP~HP)', '5MK_MK_HK': 'Triple Flash Kick (5MK~MK~HK)', '5MK_MK': 'Triple Flash Kick (5MK~MK)',
         'KK_LK_FUNJIN_STOP': 'Quick Dash > Emergency Stop', 'KK_LK_FUNJIN': 'Quick Dash'}
FOLLOW = {'L': 'Kazekama Shin Kick', 'M': 'Gorai Axe Kick', 'H': 'Senka Snap Kick'}
PREFIX = [('Super RYUBI', 'SA1 Dragonlash Flame'), ('Super 2_SippuJinrai', 'SA2 Shippu Jinrai-kyaku'),
          ('Super SHINRYUREPPA', 'SA3 Shinryu Reppa'), ('Critical Art SHINRYUREPPA', 'Critical Art (Shinryu Reppa)')]


def new(label):
    if label is None: return label
    if label in EXACT: return EXACT[label]
    m = re.fullmatch(r'Jinrai Kick \((L|M|H)\)( \(OD\))?', label)
    if m: return FOLLOW[m.group(1)] + (m.group(2) or '')
    for k, v in PREFIX:
        if label.startswith(k): return v
    return label


def supers_text(s):
    if not s: return s
    for k, v in PREFIX:
        s = re.sub(re.escape(k) + r'[A-Za-z_0-9]*', v, s)
    return s


def main(db, dry):
    con = sqlite3.connect(db)
    ken = {}   # replay_id -> Ken's player_ids
    for rid, p1, p2, c1, c2 in con.execute('select replay_id, p1_player_id, p2_player_id, p1_char, p2_char from games'):
        ids = {p for p, c in ((p1, c1), (p2, c2)) if c == 'Ken'}
        if ids: ken[rid] = ids
    n = {}
    def bump(k): n[k] = n.get(k, 0) + 1
    for hid, rid, att, vic, st, vm in con.execute('select hit_id, replay_id, attacker_id, victim_id, starter, victim_move from hits').fetchall():
        k = ken.get(rid, set())
        s2 = new(st) if att in k else st
        v2 = new(vm) if vic in k else vm
        if (s2, v2) != (st, vm):
            bump('hits'); dry or con.execute('update hits set starter=?, victim_move=? where hit_id=?', (s2, v2, hid))
    for tid, rid, pid, act in con.execute('select timing_id, replay_id, player_id, action from timings').fetchall():
        if pid in ken.get(rid, set()) and act:
            a2 = re.sub(r'([a-z]+: )(.*)', lambda m: m.group(1) + new(m.group(2)), act)
            if a2 != act: bump('timings'); dry or con.execute('update timings set action=? where timing_id=?', (a2, tid))
    for rowid, rid, pid, sup in con.execute('select rowid, replay_id, player_id, supers from resources').fetchall():
        if pid in ken.get(rid, set()):
            s2 = supers_text(sup)
            if s2 != sup: bump('resources'); dry or con.execute('update resources set supers=? where rowid=?', (s2, rowid))
    rows = con.execute('select set_key, replay_id, player_id, move, n from usage').fetchall()
    merged, changed = {}, False
    for sk, rid, pid, mv, cnt in rows:
        m2 = new(mv) if pid in ken.get(rid, set()) else mv
        if m2 != mv: changed = True; bump('usage')
        key = (rid, pid, m2)
        if key in merged: merged[key][4] += cnt
        else: merged[key] = [sk, rid, pid, m2, cnt]
    if changed and not dry:
        con.execute('delete from usage')
        con.executemany('insert into usage values (?,?,?,?,?)', [tuple(v) for v in merged.values()])
    if not dry: con.commit()
    print(('would change ' if dry else 'changed ') + ', '.join(f'{k} {v}' for k, v in n.items()) + f' (Ken in {len(ken)} games)')


if __name__ == '__main__':
    main(sys.argv[1], '--dry' in sys.argv)
