"""SF6 review history database (SQLite).

One file (D:\\SF6-Claude-Coaching\\history\\sf6.db) holding every reviewed set: players (CFN ID + names),
sets, games, the analyzer's hits / events / timings, per-set stats, player reads, habits and matchup notes.

  python shared_core_db.py init  DB
  python shared_core_db.py ingest DB ANALYZER_OUTDIR META.json      # one set; META describes it (see ingest_set); also
                                                          # computes its spectra (spectra_backfill.py), --no-spectra to skip,
                                                          # and refreshes the personal baseline (player_baseline.py)
  python shared_core_db.py sql   DB "SELECT ..."                   # ad-hoc query, prints rows
  python shared_core_db.py mr    DB [SETKEY ...]                  # MR change per game and MR after each ranked set (sfbuff's Elo, K=16);
                                                          # ingest does this for its set. Warns when MR says the games are out of order
  python shared_core_db.py odds  DB MY_MR OPP_MR                  # MR at stake (win / loss), game and FT2 / FT3 win chances from the MR gap
  python shared_core_db.py predict DB PREDICTION.json [--replace]  # store a blind prediction BEFORE the analyzer runs
  python shared_core_db.py history DB --opp NAME|CFN [--opp-char C] [--player NAME|CFN (default: shotokan.json)] [--my-char C] [--before ISO] [--exclude ID,ID]
                                                          # pre-set history for a prediction, only from earlier sets

Blind predictions: build the pre-set facts with shared_core_blind_manifest.py (no results, no later MR), gather history with
`history` (only sets before the one predicted), write PREDICTION.json and store it with `predict` before running the
analyzer. `predict` refuses a set whose games are already in the database, and a stored prediction can't be replaced
once its set is ingested. Ingest links the prediction to its set and records the grade from review_docs.prediction.

Re-ingesting a set replaces it (same set_key), so a set can be re-analysed without duplicates.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import rank as RANK
import json, os, sqlite3, sys, datetime, collections as C

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS players (
  player_id INTEGER PRIMARY KEY, cfn_id TEXT UNIQUE, name TEXT NOT NULL, first_seen TEXT, last_seen TEXT);
CREATE TABLE IF NOT EXISTS player_names (
  player_id INTEGER REFERENCES players, name TEXT, first_seen TEXT, last_seen TEXT, PRIMARY KEY (player_id, name));
CREATE TABLE IF NOT EXISTS sets (
  set_key TEXT PRIMARY KEY, played_date TEXT, ranked INTEGER, format TEXT, review TEXT,
  focus_player_id INTEGER REFERENCES players, opp_player_id INTEGER REFERENCES players,
  focus_char TEXT, opp_char TEXT, focus_games INTEGER, opp_games INTEGER, winner_player_id INTEGER REFERENCES players,
  focus_mr_start INTEGER, games_missing INTEGER DEFAULT 0, note TEXT, dashboard TEXT, analyzer TEXT, ingested_at TEXT);
CREATE TABLE IF NOT EXISTS player_flags (
  player_id INTEGER REFERENCES players, flag TEXT, note TEXT, added TEXT, PRIMARY KEY (player_id, flag));
CREATE TABLE IF NOT EXISTS games (
  replay_id TEXT PRIMARY KEY, set_key TEXT REFERENCES sets ON DELETE CASCADE, game_no INTEGER, played_time TEXT,
  p1_player_id INTEGER REFERENCES players, p2_player_id INTEGER REFERENCES players, p1_char TEXT, p2_char TEXT,
  p1_control INTEGER, p2_control INTEGER, p1_mr INTEGER, p2_mr INTEGER,
  winner_player_id INTEGER REFERENCES players, round_score TEXT, round_winners TEXT, capture_file TEXT,
  p1_lp INTEGER, p2_lp INTEGER, p1_rank TEXT, p2_rank TEXT);   -- rank: league below Master, '<MR> MR' or 'MR unknown' at Master (rank.py)
-- games also get p1_mr_change, p2_mr_change, mr_change_source and sets opp_mr_start, focus_mr_end, opp_mr_end (added in connect(); see mr_changes())
CREATE TABLE IF NOT EXISTS hits (
  hit_id INTEGER PRIMARY KEY, set_key TEXT REFERENCES sets ON DELETE CASCADE, replay_id TEXT, round INTEGER, round_timer INTEGER,
  attacker_id INTEGER, victim_id INTEGER, attacker_char TEXT, victim_char TEXT, damage INTEGER, starter TEXT, hits_in_combo INTEGER,
  hit_kind TEXT, anti_air INTEGER, situation TEXT, lens TEXT, victim_state TEXT, victim_move TEXT, note TEXT,
  drive_spent REAL, super_spent REAL, drive_gained REAL, drive_damage REAL, knockdown TEXT, kd_adv INTEGER, corner_dist REAL, victim_drive_after REAL, recoverable INTEGER, white_cashed INTEGER);
CREATE TABLE IF NOT EXISTS events (
  event_id INTEGER PRIMARY KEY, set_key TEXT REFERENCES sets ON DELETE CASCADE, replay_id TEXT, round INTEGER, round_timer INTEGER,
  player_id INTEGER, type TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS timings (
  timing_id INTEGER PRIMARY KEY, set_key TEXT REFERENCES sets ON DELETE CASCADE, replay_id TEXT, round INTEGER, round_timer INTEGER,
  player_id INTEGER, event TEXT, action TEXT, frames_until INTEGER);
CREATE TABLE IF NOT EXISTS resources (            -- Drive / super spent per player per round, by category (bars; 1 bar = 10,000)
  set_key TEXT REFERENCES sets ON DELETE CASCADE, replay_id TEXT, round INTEGER, player_id INTEGER,
  drive_rush REAL, drive_parry REAL, drive_impact REAL, drive_reversal REAL, od_specials REAL, drive_other REAL, drive_total REAL,
  super_bars REAL, supers TEXT, burnouts INTEGER, drive_end REAL, super_end REAL,
  gain_hit REAL, gain_block REAL, parry_regain REAL, loss_block REAL, loss_hit REAL, loss_hit_drive_impact REAL, loss_hit_punish_counter REAL,
  drive_rush_cancel REAL,                         -- part of drive_rush spent on combo / pressure cancels (the rest is raw)
  PRIMARY KEY (replay_id, round, player_id));
CREATE TABLE IF NOT EXISTS parries (              -- each Drive Parry: cost, hits parried, Drive regained, perfect, what happened next
  set_key TEXT REFERENCES sets ON DELETE CASCADE, replay_id TEXT, round INTEGER, round_timer INTEGER, player_id INTEGER,
  frames INTEGER, drive_before REAL, cost REAL, hits_parried INTEGER, regained REAL, net REAL, perfect INTEGER, next TEXT);
CREATE TABLE IF NOT EXISTS punish_windows (       -- defender left blockstun with the attacker still recovering by 5+ frames
  set_key TEXT REFERENCES sets ON DELETE CASCADE, replay_id TEXT, round INTEGER, round_timer INTEGER, defender_id INTEGER, attacker_id INTEGER,
  move TEXT, adv INTEGER, distance REAL, range TEXT, result TEXT, action TEXT, wiki_adv INTEGER, check_note TEXT);
CREATE TABLE IF NOT EXISTS set_stats (            -- long format: one row per set, player and metric, for trends
  set_key TEXT REFERENCES sets ON DELETE CASCADE, player_id INTEGER, metric TEXT, value REAL, PRIMARY KEY (set_key, player_id, metric));
CREATE TABLE IF NOT EXISTS reads (
  set_key TEXT REFERENCES sets ON DELETE CASCADE, player_id INTEGER, character TEXT, archetype TEXT, lean TEXT, confidence TEXT,
  evidence TEXT, counter_note TEXT, risk_tolerance TEXT, temperament TEXT, source TEXT, PRIMARY KEY (set_key, player_id));
CREATE TABLE IF NOT EXISTS habits (
  habit_row INTEGER PRIMARY KEY, set_key TEXT REFERENCES sets ON DELETE CASCADE, player_id INTEGER, kind TEXT, area TEXT, habit TEXT,
  seen TEXT, times INTEGER, fix TEXT, confidence TEXT, source TEXT);
CREATE TABLE IF NOT EXISTS matchup_notes (        -- scope 'character' (my_char vs opp_char) or 'player' (me vs opp_player)
  note_id INTEGER PRIMARY KEY, scope TEXT, my_char TEXT, opp_char TEXT, opp_player_id INTEGER, kind TEXT, note TEXT,
  seen_in TEXT, status TEXT, created TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS usage (            -- move usage per game and player, from the analyzer report
  set_key TEXT REFERENCES sets ON DELETE CASCADE, replay_id TEXT, player_id INTEGER, move TEXT, n INTEGER,
  PRIMARY KEY (replay_id, player_id, move));
CREATE TABLE IF NOT EXISTS review_docs (      -- hand-written Full-review content per set and dashboard dataset (kept across re-ingests)
  set_key TEXT, dataset TEXT, rows TEXT, updated TEXT, PRIMARY KEY (set_key, dataset));
CREATE TABLE IF NOT EXISTS dashboard_sets (   -- stable "Set N" numbering per dashboard
  dashboard TEXT, set_key TEXT, set_no INTEGER, PRIMARY KEY (dashboard, set_key));
CREATE INDEX IF NOT EXISTS ix_hits_set ON hits(set_key); CREATE INDEX IF NOT EXISTS ix_hits_victim ON hits(victim_id, lens);
CREATE INDEX IF NOT EXISTS ix_sets_opp ON sets(opp_player_id); CREATE INDEX IF NOT EXISTS ix_sets_chars ON sets(focus_char, opp_char);
CREATE TABLE IF NOT EXISTS predictions (          -- blind pre-set predictions, stored before the analyzer runs (shared_core_db.py predict)
  prediction_id INTEGER PRIMARY KEY, replay_ids TEXT NOT NULL UNIQUE, set_key TEXT, written_at TEXT NOT NULL, stored_at TEXT NOT NULL,
  manifest TEXT, body TEXT NOT NULL, grade TEXT, graded_at TEXT);
CREATE TABLE IF NOT EXISTS game_stats (           -- same metrics as set_stats, per game, with the character played in that game
  set_key TEXT REFERENCES sets ON DELETE CASCADE, replay_id TEXT, player_id INTEGER, character TEXT, metric TEXT, value REAL,
  PRIMARY KEY (replay_id, player_id, metric));
CREATE INDEX IF NOT EXISTS ix_stats_metric ON set_stats(metric, player_id);
CREATE INDEX IF NOT EXISTS ix_game_stats_char ON game_stats(player_id, character, metric);

-- views: who you play and which matchups
CREATE VIEW IF NOT EXISTS v_sets AS
  SELECT s.set_key, s.played_date, s.played_date || ' ' || COALESCE((SELECT MIN(played_time) FROM games g WHERE g.set_key = s.set_key), '') AS played_at, s.ranked, s.review, f.name AS focus, s.focus_char, o.name AS opponent, o.cfn_id AS opp_cfn_id, s.opp_char,
         s.focus_games || '-' || s.opp_games AS score, CASE WHEN s.winner_player_id = s.focus_player_id THEN 'W' ELSE 'L' END AS result,
         s.focus_mr_start, s.games_missing, s.note
  FROM sets s JOIN players f ON f.player_id = s.focus_player_id JOIN players o ON o.player_id = s.opp_player_id;
CREATE VIEW IF NOT EXISTS v_player_matchups AS
  SELECT focus, opponent, opp_cfn_id, COUNT(*) AS sets, SUM(result = 'W') AS sets_won, SUM(result = 'L') AS sets_lost,
         GROUP_CONCAT(DISTINCT opp_char) AS their_chars, GROUP_CONCAT(DISTINCT focus_char) AS my_chars, MAX(played_date) AS last_played
  FROM v_sets GROUP BY focus, opponent;
CREATE VIEW IF NOT EXISTS v_char_matchups AS
  SELECT focus, focus_char, opp_char, COUNT(*) AS sets, SUM(result = 'W') AS sets_won, SUM(result = 'L') AS sets_lost,
         COUNT(DISTINCT opponent) AS opponents, MAX(played_date) AS last_played
  FROM v_sets GROUP BY focus, focus_char, opp_char;
"""

