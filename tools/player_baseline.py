"""Personal baseline: how the configured player played in each set compared with their own recent sets.

  python player_baseline.py DB [--days 7]

For every set of the configured player (settings 'me', else shotokan.json), the baseline of each metric is the
median over their sets that started in the previous --days days (default 7) before this one. Same-day sets count
when their start time is known and earlier. Stored in the player_baseline table, one row per set and metric:
value, baseline, n_sets (how many sets the baseline uses), delta (value - baseline) and, for the eight spectra,
delta_score (the 1-5 score of the value minus the score the baseline would get on the same scale).

Metrics: the eight spectra (raw values from spectra_raw) and per-game / per-round stats from set_stats. The
spectra compare a player with everyone else (spectra_calibrate.py); this compares them with themselves.
shared_core_db.py ingest and spectra_calibrate.py run it.
"""
import datetime, os, sqlite3, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spectra as SP

STATS = [  # (metric, label, numerator, denominator)  denominator 'games' = per game
    ('counter_hits_pg', 'Counter hits per game', 'counter_hits', 'games'),
    ('punish_counters_pg', 'Punish counters per game', 'punish_counters', 'games'),
    ('throws_pg', 'Throws landed per game', 'throws', 'games'),
    ('throw_techs_pg', 'Throw techs per game', 'throw_techs', 'games'),
    ('anti_airs_pg', 'Anti-airs per game', 'anti_airs', 'games'),
    ('raw_drive_rush_pg', 'Raw Drive Rushes per game', 'raw_drive_rush', 'games'),
    ('combo_drive_rush_cancel_pg', 'Combo Drive Rush cancels per game', 'combo_drive_rush_cancel', 'games'),
    ('pressure_drive_rush_cancel_pg', 'Pressure Drive Rush cancels per game', 'pressure_drive_rush_cancel', 'games'),
    ('burnouts_pg', 'Burnouts per game', 'burnouts', 'games'),
    ('decision_presses_pr', 'Decision presses per round', 'decision_presses', 'press_rounds'),
    ('damage_per_press', 'Damage per decision press', 'damage_dealt', 'decision_presses'),
    ('after_block_press_f0', 'Pressed on the first free frame after blocking', 'after_block_attack_f0', 'after_block_n'),
    ('wake_up_attack', 'Pressed a button on wake-up', 'wake_up_attack', 'wake_up_n'),
    ('wake_up_hold', 'Held block on wake-up', 'wake_up_hold', 'wake_up_n'),
    ('oki_damage_share', 'Share of damage taken on wake-up', 'taken_situation_share: oki', None),
]


def _start(con, key, date):
    t = con.execute('select min(played_time) from games where set_key=? and played_time is not null', (key,)).fetchone()[0]
    try:
        return datetime.datetime.fromisoformat(t.replace(' ', 'T')[:16]), True
    except Exception:
        return datetime.datetime.fromisoformat(date), False   # date only: counts as the start of that day


def update(db, days=7):
    con = sqlite3.connect(db)
    import spectra_calibrate as CAL
    me = CAL.me_id(con)
    if me is None:
        print('player_baseline: no configured player, skipped'); return 0
    SP.load_cuts(con)
    con.execute("""CREATE TABLE IF NOT EXISTS player_baseline (set_key TEXT, player_id INTEGER, metric TEXT, label TEXT,
        value REAL, baseline REAL, n_sets INTEGER, delta REAL, delta_score INTEGER, window_days INTEGER,
        PRIMARY KEY (set_key, player_id, metric))""")
    sets = con.execute('select set_key, played_date from sets where focus_player_id=? or opp_player_id=?', (me, me)).fetchall()
    starts = {k: _start(con, k, d) for k, d in sets}
    vals = {}
    for k, _ in sets:
        st = {m: v for m, v in con.execute('select metric, value from set_stats where set_key=? and player_id=?', (k, me))}
        row = {}
        for m, _, num, den in STATS:
            if den is None: row[m] = st.get(num)
            elif den == 'games': row[m] = (st.get(num, 0) / st['games']) if st.get('games') else None
            else: row[m] = (st.get(num, 0) / st[den]) if st.get(den) else None
        for ax, raw in con.execute('select axis_key, raw from spectra_raw where set_key=? and player_id=?', (k, me)):
            row['spectrum: ' + ax] = raw
        vals[k] = row
    labels = dict((m, l) for m, l, _, _ in STATS)
    labels.update({'spectrum: ' + a['key']: a['axis'] for a in SP.AXES})
    con.execute('DELETE FROM player_baseline WHERE player_id=?', (me,))
    n = 0
    for k, _ in sets:
        t0, timed = starts[k]
        lo = t0 - datetime.timedelta(days=days)
        prev = [j for j, _ in sets if j != k and lo <= starts[j][0] < t0 and (timed and starts[j][1] or starts[j][0].date() < t0.date())]
        for m, v in vals[k].items():
            hist = [vals[j][m] for j in prev if vals[j].get(m) is not None]
            base = statistics.median(hist) if hist else None
            delta = (v - base) if (v is not None and base is not None) else None
            ds = None
            if m.startswith('spectrum: ') and delta is not None:
                ax = m[len('spectrum: '):]
                ds = SP.score(ax, v) - SP.score(ax, base)
            con.execute('INSERT OR REPLACE INTO player_baseline VALUES (?,?,?,?,?,?,?,?,?,?)',
                        (k, me, m, labels.get(m, m), v, base, len(hist), delta, ds, days))
            n += 1
    con.commit()
    print(f'player_baseline: {len(sets)} sets, {n} rows ({days}-day window)')
    return n


if __name__ == '__main__':
    d = int(sys.argv[sys.argv.index('--days') + 1]) if '--days' in sys.argv else 7
    update(sys.argv[1], d)
