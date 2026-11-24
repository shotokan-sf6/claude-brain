"""Behaviour spectra for player reads.

Each axis is a 1-5 scale between two opposite ends (3 = in between). Scores are computed from the
capture data of one set, for one player, and compared with every player-set reviewed so far
(the built-in cut points below are the 20/40/60/80th percentiles of the 33 player-sets in sf6.db on 2026-11-18;
spectra_calibrate.py recalibrates them from every player-set except the configured player's, stored in sf6.db and
loaded with load_cuts()).

Axes
- Temperament (defense): Impulsive (1) <-> Mindful (5). Share of after-block / wake-up situations where
  the player's first action was an attack, special, super, throw, jump or Drive Parry within 2 frames
  (reversal timing). Blocked-again situations (no choice made) are left out. Offense isn't measured here.
- Adaptability: Inelastic (1) <-> Elastic (5). For moves (not jabs) that got the player counter-hit, punished
  or checked in earlier games, how often they kept using them in later games (per round), weighted by how often each
  was punished. Needs 2+ games and at least one punished move that was used again or dropped. Only counted when the
  plan was losing (lost that game or behind in the set) or the move kept getting punished (2+ times or 2,000+ damage,
  weighted 1.5x; in a won game only 3,500+ damage from that move counts); keeping a punished move in a winning plan is neutral ("Kept a winning plan", 3/5).
- Temperament (offense): Impulsive (1) <-> Mindful (5). After the opponent blocks one of their attacks, how often the
  player presses again (attack, jump, Drive Rush) within 3 frames of being free, instead of delaying, walking or waiting.
- Initiative: Reactive (1) <-> Proactive (5). Share of neutral movement that goes forward, averaged with the share of
  neutral exchanges (after 20+ quiet frames) the player starts.
- Composure: Steady (1) <-> Tilts (5). Rate of actions started in the 15 s after taking a 2,000+ combo and the first 20 s
  of a round after losing the last one, against the rest of the time.
- Variety: Scripted (1) <-> Mixed (5). Spread (normalized entropy) of their choices after blocking and on wake-up.
- Resource use: Conservative (1) <-> Spendthrift (5). Drive bars + half a point per super bar + 1 per burnout, per round.
- Risk tolerance: Low (1) <-> High (5). Risky options per round: wake-up reversals (special / super on
  wake-up), Drive Impacts, Drive Reversals, raw Drive Rushes (half weight: 1 bar and a clean or counter hit if
  checked, a generally safe way to start pressure), supers and forward jumps.
"""
import collections as C, json, re, sys

AXES = [
    dict(key='temperament', axis='Temperament (defense)', left='Impulsive', right='Mindful'),
    dict(key='temperament_off', axis='Temperament (offense)', left='Impulsive', right='Mindful'),
    dict(key='elasticity', axis='Adaptability', left='Inelastic', right='Elastic'),
    dict(key='risk', axis='Risk tolerance', left='Low', right='High'),
    dict(key='initiative', axis='Initiative', left='Reactive', right='Proactive'),
    dict(key='composure', axis='Composure', left='Steady', right='Tilts'),
    dict(key='variety', axis='Variety', left='Scripted', right='Mixed'),
    dict(key='resources', axis='Resource use', left='Conservative', right='Spendthrift'),
]
REVERSED = {'temperament', 'temperament_off', 'elasticity'}   # a higher raw value points to the left end
# cut points (20/40/60/80th percentiles of the pool, 2026-11-18); a raw value below cut[0] scores 1, above cut[3] scores 5
CUTS = {
    'temperament': [0.30, 0.38, 0.43, 0.51],   # impulsive share: higher = more impulsive (score reversed)
    'elasticity': [0.57, 0.73, 0.82, 0.98],      # later-use ratio: higher = more inelastic (score reversed)
    'risk': [2.0, 2.5, 3.5, 4.0],              # risky options per round: higher = more risk
    'temperament_off': [0.07, 0.12, 0.17, 0.26],  # share of immediate re-presses after a blocked attack (score reversed)
    'initiative': [0.37, 0.42, 0.47, 0.56],     # forward-movement share and exchanges started
    'composure': [1.02, 1.15, 1.34, 1.48],      # action rate after adversity / otherwise (most players speed up a bit)
    'variety': [0.51, 0.57, 0.6, 0.69],         # normalized entropy of after-block / wake-up choices
    'resources': [1.26, 1.5, 1.7, 1.94],        # gauge bars spent per round (recalibrated 2026-11-18 after counting the spend that triggers burnout)
}
DEFAULT_CUTS = {k: list(v) for k, v in CUTS.items()}
CUTS_META = {'source': 'built-in (2026-11-18, 33 player-sets)'}