DR_TYPES = ('raw drive rush', 'pressure drive rush cancel', 'combo drive rush cancel', 'whiff drive rush cancel')


def connect(db):
    con = sqlite3.connect(db)
    con.execute('PRAGMA foreign_keys = ON')
    con.executescript(SCHEMA)
    for t, cols in (('games', 'p1_lp INTEGER, p2_lp INTEGER, p1_rank TEXT, p2_rank TEXT'), ('hits', 'drive_spent REAL, super_spent REAL, drive_gained REAL, drive_damage REAL, knockdown TEXT, kd_adv INTEGER, corner_dist REAL, victim_drive_after REAL, recoverable INTEGER, white_cashed INTEGER'),
                    ('resources', 'gain_hit REAL, gain_block REAL, parry_regain REAL, loss_block REAL, loss_hit REAL, loss_hit_drive_impact REAL, loss_hit_punish_counter REAL, drive_rush_cancel REAL'),
                    ('games', 'p1_mr_change INTEGER, p2_mr_change INTEGER, mr_change_source TEXT'),
                    ('sets', 'opp_mr_start INTEGER, focus_mr_end INTEGER, opp_mr_end INTEGER, reviewed_at TEXT, excluded TEXT')):
        have = {r[1] for r in con.execute(f'PRAGMA table_info({t})')}
        for c_ in cols.split(', '):
            if c_.split()[0] not in have: con.execute(f'ALTER TABLE {t} ADD COLUMN {c_}')   # older databases
    # reviewed_at: when a set was first reviewed (ISO time) (kept across re-ingests, unlike ingested_at). Sets from before the
    # column existed take their ingest date, else 2026-11-26.
    con.execute("UPDATE sets SET reviewed_at = COALESCE(ingested_at, '2026-11-26') WHERE reviewed_at IS NULL")
    con.commit()
    return con


