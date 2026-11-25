"""Tab-style views of sf6.db (set metrics, player reads, opponents, character matchups) as JSON. Formerly fed the retired Replay Tracker sheet; overview_from_db.py imports its move-name helper.

  python sf6db_export.py DB OUTDIR      -> OUTDIR/<tab>.json, each {"header": [...], "rows": [[...], ...]}

Tabs: set_metrics, player_reads, opponents, char_matchups (only sets where the focus player is "me" in settings).
"""
import json, os, sqlite3, sys, collections as C

LEAKS = [('Counter-hit at mid range', 'Counter-hit at mid range'), ('Whiff punished', 'Whiff punished'), ('Walked in', 'Walked in'), ('Jumped', 'Jumped'),
         ('Challenging pressure', 'Challenging pressure'), ('Challenging okizeme', 'Challenging okizeme'), ('Unsafe move punished', 'Unsafe move punished'), ('Pressed after turn ended', 'Pressed after turn ended'),
         ('Blocking, opened up', 'Opened up while blocking'), ('Jumped in on (no anti-air)', "Jump-ins not anti-aired")]


ACTS = {'atck': 'pressed a button', 'nothing (30f)': 'held still', 'special': 'special', 'super': 'super', 'jump': 'jumped',
        'parry': 'Drive Parry', 'dash': 'dashed', 'throw': 'throw'}
RAW = {'SOMERSAULT': 'Somersault Kick', 'SONICBOOM': 'Sonic Boom', 'SONIC_BOOM': 'Sonic Boom'}


def mv(n):
    """Readable move name for analyzer names the special-move tables don't cover yet (e.g. SOMERSAULT_Start)."""
    if not n: return n
    import re as _re
    m_ = _re.match(r'(.+?)_(OD|EX)$', n)
    if m_: return mv(m_.group(1)) + ' (OD)'
    base = n.replace('_Start', '').replace('_START', '')
    if base in RAW: return RAW[base]
    if base.isupper() and len(base) > 3: return base.replace('_', ' ').title()
    return n


def q(con, sql, *a):
    cur = con.execute(sql, a); cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def stats(con, set_key, pid):
    return {r['metric']: r['value'] for r in q(con, 'SELECT metric, value FROM set_stats WHERE set_key=? AND player_id=?', set_key, pid)}


def pct(v):
    return None if v is None else round(v * 100)