def load_cuts(con):
    """Use the cut points calibrated by spectra_calibrate.py (settings 'spectra_cuts' in sf6.db) when there are any.
    They are the 20/40/60/80th percentiles of every player-set except the configured player's, each other player
    weighted equally (less below 10 games). Falls back to the built-in cut points."""
    global CUTS_META
    try:
        row = con.execute("select value from settings where key='spectra_cuts'").fetchone()
    except Exception:
        row = None
    if not row:
        return CUTS_META
    d = json.loads(row[0])
    for k, v in (d.get('cuts') or {}).items():
        if k in CUTS and len(v) == 4: CUTS[k] = v
    CUTS_META = {k: v for k, v in d.items() if k != 'cuts'}
    return CUTS_META


def score(key, v):
    """1-5 score for a raw value on one axis (None stays None)."""
    if v is None: return None
    b = _bucket(v, CUTS[key])
    return 6 - b if key in REVERSED else b


WORDS = {'risk': ['Very low', 'Low', 'Medium', 'High', 'Very high']}
for _a in AXES:
    WORDS.setdefault(_a['key'], [f"Very {_a['left'].lower()}", f"Leans {_a['left'].lower()}", 'In between', f"Leans {_a['right'].lower()}", f"Very {_a['right'].lower()}"])
import os as _os
_CACHE = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'beh_cache.json')
BEH = json.load(open(_CACHE)) if _os.path.exists(_CACHE) else {}
PRESS = ('atck', 'special', 'super', 'parry', 'jump')
LIGHTS = {'5LP', '2LP', '5LK', '2LK', 'j.LP', 'j.LK'}   # jabs are tools, not commitments to drop
SKIP_MOVES = ('Throw', 'Getting up', 'Walking', 'BAS_', 'DRD', 'GRD', 'NOKI', 'FC_HOLD')


def _core(m):
    return re.sub(r' \((L|M|H|OD)\)$', '', str(m))


def _bucket(v, cuts):
    return 1 + sum(v > c for c in cuts)


def _rounds(games):
    out = {}
    for g in games:
        try: out[g['game_id']] = sum(int(x) for x in str(g['round_score']).split('-'))
        except Exception: out[g['game_id']] = 3
    return out