def player(con, name, cfn_id=None, seen=None):
    """Find or create a player: by CFN ID when known, else by current name. Records name changes."""
    cur = con.cursor()
    row = None
    if cfn_id:
        row = cur.execute('SELECT player_id, name FROM players WHERE cfn_id = ?', (cfn_id,)).fetchone()
        if not row:  # a player first stored by name only, now seen with an ID
            row = cur.execute('SELECT player_id, name FROM players WHERE name = ? AND cfn_id IS NULL', (name,)).fetchone()
            if row: cur.execute('UPDATE players SET cfn_id = ? WHERE player_id = ?', (cfn_id, row[0]))
    if not row:
        row = cur.execute('SELECT player_id, name FROM players WHERE name = ? ORDER BY cfn_id IS NULL LIMIT 1', (name,)).fetchone()
    if not row:
        cur.execute('INSERT INTO players (cfn_id, name, first_seen, last_seen) VALUES (?, ?, ?, ?)', (cfn_id, name, seen, seen))
        pid = cur.lastrowid
    else:
        pid = row[0]
        if seen:
            cur.execute('UPDATE players SET name = ?, last_seen = MAX(COALESCE(last_seen, ?), ?), first_seen = MIN(COALESCE(first_seen, ?), ?) WHERE player_id = ?',
                        (name, seen, seen, seen, seen, pid))
    cur.execute('INSERT OR IGNORE INTO player_names (player_id, name, first_seen, last_seen) VALUES (?, ?, ?, ?)', (pid, name, seen, seen))
    if seen:
        cur.execute('UPDATE player_names SET last_seen = MAX(COALESCE(last_seen, ?), ?), first_seen = MIN(COALESCE(first_seen, ?), ?) WHERE player_id = ? AND name = ?',
                    (seen, seen, seen, seen, pid, name))
    return pid


def set_stats(hits, events, timings, games, pids, presses=None, pwin=None):
    """Per-player metrics for trend tracking (ints and shares)."""
    out = {}
    for name, pid in pids.items():
        mine = [h for h in hits if h['attacker'] == name]; took = [h for h in hits if h['victim'] == name]
        taken = sum(h['damage'] for h in took) or 0
        m = dict(games=len(games), damage_dealt=sum(h['damage'] for h in mine), damage_taken=taken,
                 counter_hits=sum(h['hit_kind'] == 'counter hit' for h in mine), punish_counters=sum(h['hit_kind'] == 'punish counter' for h in mine),
                 throws=sum(h['hit_kind'] == 'throw' for h in mine), anti_airs=sum(bool(h['anti_air']) for h in mine),
                 burnouts=sum(e['player'] == name and e['type'] == 'burnout' for e in events),
                 throw_techs=sum(e['player'] == name and e['type'] == 'throw tech' for e in events),
                 perfect_parries=sum(e['player'] == name and e['type'] == 'perfect parry' for e in events),
                 drive_reversals=sum(e['player'] == name and e['type'] == 'drive reversal' for e in events))
        if presses:   # button economy (Theory #4): all presses and decision presses (opponent not being hit / knocked down)
            pr = [x for x in presses if x['player'] == name]
            m['presses'] = sum(x['presses'] for x in pr); m['decision_presses'] = sum(x['decision_presses'] for x in pr); m['press_rounds'] = len(pr)
        if pwin is not None:   # block punishes: windows of -5 or worse in reach (close / mid), and how many were punished
            for rg in ('close', 'mid'):
                ws = [x for x in pwin if x['defender'] == name and x['range'] == rg and not (x['check'] or '').startswith('wiki disagrees')]
                m[f'punish_windows_{rg}'] = len(ws); m[f'punishes_landed_{rg}'] = sum(x['result'] == 'punished' for x in ws)
        for t in DR_TYPES:
            m[t.replace(' ', '_')] = sum(e['player'] == name and e['type'] == t for e in events)
        for ev in ('after block', 'wake-up'):
            ts = [t for t in timings if t['player'] == name and t['event'] == ev]
            k = ev.replace(' ', '_').replace('-', '_')
            m[f'{k}_n'] = len(ts)
            m[f'{k}_attack'] = sum(t['action'].split(':')[0] in ('atck', 'special', 'super') for t in ts)
            m[f'{k}_attack_f0'] = sum(t['action'].split(':')[0] in ('atck', 'special', 'super') and (t['frames_until'] or 0) <= 1 for t in ts)
            m[f'{k}_hold'] = sum(t['action'].startswith('nothing') for t in ts)
            m[f'{k}_jump'] = sum(t['action'].startswith('jump') for t in ts)
            m[f'{k}_parry'] = sum(t['action'].startswith('parry') for t in ts)
        lens = C.Counter()
        sit = C.Counter()
        for h in took:
            lens[h['lens'] or 'Unclear / super'] += h['damage']; sit[h['situation']] += h['damage']
        for k, v in lens.items(): m['taken_share: ' + k] = round(v / taken, 4) if taken else 0
        for k, v in lens.items(): m['taken_dmg: ' + k] = v   # raw damage too, so shares can be weighted by how much was taken
        for k, v in sit.items(): m['taken_situation_share: ' + k] = round(v / taken, 4) if taken else 0
        out[pid] = m
    return out