def export(db):
    con = sqlite3.connect(db)
    me_name = q(con, "SELECT value FROM settings WHERE key='me'")[0]['value']
    me = q(con, 'SELECT player_id FROM players WHERE name=?', me_name)[0]['player_id']
    sets = q(con, '''SELECT s.*, v.played_at, o.name AS opponent, o.cfn_id AS opp_cfn
                     FROM sets s JOIN v_sets v USING(set_key) JOIN players o ON o.player_id = s.opp_player_id
                     WHERE s.focus_player_id = ? ORDER BY v.played_at, s.set_key''', me)
    T = {}

    # ---- Set Metrics: one row per set, the numbers that matter for trends
    H = ['Date', 'Time', 'Set', 'Opponent', 'Opp CFN ID', 'My char', 'Opp char', 'Result', 'Games', 'Rounds', 'Review', 'My MR', 'Opp rank / MR',
         'Dealt', 'Taken', 'Anti-airs (me)', 'Anti-airs (opp)', 'Counter hits (me)', 'Counter hits (opp)', 'Throws (me)', 'Throws (opp)',
         'Throw techs (me)', 'Burnouts (me)', 'Burnouts (opp)', 'Raw DR (me)', 'Pressure DR (me)', 'Combo DR (me)', 'Raw DR (opp)',
         'After block: press %', 'After block: frame-0 press %', 'After block: hold %'] + [f'% taken: {n}' for _, n in LEAKS] + ['Missing games', 'Note']
    R = []
    for s in sets:
        a, b = stats(con, s['set_key'], me), stats(con, s['set_key'], s['opp_player_id'])
        g = q(con, 'SELECT * FROM games WHERE set_key=? ORDER BY game_no', s['set_key'])
        rw = sum(w == me_name for x in g for w in (x['round_winners'] or '').split(', '))
        rl = sum(w and w != me_name for x in g for w in (x['round_winners'] or '').split(', '))
        # opponent's rank label (rank.py): '<MR> MR', 'MR unknown' or the league below Master; falls back to a bare MR for old captures
        _ol = [(x['p2_rank'] if x['p1_player_id'] == me else x['p1_rank']) or None for x in g]
        _om = next((x['p2_mr'] if x['p1_player_id'] == me else x['p1_mr'] for x in g if (x['p2_mr'] if x['p1_player_id'] == me else x['p1_mr'])), None)
        oppmr = next((l for l in _ol if l and l != 'MR unknown'), None) or next((l for l in _ol if l), None) or (f'{_om} MR' if _om else None)
        ab = a.get('after_block_n') or 0
        R.append([s['played_date'], (s['played_at'] or '').split(' ')[-1] or None, s['set_key'].replace('_', ', '), s['opponent'], s['opp_cfn'],
                  s['focus_char'], s['opp_char'], 'Won' if s['winner_player_id'] == me else 'Lost', f"'{s['focus_games']}-{s['opp_games']}", f"'{rw}-{rl}",
                  s['review'], s['focus_mr_start'], oppmr, a.get('damage_dealt'), a.get('damage_taken'), a.get('anti_airs'), b.get('anti_airs'),
                  (a.get('counter_hits') or 0) + (a.get('punish_counters') or 0), (b.get('counter_hits') or 0) + (b.get('punish_counters') or 0),
                  a.get('throws'), b.get('throws'), a.get('throw_techs'), a.get('burnouts'), b.get('burnouts'), a.get('raw_drive_rush'),
                  a.get('pressure_drive_rush_cancel'), a.get('combo_drive_rush_cancel'), b.get('raw_drive_rush'),
                  round(100 * a.get('after_block_attack', 0) / ab) if ab else None, round(100 * a.get('after_block_attack_f0', 0) / ab) if ab else None,
                  round(100 * a.get('after_block_hold', 0) / ab) if ab else None]
                 + [pct(a.get('taken_share: ' + k, 0)) for k, _ in LEAKS] + [s['games_missing'] or None, s['note']])
    T['set_metrics'] = (H, R)

    # ---- Player Reads: both players, every set
    H = ['Date', 'Set', 'Player', 'Role', 'Character', 'Archetype', 'Lean', 'Confidence', 'Evidence', 'How to beat it / what it costs', 'Source']
    R = []
    for s in sets:
        for r in q(con, 'SELECT r.*, p.name FROM reads r JOIN players p USING(player_id) WHERE set_key=? ORDER BY r.player_id != ?', s['set_key'], me):
            R.append([s['played_date'], s['set_key'].replace('_', ', '), r['name'], 'Me' if r['player_id'] == me else 'Opponent', r['character'],
                      r['archetype'], r['lean'], r['confidence'], r['evidence'], r['counter_note'], r['source']])
    T['player_reads'] = (H, R)

    # ---- Opponents: one row per player
    H = ['Opponent', 'CFN ID', 'Characters', 'Sets', 'Sets won', 'Sets lost', 'Games won', 'Games lost', 'Last played', 'Their rank / MR (latest)',
         'Latest read', 'Their top damage vs me', 'After blocking (their first action)', 'Repeated habits (2+ sets)', 'Past names']
    R = []
    by_opp = C.defaultdict(list)
    for s in sets: by_opp[s['opp_player_id']].append(s)
    for pid, ss in sorted(sorted(by_opp.items(), key=lambda kv: max(x['played_at'] or '' for x in kv[1]), reverse=True), key=lambda kv: -len(kv[1])):
        name = ss[0]['opponent']; keys = [x['set_key'] for x in ss]
        mk = ','.join('?' * len(keys))
        top = q(con, f'SELECT starter, SUM(damage) d, COUNT(*) n FROM hits WHERE set_key IN ({mk}) AND attacker_id=? GROUP BY starter ORDER BY d DESC LIMIT 3', *keys, pid)
        tim = q(con, f"SELECT action FROM timings WHERE set_key IN ({mk}) AND player_id=? AND event='after block'", *keys, pid)
        acts = C.Counter(t['action'].split(':')[0] for t in tim if not t['action'].startswith('blocked'))
        nact = sum(acts.values())
        rd = q(con, f'SELECT r.archetype, r.lean, r.confidence FROM reads r JOIN v_sets v USING(set_key) WHERE r.set_key IN ({mk}) AND r.player_id=? ORDER BY v.played_at DESC LIMIT 1', *keys, pid)
        hab = q(con, f'SELECT habit, COUNT(DISTINCT set_key) n FROM habits WHERE set_key IN ({mk}) AND player_id=? GROUP BY habit HAVING n >= 2', *keys, pid)
        names = [r['name'] for r in q(con, 'SELECT name FROM player_names WHERE player_id=? AND name != ?', pid, name)]
        mr = q(con, f'SELECT CASE WHEN p1_player_id=? THEN COALESCE(p1_rank, p1_mr || \' MR\') ELSE COALESCE(p2_rank, p2_mr || \' MR\') END mr FROM games g JOIN v_sets v USING(set_key) WHERE g.set_key IN ({mk}) ORDER BY v.played_at DESC, g.game_no DESC', pid, *keys)
        gw = sum(x['focus_games'] for x in ss); gl = sum(x['opp_games'] for x in ss)
        R.append([name, ss[0]['opp_cfn'], ', '.join(sorted({x['opp_char'] for x in ss})), len(ss), sum(x['winner_player_id'] == me for x in ss),
                  sum(x['winner_player_id'] != me for x in ss), gw, gl, max(x['played_date'] or '' for x in ss) or None,
                  next((m['mr'] for m in mr if m['mr']), None),
                  f"{rd[0]['archetype']} ({rd[0]['lean']}), {rd[0]['confidence']}" if rd else None,
                  '; '.join(f"{mv(t['starter'])} {t['d']:,} ({t['n']})" for t in top) or None,
                  ', '.join(f"{ACTS.get(k, k)} {round(100 * v / nact)}%" for k, v in acts.most_common(3)) if nact else None,
                  '; '.join(h['habit'] for h in hab) or None, ', '.join(names) or None])
    T['opponents'] = (H, R)

    # ---- Character matchups: my character vs theirs, every opponent
    H = ['My char', 'Opp char', 'Sets', 'Sets won', 'Sets lost', 'Games won', 'Games lost', 'Opponents', 'Last played',
         'Anti-airs (me / opp)', 'Counter hits (me / opp)', 'Raw DR (me / opp)', 'Biggest leaks (% of damage taken)', 'Their top damage vs me']
    R = []
    by_mu = C.defaultdict(list)
    for s in sets: by_mu[(s['focus_char'], s['opp_char'])].append(s)
    for (mc, oc), ss in sorted(by_mu.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        keys = [x['set_key'] for x in ss]; mk = ','.join('?' * len(keys))
        A = C.Counter(); B = C.Counter()
        for x in ss:
            A.update(stats(con, x['set_key'], me)); B.update(stats(con, x['set_key'], x['opp_player_id']))
        lens = q(con, f'SELECT lens, SUM(damage) d FROM hits WHERE set_key IN ({mk}) AND victim_id=? GROUP BY lens ORDER BY d DESC', *keys, me)
        tot = sum(l['d'] for l in lens) or 1
        top = q(con, f'SELECT starter, SUM(damage) d, COUNT(*) n FROM hits WHERE set_key IN ({mk}) AND victim_id=? GROUP BY starter ORDER BY d DESC LIMIT 3', *keys, me)
        R.append([mc, oc, len(ss), sum(x['winner_player_id'] == me for x in ss), sum(x['winner_player_id'] != me for x in ss),
                  sum(x['focus_games'] for x in ss), sum(x['opp_games'] for x in ss), ', '.join(sorted({x['opponent'] for x in ss})),
                  max(x['played_date'] or '' for x in ss) or None,
                  f"{int(A['anti_airs'])} / {int(B['anti_airs'])}", f"{int(A['counter_hits'] + A['punish_counters'])} / {int(B['counter_hits'] + B['punish_counters'])}",
                  f"{int(A['raw_drive_rush'])} / {int(B['raw_drive_rush'])}",
                  '; '.join(f"{l['lens'] or 'Unclear / super'} {round(100 * l['d'] / tot)}%" for l in lens[:3]),
                  '; '.join(f"{mv(t['starter'])} {t['d']:,} ({t['n']})" for t in top)])
    T['char_matchups'] = (H, R)
    return T


if __name__ == '__main__':
    db, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for k, (h, r) in export(db).items():
        json.dump({'header': h, 'rows': r}, open(f'{out}/{k}.json', 'w'), ensure_ascii=False)
        print(k, len(r), 'rows x', len(h))