def raw(player, games, hits, tim, ev, use, beh=None):
    """raw values for one player in one set; use = list (per game, same order) of {player: Counter(move)}"""
    gids = [g['game_id'] for g in games]
    rounds = _rounds(games)
    # temperament
    t = [x for x in tim if x['player'] == player and not str(x['action']).startswith('blocked')]
    imp = [x for x in t if str(x['action']).split(':')[0] in PRESS and x['frames_until'] is not None and x['frames_until'] <= 2]
    temp = (len(imp) / len(t)) if len(t) >= 8 else None
    # elasticity (Sean, 2026-11-21): reusing a punished move only counts as inelastic when the plan is losing
    # (lost that game, or behind in the set going into it) or the move keeps getting punished in that game.
    # Keeping a winning plan is neutral, not inelastic.
    num = den = 0.0; moves_seen = C.Counter(); kept_winning = C.Counter(); costly = C.Counter()
    def _pun(h):
        return (h['victim'] == player and h['victim_move']
                and (h['hit_kind'] in ('counter hit', 'punish counter') or h['lens'] in ('Unsafe move punished', 'Pressed after turn ended', 'Whiff punished', 'Own offense beaten by a reversal', 'Drive Rush / Impact checked'))
                and not str(h['victim_move']).startswith(SKIP_MOVES) and _core(h['victim_move']) not in LIGHTS)
    won = {g['game_id']: (g.get('winner') == player) for g in games}
    known = all(g.get('winner') for g in games)
    for gi in range(1, len(gids)):
        before = gids[:gi]
        pun = C.Counter(_core(h['victim_move']) for h in hits if h['game_id'] in before and _pun(h))
        again = C.Counter(); again_dmg = C.Counter()
        for h in hits:
            if h['game_id'] == gids[gi] and _pun(h):
                again[_core(h['victim_move'])] += 1; again_dmg[_core(h['victim_move'])] += h.get('damage') or 0
        w_before = sum(won[g] for g in before); behind = w_before < len(before) - w_before
        losing = (not known) or behind or not won[gids[gi]]
        rb = sum(rounds[g] for g in before) or 1; rg = rounds[gids[gi]] or 1
        cu = [C.Counter() for _ in use]
        for k, u in enumerate(use):
            for m_, n_ in u.get(player, {}).items(): cu[k][_core(m_)] += n_
        for m, w in pun.items():
            ub = sum(cu[k].get(m, 0) for k in range(gi)) / rb
            if ub <= 0: continue
            ug = cu[gi].get(m, 0) / rg
            still_costing = again[m] >= 2 or again_dmg[m] >= 2000
            # in a game they won (and weren't behind), a reused move only counts if it cost a real chunk of life
            if not losing and again_dmg[m] < 3500:
                if ug > 0: kept_winning[m] += w
                continue
            ww = w * (1.5 if still_costing else 1.0)
            if still_costing: costly[m] += 1
            num += ww * ug; den += ww * ub; moves_seen[m] += w
    elas = (num / den) if den > 0 and sum(moves_seen.values()) >= 2 else None
    elas_winning = elas is None and sum(kept_winning.values()) >= 2
    # risk
    R = sum(rounds.values()) or 1
    U = C.Counter()
    for u in use: U.update(u.get(player, {}))
    wake_rev = sum(1 for x in tim if x['player'] == player and x['event'] == 'wake-up' and str(x['action']).split(':')[0] in ('special', 'super'))
    raw_dr = sum(1 for e in ev if e['player'] == player and e['type'] == 'raw drive rush')
    supers = sum(n for m, n in U.items() if m.startswith(('SA', 'Critical Art', 'CA')))
    jumps = U.get('BAS_JUMP_F_START', 0)
    risky = 2 * wake_rev + 1.5 * U.get('Drive Impact', 0) + 1.5 * U.get('Drive Reversal', 0) + 0.5 * raw_dr + supers + 0.5 * jumps
    risk = risky / R
    # frame-level counts (behavior.py), summed over the set's games
    if beh is None:
        beh = C.Counter()
        for g in gids: beh.update(BEH.get(g, {}).get(player, {}))
    b = beh
    toff = (b['off_imp'] / b['off_n']) if b.get('off_n', 0) >= 8 else None
    ini = (0.5 * b['fwd'] / (b['fwd'] + b['back']) + 0.5 * b['starts'] / b['starts_all']) if b.get('starts_all', 0) >= 6 and (b.get('fwd', 0) + b.get('back', 0)) > 0 else None
    comp = ((b['hot_act'] / b['hot_f']) / (b['calm_act'] / b['calm_f'])) if b.get('hot_f', 0) >= 600 and b.get('calm_act', 0) > 0 else None
    nburn = sum(1 for e in ev if e['player'] == player and e['type'] == 'burnout')   # the analyzer's burnout events
    res = ((b.get('drive_spent', 0) / 60000 + 0.5 * b.get('super_spent', 0) / 10000 + nburn) / R) if b else None
    # variety: spread of choices after blocking / on wake-up (normalized entropy)
    import math
    var_parts = []
    for evn in ('after block', 'wake-up'):
        cs = C.Counter((str(x['action']).split(':')[0] if str(x['action']).split(':')[0] in ('atck', 'jump', 'parry', 'dash') else _core(x['action']))
                       for x in tim if x['player'] == player and x['event'] == evn and not str(x['action']).startswith('blocked'))
        n = sum(cs.values())
        if n >= 5 and len(cs) > 1:
            H = -sum(v / n * math.log(v / n) for v in cs.values())
            var_parts.append((n, H / math.log(min(n, 8))))
        elif n >= 5: var_parts.append((n, 0.0))
    var = (sum(n * v for n, v in var_parts) / sum(n for n, _ in var_parts)) if var_parts else None
    ev_ = dict(temperament=(f"{len(imp)} of {len(t)} after-block / wake-up choices were a button, special, jump or parry on reversal timing (0-2 frames)" if temp is not None else 'too few after-block / wake-up situations'),
               elasticity=((f"while losing (or while the moves kept costing), used the moves that got punished at {elas:.0%} of their earlier rate ({', '.join(m for m, _ in moves_seen.most_common(3))})"
                           + (f"; still getting punished for {', '.join(costly)}" if costly else '')
                           + (f"; kept {', '.join(m for m, _ in kept_winning.most_common(2))} in games they were winning (not counted)" if kept_winning else '')) if elas is not None
                          else (f"kept a winning plan: reused {', '.join(m for m, _ in kept_winning.most_common(3))} after it got punished, but they were winning and it stopped costing them, so that isn't inelastic" if elas_winning
                                else 'not enough evidence (one game, or no punished move came up again while losing)')),
               temperament_off=(f"once free after their attack was blocked, pressed again within 3 frames {b['off_imp']} of {b['off_n']} times" if toff is not None else 'too few blocked attacks'),
               initiative=(f"walked / dashed forward in {b['fwd'] / max(1, b['fwd'] + b['back']):.0%} of neutral movement and started {b['starts']} of {b['starts_all']} neutral exchanges" if ini is not None else 'too few neutral exchanges'),
               composure=(f"pressed {comp:.0%} as often after taking a 2,000+ combo or losing a round as otherwise" if comp is not None else 'not enough time after big damage or a lost round'),
               variety=(f"spread of choices after blocking and on wake-up: {var:.0%} of the maximum" if var is not None else 'too few after-block / wake-up choices'),
               resources=(f"{res:.1f} gauge bars spent per round ({b.get('drive_spent', 0) / 10000:.0f} Drive bars, {b.get('super_spent', 0) / 10000:.0f} super bars, {nburn} burnouts over {R} rounds)" if res is not None else 'no frame data'),
               risk=f"{risk:.1f} risky options per round: {wake_rev} wake-up reversals, {U.get('Drive Impact', 0)} Drive Impacts, {U.get('Drive Reversal', 0)} Drive Reversals, {raw_dr} raw Drive Rushes (half weight), {supers} supers, {jumps} forward jumps over {R} rounds")
    return dict(temperament=temp, temperament_off=toff, elasticity=elas, elasticity_winning=elas_winning, risk=risk, initiative=ini, composure=comp, variety=var, resources=res), ev_