def resource_row(k, r, names):
    b = r['drive_bars']
    return (k, r['game_id'], r['round'], names[r['player']], b.get('Drive Rush'), b.get('Drive Parry'), b.get('Drive Impact'), b.get('Drive Reversal'),
            b.get('OD specials'), b.get('other'), r['drive_total_bars'], r['super_bars'], json.dumps(r['supers']), r['burnouts'],
            round((r['drive_end'] or 0) / 10000, 2), round((r['super_end'] or 0) / 10000, 2),
            r.get('gain_hit'), r.get('gain_block'), r.get('parry_regain'), r.get('loss_block'), r.get('loss_hit'), r.get('loss_hit_drive_impact'), r.get('loss_hit_punish_counter'), r.get('drive_rush_cancel_bars'))


def ingest_set(con, outdir, meta):
    """meta: set_key, focus (name), played_date, ranked, review ('Full'/'Quick'), format, note, dashboard,
    games_missing, game_times [..], focus_mr [..] (per game, optional), reads [rows], habits [rows] (default: review_docs archetypes / habits), source (reads/habits origin),
    review_docs {dataset: rows} (hand-written Full-review content, kept across re-ingests), dash {"dashboard": "quick-dashboard", "set_no": N} (stable Set N)."""
    L = lambda n: json.load(open(os.path.join(outdir, n + '.json')))
    hits, events, timings, games = L('hits'), L('events'), L('timings'), L('games')
    presses = L('presses') if os.path.exists(os.path.join(outdir, 'presses.json')) else None
    infos = {}
    for n, g in enumerate(games):
        infos[g['game_id']] = load_info(meta['captures_local'][g['game_id']])
        for s_ in ('p1', 'p2'):   # names typed in Move Export for ids the game doesn't name (char_names.json)
            c_ = infos[g['game_id']].get(s_ + '_char') or ''
            if c_.startswith('char_') and c_[5:] in (meta.get('char_names') or {}):
                infos[g['game_id']][s_ + '_char'] = meta['char_names'][c_[5:]]
        for s_, c_ in (meta.get('override') or {}).get(g['game_id'], {}).items():   # stale labels in pre-v3.1 captures
            infos[g['game_id']][s_ + '_char'] = c_
        if meta.get('game_numbers'): g['game_no'] = meta['game_numbers'][n]          # e.g. a game missing from the set
    k = meta['set_key']
    cur = con.cursor()
    prev_reviewed, prev_excluded = cur.execute('SELECT reviewed_at, excluded FROM sets WHERE set_key = ?', (k,)).fetchone() or (None, None)
    cur.execute('DELETE FROM sets WHERE set_key = ?', (k,))
    seen = meta.get('played_date')
    names = {}
    for g in games:
        i = infos[g['game_id']]
        for s in ('p1', 'p2'):
            names[i[s + '_name']] = player(con, i[s + '_name'], i.get(s + '_cfn_id'), seen)
    focus = meta['focus']; opp = next(n for n in names if n != focus)
    i0 = infos[games[0]['game_id']]
    fs = 'p1' if i0['p1_name'] == focus else 'p2'; os_ = 'p2' if fs == 'p1' else 'p1'
    fg = sum(g['winner'] == focus for g in games) + meta.get('extra_focus_wins', 0)
    og = len(games) - sum(g['winner'] == focus for g in games) + meta.get('extra_opp_wins', 0)
    winner = None if meta.get('incomplete') else (names[focus] if fg > og else names[opp])   # incomplete set (e.g. FT2 left 1-0 / 1-1): no winner
    cur.execute('INSERT INTO sets (set_key, played_date, ranked, format, review, focus_player_id, opp_player_id, focus_char, opp_char, '
                'focus_games, opp_games, winner_player_id, focus_mr_start, games_missing, note, dashboard, analyzer, ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (k, seen, meta.get('ranked'), meta.get('format', 'FT2'), meta.get('review'), names[focus], names[opp],
                 meta.get('focus_char') or i0[fs + '_char'], meta.get('opp_char') or i0[os_ + '_char'], fg, og, winner,
                 (meta.get('focus_mr') or [None])[0] or None, meta.get('games_missing', 0), meta.get('note'), meta.get('dashboard'),
                 meta.get('analyzer', 'shared_core_analyze.py'), datetime.datetime.now().isoformat(timespec='seconds')))
    cur.execute('UPDATE sets SET reviewed_at = ? WHERE set_key = ?',
                (meta.get('reviewed_at') or prev_reviewed or datetime.datetime.now().isoformat(timespec='seconds'), k))   # first review time, kept on re-ingest
    # excluded: a reason (e.g. '1v1me' for a betting match that opens with a ~30 s warm-up). Kept in the database, left out of
    # history, the published site and its stats. Set by META 'excluded' or `shared_core_db.py exclude`; kept on re-ingest.
    cur.execute('UPDATE sets SET excluded = ? WHERE set_key = ?', (meta.get('excluded', prev_excluded), k))
    for n, g in enumerate(games):
        i = infos[g['game_id']]
        fm = (meta.get('focus_mr') or [None] * len(games))[n] if n < len(meta.get('focus_mr') or []) else None
        p1mr = i.get('p1_mr') or (fm if fs == 'p1' else None); p2mr = i.get('p2_mr') or (fm if fs == 'p2' else None)
        lp1, lp2 = i.get('p1_lp'), i.get('p2_lp')
        cur.execute('INSERT OR REPLACE INTO games (replay_id, set_key, game_no, played_time, p1_player_id, p2_player_id, p1_char, p2_char, '
                    'p1_control, p2_control, p1_mr, p2_mr, winner_player_id, round_score, round_winners, capture_file, p1_lp, p2_lp, p1_rank, p2_rank) '
                    'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (g['game_id'], k, g['game_no'], (meta.get('game_times') or [None] * 9)[n] if meta.get('game_times') else None,
                     names[i['p1_name']], names[i['p2_name']], i['p1_char'], i['p2_char'], i.get('p1_control'), i.get('p2_control'),
                     p1mr or None, p2mr or None, names[g['winner']], g['round_score'], g['round_winners'], meta['captures'][g['game_id']],
                     lp1, lp2, RANK.label(lp1, p1mr), RANK.label(lp2, p2mr)))
    charof = {}
    for g in games:
        i = infos[g['game_id']]
        for s in ('p1', 'p2'): charof[(g['game_id'], i[s + '_name'])] = i[s + '_char']
    cur.executemany('INSERT INTO hits (set_key, replay_id, round, round_timer, attacker_id, victim_id, attacker_char, victim_char, damage, starter, hits_in_combo, hit_kind, anti_air, situation, lens, victim_state, victim_move, note, drive_spent, super_spent, drive_gained, drive_damage, knockdown, kd_adv, corner_dist, victim_drive_after, recoverable, white_cashed) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    [(k, h['game_id'], h['round'], h['round_timer'], names[h['attacker']], names[h['victim']], charof.get((h['game_id'], h['attacker'])),
                      charof.get((h['game_id'], h['victim'])), h['damage'], h['starter'], h.get('hits_in_combo'), h['hit_kind'], int(bool(h.get('anti_air'))),
                      h.get('situation'), h.get('lens'), h.get('victim_state'), h.get('victim_move'), h.get('note'),
                      h.get('drive_spent'), h.get('super_spent'), h.get('drive_gained'), h.get('drive_damage'), h.get('knockdown'), h.get('kd_adv'), h.get('corner_dist'), h.get('victim_drive_after'), h.get('recoverable'), h.get('white_cashed')) for h in hits])
    cur.executemany('INSERT INTO events (set_key, replay_id, round, round_timer, player_id, type, note) VALUES (?,?,?,?,?,?,?)',
                    [(k, e['game_id'], e['round'], e.get('round_timer'), names[e['player']], e['type'], e.get('note')) for e in events])
    cur.executemany('INSERT INTO timings (set_key, replay_id, round, round_timer, player_id, event, action, frames_until) VALUES (?,?,?,?,?,?,?,?)',
                    [(k, t['game_id'], t['round'], t['round_timer'], names[t['player']], t['event'], t['action'], t['frames_until']) for t in timings])
    if os.path.exists(f'{outdir}/resources.json'):
        cur.execute('DELETE FROM resources WHERE set_key=?', (k,))
        cur.executemany('INSERT OR REPLACE INTO resources VALUES (' + ','.join('?' * 24) + ')', [resource_row(k, r, names) for r in L('resources')])
    cur.execute('DELETE FROM parries WHERE set_key=?', (k,))
    if os.path.exists(f'{outdir}/parries.json'):
        cur.executemany('INSERT INTO parries VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)', [(k, x['game_id'], x['round'], x['round_timer'], names[x['player']], x['frames'], x['drive_before'], x['cost'],
                                                                                x['hits_parried'], x['regained'], x['net'], int(bool(x['perfect'])), x['next']) for x in L('parries')])
    cur.execute('DELETE FROM punish_windows WHERE set_key=?', (k,))
    pwin = L('punish_windows') if os.path.exists(f'{outdir}/punish_windows.json') else []
    cur.executemany('INSERT INTO punish_windows VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', [(k, x['game_id'], x['round'], x['round_timer'], names[x['defender']], names[x['attacker']], x['move'], x['adv'],
                                                                                    x['distance'], x['range'], x['result'], x['action'], x['wiki_adv'], x['check']) for x in pwin])
    if os.path.exists(f'{outdir}/corner.json'):   # time cornered per round (tools/corner_time.py); totals go into set_stats / game_stats below
        import corner_time
        crn = L('corner')
        for g in games:
            corner_time.store(con, k, g['game_id'], [r for r in crn if r['game_id'] == g['game_id']], names)
    for pid, m in set_stats(hits, events, timings, games, names, presses, pwin).items():
        cur.executemany('INSERT INTO set_stats VALUES (?,?,?,?)', [(k, pid, a, b) for a, b in m.items()])
    cur.execute('DELETE FROM game_stats WHERE set_key=?', (k,))
    for g in games:   # per game too, so a player's stats can be split by character (and a mid-set character switch is split correctly)
        gid = g['game_id']; only = lambda rows: [x for x in rows if x.get('game_id') == gid]
        for name, pid in names.items():
            m = set_stats(only(hits), only(events), only(timings), [g], {name: pid}, only(presses) if presses else None, only(pwin))[pid]
            cur.executemany('INSERT OR REPLACE INTO game_stats VALUES (?,?,?,?,?,?)', [(k, gid, pid, charof.get((gid, name)), a, b) for a, b in m.items()])
    if os.path.exists(f'{outdir}/corner.json'):
        corner_time.write_stats(con, k, crn, names, per_game={g['game_id']: [r for r in crn if r['game_id'] == g['game_id']] for g in games})
    rep = os.path.join(outdir, 'report.md')
    if os.path.exists(rep):
        import ast, re
        gi = -1
        for line in open(rep, encoding='utf-8'):
            if line.startswith('# Game'): gi += 1
            m = re.match(r'\s+usage (.+?): (\[.*\])$', line)
            if m and 0 <= gi < len(games) and m.group(1) in names:
                cur.executemany('INSERT OR REPLACE INTO usage VALUES (?,?,?,?,?)',
                                [(k, games[gi]['game_id'], names[m.group(1)], mv, n) for mv, n in ast.literal_eval(m.group(2))])
    for ds, rows in (meta.get('review_docs') or {}).items():
        cur.execute('INSERT OR REPLACE INTO review_docs VALUES (?,?,?,?)', (k, ds, json.dumps(rows, ensure_ascii=False), datetime.datetime.now().isoformat(timespec='seconds')))
    if meta.get('dash'):   # {"dashboard": name, "set_no": N or None (next free)}
        d = meta['dash']; have = cur.execute('SELECT set_no FROM dashboard_sets WHERE dashboard=? AND set_key=?', (d['dashboard'], k)).fetchone()
        if not have:
            no = d.get('set_no') or (cur.execute('SELECT COALESCE(MAX(set_no),0)+1 FROM dashboard_sets WHERE dashboard=?', (d['dashboard'],)).fetchone()[0])
            cur.execute('INSERT INTO dashboard_sets VALUES (?,?,?)', (d['dashboard'], k, no))
    src = meta.get('source')
    # A Full review's hand-written archetypes / habits live in review_docs; use them when META has no
    # separate reads / habits, so the reads and habits tables (and SHOTOKAN-WEB) always get them.
    docs = meta.get('review_docs') or {}
    if not meta.get('reads') and docs.get('archetypes'): meta['reads'] = docs['archetypes']
    if not meta.get('habits') and docs.get('habits'): meta['habits'] = docs['habits']
    for r in meta.get('reads', []):
        if r['player'] not in names: continue
        cur.execute('INSERT OR REPLACE INTO reads VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                    (k, names[r['player']], r.get('character'), r.get('archetype'), r.get('lean'), r.get('confidence'), r.get('evidence'),
                     r.get('counter_note'), r.get('doc_risk_tolerance'), r.get('doc_temperament'), src))
    cur.executemany('INSERT INTO habits (set_key, player_id, kind, area, habit, seen, times, fix, confidence, source) VALUES (?,?,?,?,?,?,?,?,?,?)',
                    [(k, names[h['player']], h.get('kind'), h.get('area'), h.get('habit'), h.get('seen'), h.get('times'), h.get('fix'), h.get('confidence'), src)
                     for h in meta.get('habits', []) if h['player'] in names])
    con.commit()
    return k


def _ids_key(ids):
    return ','.join(sorted(i.strip().upper() for i in ids if i.strip()))


def store_prediction(con, pred, replace=False):
    """Store a blind prediction before any of its games are ingested. pred needs 'replays' (list of replay IDs) and
    'written_at'; 'manifest' (shared_core_blind_manifest.py output) is kept if present. Returns the prediction_id."""
    ids = pred.get('replays') or []
    if isinstance(ids, str): ids = ids.replace(',', ' ').split()
    if not ids: raise SystemExit("prediction needs 'replays': the set's replay IDs")
    if not pred.get('written_at'): raise SystemExit("prediction needs 'written_at'")
    key = _ids_key(ids)
    seen = [r[0] for r in con.execute(f"SELECT replay_id FROM games WHERE replay_id IN ({','.join('?' * len(ids))})", [i.upper() for i in ids])]
    if seen:
        raise SystemExit(f"refused: {', '.join(seen)} already ingested, so the result is known. Store predictions before the analyzer runs.")
    old = con.execute('SELECT prediction_id, set_key FROM predictions WHERE replay_ids=?', (key,)).fetchone()
    if old and not replace:
        raise SystemExit(f'a prediction for these replays is already stored (id {old[0]}); --replace to overwrite it before ingest')
    if old: con.execute('DELETE FROM predictions WHERE prediction_id=?', (old[0],))
    cur = con.execute('INSERT INTO predictions (replay_ids, written_at, stored_at, manifest, body) VALUES (?,?,?,?,?)',
                      (key, pred['written_at'], datetime.datetime.now().isoformat(timespec='seconds'),
                       json.dumps(pred.get('manifest')) if pred.get('manifest') is not None else None, json.dumps(pred)))
    con.commit()
    return cur.lastrowid