def spectra(player, games, hits, tim, ev, use):
    vals, evs = raw(player, games, hits, tim, ev, use)
    out = []
    for a in AXES:
        v = vals[a['key']]
        if v is None and a['key'] == 'elasticity' and vals.get('elasticity_winning'):
            out.append(dict(a, score=3, label='Kept a winning plan', evidence=evs[a['key']])); continue
        if v is None:
            out.append(dict(a, score=None, label='Not enough evidence', evidence=evs[a['key']])); continue
        sc = score(a['key'], v)
        out.append(dict(a, score=sc, label=WORDS[a['key']][sc - 1], evidence=evs[a['key']], raw=round(v, 4)))
    return out


def attach(archetypes, sid, games, hits, tim, ev, use):
    """add spectra to the archetype rows of one set (in place); keep any hand-written temperament note as 'adaptation'"""
    for r in archetypes:
        if r.get('set_id') != sid: continue
        sp = spectra(r['player'], games, hits, tim, ev, use)
        for s_ in sp:   # Full reviews: the reviewer's call wins when it conflicts with the computed score
            ov = (r.get('spectra_override') or {}).get(s_['key'])
            if ov:
                comp = f"computed {s_['score']}/5" if s_['score'] else 'not computed'
                s_['computed_score'] = s_['score']; s_['score'] = ov[0]; s_['label'] = WORDS[s_['key']][ov[0] - 1]
                s_['evidence'] = f"Reviewer's call ({comp}): {ov[1]} Data: {s_['evidence']}"; s_['override'] = True
        old = r.get('doc_temperament')
        if old and old != '—' and not r.get('spectra'): r['adaptation'] = old
        r['spectra'] = sp
        d = {s['key']: s for s in sp}
        r['doc_temperament'] = d['temperament']['label'] + (f" ({d['temperament']['score']}/5 toward mindful)" if d['temperament']['score'] else '')
        r['doc_risk_tolerance'] = d['risk']['label'] + (f" ({d['risk']['score']}/5)" if d['risk']['score'] else '')
        r['elasticity'] = d['elasticity']['label'] + (f" ({d['elasticity']['score']}/5 toward elastic)" if d['elasticity']['score'] else '')
    return archetypes