def link_prediction(con, set_key, meta):
    """After ingest: attach the stored prediction to its set and record the grade from review_docs.prediction."""
    ids = [r[0] for r in con.execute('SELECT replay_id FROM games WHERE set_key=?', (set_key,))]
    row = con.execute('SELECT prediction_id FROM predictions WHERE replay_ids=?', (_ids_key(ids),)).fetchone()
    if not row:
        print('note: no stored blind prediction for this set (shared_core_db.py predict stores one before the analyzer runs)')
        return None
    grade = (meta.get('review_docs') or {}).get('prediction')
    con.execute('UPDATE predictions SET set_key=?, grade=COALESCE(?, grade), graded_at=CASE WHEN ? IS NULL THEN graded_at ELSE ? END WHERE prediction_id=?',
                (set_key, json.dumps(grade) if grade else None, json.dumps(grade) if grade else None,
                 datetime.datetime.now().isoformat(timespec='seconds'), row[0]))
    con.commit()
    return row[0]


def _pid(con, who):
    if not who: return None
    r = con.execute('SELECT player_id FROM players WHERE cfn_id=? OR name=? UNION SELECT player_id FROM player_names WHERE name=?', (who, who, who)).fetchone()
    return r[0] if r else None


def mr_change(my_mr, opp_mr, result):
    """MR change for one ranked game: Elo with K = 16, as in sfbuff (github.com/alanoliveira/sfbuff,
    app/models/master_rating_calculator.rb, MIT). result 1 win, 0 loss, 0.5 draw. Checked on sf6.db 2026-11-25:
    it matches the next game's MR in 314 of 316 game sides (the other 2 were one set stored in the wrong game order)."""
    return round(16 * (result - 1 / (1 + 10 ** ((opp_mr - my_mr) / 400.0))))


def mr_odds(my_mr, opp_mr):
    """What the MR gap says before a set (2026-11-25): every ranked game has 16 MR at stake, split by the Elo
    expectation, so the MR a player would lose is 16 x their chance to win the game (8 / 8 = 50%; +6 / -10 = 62.5%).
    Returns the win / loss MR, the game win chance and the chance to win an FT2 and an FT3 if every game had that chance."""
    p = 1 / (1 + 10 ** ((opp_mr - my_mr) / 400.0)); q = 1 - p
    return dict(win=mr_change(my_mr, opp_mr, 1), loss=mr_change(my_mr, opp_mr, 0), game=round(p, 3),
                ft2=round(p * p * (1 + 2 * q), 3), ft3=round(p ** 3 * (1 + 3 * q + 6 * q * q), 3))


def mr_changes(con, set_key):
    """Fill games.p1/p2_mr_change and sets.opp_mr_start / focus_mr_end / opp_mr_end for a ranked set where both players
    have an MR. A game's change is observed (the same player's MR in the set's next game minus this one) when there is a
    next game, else calculated with mr_change(); the last game of a set is always calculated. mr_change_source says which:
    'observed', 'calculated', or 'observed; formula says X / Y' when they disagree, which usually means the games are
    stored out of played order. Returns a list of those disagreements."""
    ranked = con.execute('SELECT ranked, focus_player_id, opp_player_id FROM sets WHERE set_key=?', (set_key,)).fetchone()
    if not ranked: return []
    rk, fpid, opid = ranked
    g = con.execute('SELECT replay_id, game_no, p1_player_id, p2_player_id, p1_mr, p2_mr, winner_player_id FROM games '
                    'WHERE set_key=? ORDER BY game_no', (set_key,)).fetchall()
    mr_of = lambda row, pid: row[4] if row[2] == pid else row[5] if row[3] == pid else None
    warn = []
    for i, row in enumerate(g):
        rid, _, p1, p2, m1, m2, w = row
        if not rk or not m1 or not m2 or m1 <= 0 or m2 <= 0:
            con.execute('UPDATE games SET p1_mr_change=NULL, p2_mr_change=NULL, mr_change_source=NULL WHERE replay_id=?', (rid,)); continue
        res = lambda pid: 0.5 if w is None else (1 if w == pid else 0)
        calc = (mr_change(m1, m2, res(p1)), mr_change(m2, m1, res(p2)))
        nxt = g[i + 1] if i + 1 < len(g) else None
        obs = None
        if nxt:
            n1, n2 = mr_of(nxt, p1), mr_of(nxt, p2)
            if n1 and n2 and n1 > 0 and n2 > 0: obs = (n1 - m1, n2 - m2)
        if obs is None: ch, src = calc, 'calculated'
        elif all(abs(a - b) <= 1 for a, b in zip(obs, calc)): ch, src = obs, 'observed'
        else:
            ch, src = obs, f'observed; formula says {calc[0]:+d} / {calc[1]:+d}'
            warn.append(f'{set_key} game {row[1]} ({rid}): MR moved {obs[0]:+d} / {obs[1]:+d}, formula {calc[0]:+d} / {calc[1]:+d} (games out of order?)')
        con.execute('UPDATE games SET p1_mr_change=?, p2_mr_change=?, mr_change_source=? WHERE replay_id=?', (ch[0], ch[1], src, rid))
    first = g[0] if g else None; last = g[-1] if g else None
    ends = {}
    if first and last and rk:
        lc = con.execute('SELECT p1_mr_change, p2_mr_change FROM games WHERE replay_id=?', (last[0],)).fetchone()
        for pid in (fpid, opid):
            m = mr_of(last, pid); d = lc[0] if last[2] == pid else lc[1]
            ends[pid] = m + d if m and m > 0 and d is not None else None
        o0 = mr_of(first, opid)
        con.execute('UPDATE sets SET opp_mr_start=?, focus_mr_end=?, opp_mr_end=? WHERE set_key=?',
                    (o0 if o0 and o0 > 0 else None, ends.get(fpid), ends.get(opid), set_key))
    return warn


def history(con, opp=None, opp_char=None, player=None, my_char=None, before=None, exclude=()):
    """Pre-set history for a prediction, only from sets before `before` (ISO date or datetime; default now).
    A set counts as earlier if played_date is before the date, or on the same date and its first game was played
    before the time (games.played_time, from the meta's game_times; ingest time only when no game time is stored).
    Times are compared as 'YYYY-MM-DD HH:MM[:SS]', so 'T' or ' ' separators both work."""
    import paths
    player = paths.require_player(player)
    before = (before or datetime.datetime.now().isoformat(timespec='seconds')).replace('T', ' ')
    day, tm = before[:10], (before[11:] if len(before) > 10 else None)
    ex = set(i.upper() for i in exclude)
    def started(sk, date, ing):
        ts = [t for (t,) in con.execute('SELECT played_time FROM games WHERE set_key=? AND played_time IS NOT NULL AND played_time<>""', (sk,))]
        ts = [t if len(t) > 8 else f'{date} {t}' for t in ts]   # some older rows store only 'HH:MM'
        return min(ts) if ts else (ing or '').replace('T', ' ')
    def earlier(sk, date, ing):
        if ex and any(r[0] in ex for r in con.execute('SELECT replay_id FROM games WHERE set_key=?', (sk,))): return False
        if date < day: return True
        if date != day or tm is None: return False
        st = started(sk, date, ing)
        return bool(st) and st[:16] < before[:16]   # to the minute; a set starting at `before` is the set itself
    me, op = _pid(con, player), _pid(con, opp)
    sets = [r for r in con.execute('SELECT set_key, played_date, ingested_at, format, ranked, focus_player_id, opp_player_id, focus_char, opp_char, '
                                   'focus_games, opp_games, winner_player_id FROM sets WHERE excluded IS NULL ORDER BY played_date') if earlier(r[0], r[1], r[2])]
    sets.sort(key=lambda r: (r[1], started(r[0], r[1], r[2])))   # same-day sets in played order
    out = {'before': before, 'vs_player': [], 'char_matchup': [], 'opp_reads': [], 'opp_habits': [], 'my_recent_habits': []}
    name = lambda p: (con.execute('SELECT name FROM players WHERE player_id=?', (p,)).fetchone() or ['?'])[0]
    for sk, d, _, fmt, rk, f, o, fc, oc, fg, og, w in sets:
        pids = {f: fc, o: oc}
        row = dict(set_key=sk, date=d, format=fmt, ranked=rk, players=f'{name(f)} ({fc}) {fg}-{og} {name(o)} ({oc})', winner=name(w) if w else None)
        if op and op in pids: out['vs_player'].append(row)
        other = o if f == me else f
        if me in pids and opp_char and pids[me] == (my_char or pids[me]) and pids.get(other) == opp_char and other != me:
            out['char_matchup'].append(row)
        if op in pids:
            for r in con.execute('SELECT archetype, lean, confidence, evidence FROM reads WHERE set_key=? AND player_id=?', (sk, op)):
                out['opp_reads'].append(dict(set_key=sk, date=d, archetype=r[0], lean=r[1], confidence=r[2], evidence=r[3]))
            for r in con.execute('SELECT kind, area, habit, times FROM habits WHERE set_key=? AND player_id=?', (sk, op)):
                out['opp_habits'].append(dict(set_key=sk, kind=r[0], area=r[1], habit=r[2], times=r[3]))
    mine = [s for s in sets if me in (s[5], s[6])][-5:]
    for s in mine:
        for r in con.execute("SELECT kind, area, habit, times FROM habits WHERE set_key=? AND player_id=? AND kind IN ('Leak','Strength')", (s[0], me)):
            out['my_recent_habits'].append(dict(set_key=s[0], date=s[1], kind=r[0], area=r[1], habit=r[2], times=r[3]))
    return out


def load_info(path):
    """Just the capture's info block (plain or .gz)."""
    if path.endswith('.gz'):
        import gzip
        with gzip.open(path, 'rt', encoding='utf-8') as f: return json.load(f)['info']
    return json.load(open(path, encoding='utf-8'))['info']


if __name__ == '__main__':
    cmd, db = sys.argv[1], sys.argv[2]
    con = connect(db)
    if cmd == 'ingest':
        meta = json.load(open(sys.argv[4]))
        key = ingest_set(con, sys.argv[3], meta)
        print('ingested', key)
        for w in mr_changes(con, key): print('MR check:', w)
        link_prediction(con, key, meta)
        con.commit(); con.close()
        if '--no-spectra' not in sys.argv:   # the eight player spectra (spectra table + review_docs archetypes)
            import spectra_backfill
            spectra_backfill.backfill(db, [key], local=meta.get('captures_local'))
            import player_baseline   # the configured player vs their own last 7 days (player_baseline table)
            player_baseline.update(db)
    elif cmd == 'predict':
        pid = store_prediction(con, json.load(open(sys.argv[3], encoding='utf-8')), replace='--replace' in sys.argv)
        print('stored prediction', pid)
    elif cmd == 'history':
        a = sys.argv[3:]
        opt = lambda k: a[a.index(k) + 1] if k in a else None
        h = history(con, opt('--opp'), opt('--opp-char'), opt('--player'), opt('--my-char'), opt('--before'),
                    (opt('--exclude') or '').replace(',', ' ').split())
        print(json.dumps(h, indent=1, ensure_ascii=False))
    elif cmd == 'mr':   # fill MR changes for every set (or the set keys given); prints sets whose MR says the game order is wrong
        keys = sys.argv[3:] or [r[0] for r in con.execute('SELECT set_key FROM sets')]
        warns = [w for k in keys for w in mr_changes(con, k)]
        con.commit()
        n = con.execute('SELECT COUNT(*), SUM(mr_change_source LIKE "observed%"), SUM(mr_change_source = "calculated") FROM games WHERE mr_change_source IS NOT NULL').fetchone()
        print(f'MR changes: {n[0]} games ({n[1]} observed, {n[2]} calculated) in {len(keys)} sets checked')
        for w in warns: print('MR check:', w)
    elif cmd == 'odds':   # python shared_core_db.py odds DB MY_MR OPP_MR
        print(json.dumps(mr_odds(float(sys.argv[3]), float(sys.argv[4]))))
    elif cmd == 'sql':
        cur = con.execute(sys.argv[3]); print(' | '.join(d[0] for d in cur.description))
        for r in cur.fetchall(): print(' | '.join('' if v is None else str(v) for v in r))
    elif cmd == 'flag':   # python shared_core_db.py flag DB "NAME|CFN" [FLAG] [--note "..."] [--remove]; FLAG defaults to 'notable'
        a = [x for x in sys.argv[3:]]
        note = a[a.index('--note') + 1] if '--note' in a else None
        args = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] != '--note')]
        who, flag = args[0], (args[1] if len(args) > 1 else 'notable')
        row = con.execute('SELECT p.player_id, p.name FROM players p WHERE p.cfn_id = ? OR lower(p.name) = lower(?) '
                          'UNION SELECT n.player_id, p.name FROM player_names n JOIN players p USING (player_id) WHERE lower(n.name) = lower(?)',
                          (who, who, who)).fetchall()
        if len(row) != 1:
            sys.exit(f'{who}: {len(row)} players match; use the CFN ID')
        pid, name = row[0]
        if '--remove' in a:
            con.execute('DELETE FROM player_flags WHERE player_id = ? AND flag = ?', (pid, flag)); print('unflagged', name, flag)
        else:
            con.execute('INSERT OR REPLACE INTO player_flags VALUES (?,?,?,?)', (pid, flag, note, datetime.date.today().isoformat())); print('flagged', name, flag)
        con.commit()
    elif cmd == 'exclude':   # python shared_core_db.py exclude DB SETKEY [REASON] [--remove]; REASON defaults to '1v1me'
        a = [x for x in sys.argv[3:] if not x.startswith('--')]
        k, why = a[0], (a[1] if len(a) > 1 else '1v1me')
        n = con.execute('UPDATE sets SET excluded = ? WHERE set_key = ?', (None if '--remove' in sys.argv else why, k)).rowcount
        con.commit(); print(('included' if '--remove' in sys.argv else f'excluded ({why})') if n else 'no such set', k)
    elif cmd == 'flags':   # list flagged players
        for r in con.execute('SELECT p.name, p.cfn_id, f.flag, f.note, f.added FROM player_flags f JOIN players p USING (player_id) ORDER BY f.flag, lower(p.name)'):
            print(' | '.join('' if v is None else str(v) for v in r))
    elif cmd == 'init':
        print('ok')
