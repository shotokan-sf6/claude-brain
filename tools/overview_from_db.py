"""Overview tab of the quick-dashboard, computed from the history database.

  python overview_from_db.py DB OUTDIR      # run after quick_dashboard_from_db.py (reads OUTDIR/stats.json and sets.json)

Writes ov_sets, overview (patterns across sets), gameplan and ov_training. Every number in the text is
computed from sf6.db, so the Overview updates when a set is added or re-analysed.
"""
import json, os, sqlite3, sys, collections as C
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
from sf6db_export import mv as _mv
JUMPS = {'BAS_JUMP_F_START': 'forward jump (takeoff)', 'BAS_JUMP_F_AIR': 'forward jump', 'BAS_JUMP_N_START': 'neutral jump (takeoff)', 'BAS_JUMP_N_AIR': 'neutral jump',
         'BAS_JUMP_B_START': 'back jump (takeoff)', 'BAS_JUMP_B_AIR': 'back jump', 'BAS_JUMP_F_LAND': 'forward jump landing', 'BAS_JUMP_N_LAND': 'jump landing'}
mv = lambda n: JUMPS.get(n) or _mv(n)

ME = paths.PLAYER   # the player in focus (shotokan.json / SHOTOKAN_PLAYER)
LEAK = {'Counter-hit at mid range': 'Counter-hit at mid range', 'Whiff punished': 'Whiff punished', 'Walked in': 'Walking in', 'Jumped': 'Jumps / dive kicks',
        'Challenging pressure': 'Challenging pressure', 'Challenging okizeme': 'Challenging okizeme', 'Unsafe move punished': 'Unsafe moves', 'Pressed after turn ended': 'Pressing after turn ended',
        'Blocking, opened up': 'Opened up', 'Jumped in on (no anti-air)': 'Jump-ins not anti-aired', 'Unclear / super': 'Supers',
        'Own offense beaten by a reversal': 'Reversals', 'Drive Rush / Impact checked': 'Drive Rush / Impact'}
NORMALS = ('LP', 'MP', 'HP', 'LK', 'MK', 'HK')
f = lambda n: f'{int(round(n)):,}'
pct = lambda a, b: ('under 1%' if 0 < a / b < 0.01 else f'{a / b:.0%}') if b else '0%'
about = lambda n: f'about {int(round(n, -2)):,}' if n >= 1000 else f(n)


def main(db, out):
    paths.require_player(ME)
    con = sqlite3.connect(db); con.row_factory = sqlite3.Row
    q = lambda sql, *a: [dict(r) for r in con.execute(sql, a).fetchall()]
    me = con.execute('SELECT player_id FROM players WHERE name=?', (ME,)).fetchone()[0]
    S = json.load(open(f'{out}/stats.json'))
    sets = {s['set_id']: s for s in json.load(open(f'{out}/sets.json'))}
    keys = [s['set_key'] for s in S]
    ph = ','.join('?' * len(keys))
    H = q(f'SELECT * FROM hits WHERE set_key IN ({ph})', *keys)
    E = q(f'SELECT * FROM events WHERE set_key IN ({ph})', *keys)
    T = q(f'SELECT * FROM timings WHERE set_key IN ({ph}) AND player_id=?', *keys, me)
    U = q(f'SELECT * FROM usage WHERE set_key IN ({ph})', *keys)
    G = q(f'SELECT * FROM games WHERE set_key IN ({ph})', *keys)
    took = [h for h in H if h['victim_id'] == me]; dealt = [h for h in H if h['attacker_id'] == me]
    tot_t = sum(h['damage'] for h in took) or 1; tot_d = sum(h['damage'] for h in dealt) or 1
    n_sets, n_games = len(S), len(G)
    sid_of = {s['set_key']: s['set_id'] for s in S}
    use_me = C.Counter(); use_opp = C.Counter()
    for u in U: (use_me if u['player_id'] == me else use_opp)[u['move']] += u['n']
    jumps = use_me['BAS_JUMP_F_START']
    # the capture logs a dive kick under its strength and sometimes also under the plain name: count the larger per game
    per = C.defaultdict(lambda: [0, 0])
    for u in U:
        if u['player_id'] == me and u['move'].startswith('Cannon Strike'): per[u['replay_id']][0 if u['move'] == 'Cannon Strike (dive kick)' else 1] += u['n']
    dives = sum(max(a, b) for a, b in per.values())
    lens = lambda name: [h for h in took if (h['lens'] or 'Unclear / super') == name]
    dmg = lambda hs: sum(h['damage'] for h in hs)
    seen = lambda fn: f'{sum(1 for s in S if fn(s))} of {n_sets} sets'
    share = lambda s, k: s['lens_me'].get(k, 0) / max(1, sum(s['lens_me'].values()))
    top_leak = lambda s: max(((k, v) for k, v in s['lens_me'].items() if k in LEAK), key=lambda kv: kv[1], default=(None, 0))[0]
    name_of = {r['player_id']: r['name'] for r in q('SELECT player_id, name FROM players')}

    # ---------------------------------------------------------------- ov_sets
    rows = []
    for s in S:
        st = sets[s['set_id']]; tot = sum(s['lens_me'].values()) or 1
        k = top_leak(s); v = s['lens_me'].get(k, 0)
        mr = next((g for g in G if g['set_key'] == s['set_key'] and g['game_no'] == 1), None)
        mrv = (mr['p1_mr'] if mr and mr['p1_player_id'] == me else mr['p2_mr'] if mr else None)
        # rank labels (rank.py): '<MR> MR', 'MR unknown' (Master without MR) or the league below Master; first game that has one
        gl = [g for g in G if g['set_key'] == s['set_key']]
        lab = lambda g, mine: (g['p1_rank'] if (g['p1_player_id'] == me) == mine else g['p2_rank']) or None
        rank_me = next((lab(g, True) for g in gl if lab(g, True) and lab(g, True) != 'MR unknown'), None) or next((lab(g, True) for g in gl if lab(g, True)), None) or (f'{mrv} MR' if mrv else None)
        rank_opp = next((lab(g, False) for g in gl if lab(g, False) and lab(g, False) != 'MR unknown'), None) or next((lab(g, False) for g in gl if lab(g, False)), None)
        omr_ = next(((g['p2_mr'] if g['p1_player_id'] == me else g['p1_mr']) for g in gl if (g['p2_mr'] if g['p1_player_id'] == me else g['p1_mr'])), None)
        rank_opp = rank_opp or (f'{omr_} MR' if omr_ else None)
        rows.append(dict(set_id=s['set_id'], order=st['order'], ranked=st['ranked'], review=st['review'], date=st['date'], opponent=s['opp'], character=s['opp_char'],
                         result=f"{'Won' if s['set_won'] else 'Lost'} {s['games_won']}-{s['games_lost']}" + (' *' if st.get('note') else ''),
                         set_won=int(s['set_won']), set_lost=int(not s['set_won']), games_won=s['games_won'], games_lost=s['games_lost'],
                         rounds_won=s['rounds_won'], rounds_lost=s['rounds_lost'], rounds=f"{s['rounds_won']}-{s['rounds_lost']}", mr_start=mrv or '—', rank_start=rank_me or '—', opp_rank=rank_opp or '—',
                         dealt=s['dealt'], taken=s['taken'], aa=f"{s['aa_me']} / {s['aa_opp']}", aa_me=s['aa_me'], aa_opp=s['aa_opp'],
                         ch=f"{s['ch_me']} / {s['ch_opp']}", ch_me=s['ch_me'], ch_opp=s['ch_opp'], burn=f"{s['burn_me']} / {s['burn_opp']}",
                         burn_me=s['burn_me'], burn_opp=s['burn_opp'], dr=f"{s['dr_me']} / {s['dr_opp']}",
                         top_leak=f"{LEAK[k]} ({v / tot:.0%})" if k else '—'))
    json.dump(rows, open(f'{out}/ov_sets.json', 'w'), indent=1, ensure_ascii=False)

    # ---------------------------------------------------------------- facts
    neutral_t = dmg([h for h in took if h['situation'] == 'neutral']); neutral_d = dmg([h for h in dealt if h['situation'] == 'neutral'])
    mid = lens('Counter-hit at mid range'); walk = lens('Walked in'); jmp = lens('Jumped'); press = lens('Challenging pressure') + lens('Challenging okizeme')
    noaa = lens('Jumped in on (no anti-air)')
    btn = C.Counter(h['victim_move'] for h in took if h['victim_move'] and h['victim_move'][-2:] in NORMALS and h['lens'] != 'Jumped')
    top_btns = [b for b, _ in btn.most_common(3)]
    b0 = top_btns[0] if top_btns else '—'
    b0h = [h for h in took if h['victim_move'] == b0]
    b0_lens = C.Counter(h['lens'] for h in b0h)
    mid_top = sum(1 for s in S if top_leak(s) == 'Counter-hit at mid range')
    big_mid = [s['opp'] for s in S if share(s, 'Counter-hit at mid range') >= 0.4]
    thrown = [h for h in took if h['hit_kind'] == 'throw']; walk_thr = [h for h in walk if h['hit_kind'] == 'throw']
    my_thr_pun = [h for h in took if h['victim_move'] in ('Throw attempt', 'Throw tech attempt')]
    walk_st = C.Counter(h['starter'] for h in walk).most_common(3)
    aa_me = [h for h in dealt if h['anti_air']]; aa_them = [h for h in took if h['anti_air']]
    aa_best = max(S, key=lambda s: s['aa_me']); low_aa = sum(1 for s in S if s['aa_me'] <= 1)
    dive_hit = [h for h in took if (h['victim_move'] or '').startswith('Cannon Strike')]
    dive_start = [h for h in dealt if (h['starter'] or '').startswith('Cannon Strike')]
    ab = [t for t in T if t['event'] == 'after block']; wk = [t for t in T if t['event'] == 'wake-up']
    att = lambda t: t['action'].split(':')[0] in ('atck', 'special', 'super')
    ab_att = [t for t in ab if att(t)]; ab_f0 = [t for t in ab_att if (t['frames_until'] or 0) <= 1]
    ab_hold = [t for t in ab if t['action'].startswith('nothing')]; ab_jump = [t for t in ab if t['action'].startswith('jump')]
    ab_fj = [t for t in ab if t['action'] == 'jump: BAS_JUMP_F_START']
    ab_btn = C.Counter(t['action'].split(': ')[1] for t in ab_f0 if ': ' in t['action']).most_common(3)
    aa_st = C.Counter(h['starter'] for h in aa_me).most_common(3)
    ch_me = [h for h in dealt if h['hit_kind'] in ('counter hit', 'punish counter')]; ch_them = [h for h in took if h['hit_kind'] in ('counter hit', 'punish counter')]
    ch_st = C.Counter(h['starter'] for h in ch_me).most_common(4); ch_sit = C.Counter(h['situation'] for h in ch_me).most_common()
    opp_ab = q(f"SELECT action, frames_until FROM timings WHERE set_key IN ({ph}) AND player_id<>? AND event='after block'", *keys, me)
    opp_f0 = sum(1 for t in opp_ab if att(t) and (t['frames_until'] or 0) <= 1)
    my_thr = [h for h in dealt if h['hit_kind'] == 'throw']; thr_sit = C.Counter(h['situation'] for h in my_thr).most_common()
    thr_dp = [h for h in my_thr if h['victim_move'] == 'Drive Parry']
    opp_tech = sum(1 for e in E if e['player_id'] != me and e['type'] == 'throw tech')
    starters = C.Counter()
    for h in dealt: starters[h['starter']] += h['damage']
    top_starter = starters.most_common(1)[0] if starters else ('—', 0)
    # wake-up Cannon Spike: a wake-up timing that chose it, and whether a Cannon Spike hit landed in that round within 2 s
    cs = [t for t in wk if 'Cannon Spike' in t['action']]
    cs_hit = sum(1 for t in cs if any(h['replay_id'] == t['replay_id'] and h['round'] == t['round'] and abs(h['round_timer'] - t['round_timer']) <= 2
                                      and (h['starter'] or '').startswith('Cannon Spike') for h in dealt))
    cs_pun = [h for h in took if (h['victim_move'] or '').startswith('Cannon Spike') and h['situation'] in ('punish', 'oki', 'defense')]
    wk_act = C.Counter(('blocked' if t['action'].startswith('blocked') else 'held still' if t['action'].startswith('nothing') else t['action'].split(': ')[-1].replace('BAS_JUMP_F_START', 'forward jump').replace('BAS_JUMP_B_START', 'back jump').replace('BAS_JUMP_N_START', 'neutral jump')) for t in wk).most_common(6)
    # game-number and round-1 records
    rec = C.defaultdict(lambda: [0, 0]); r1 = [0, 0]
    for g in G:
        w = g['winner_player_id'] == me; rec[g['game_no']][0 if w else 1] += 1
        rw = (g['round_winners'] or '').split(', ')
        if rw and rw[0]: r1[0 if rw[0] == ME else 1] += 1
    for s in S:   # a game missing from the set counts as the loss the MR shows
        st = sets[s['set_id']]
        have = {g['game_no'] for g in G if g['set_key'] == s['set_key']}
        for n in range(1, max(have) + 1):
            if n not in have: rec[n][1] += 1
    lost_g1 = [s for s in S if any(g['set_key'] == s['set_key'] and g['game_no'] == 1 and g['winner_player_id'] != me for g in G)]
    back_g2 = [s for s in lost_g1 if any(g['set_key'] == s['set_key'] and g['game_no'] == 2 and g['winner_player_id'] == me for g in G)]
    back_won = [s for s in lost_g1 if s['set_won']]
    chars = C.Counter(s['opp_char'] for s in S); cmain, cn = chars.most_common(1)[0]
    csets = [s for s in S if s['opp_char'] == cmain]
    ck = {s['set_key'] for s in csets}
    ctook = [h for h in took if h['set_key'] in ck]; ctot = dmg(ctook) or 1
    clens = C.Counter()
    for h in ctook: clens[h['lens'] or 'Unclear / super'] += h['damage']
    cleaks = [(k, v) for k, v in clens.most_common() if k in LEAK][:3]
    cst = C.Counter(h['starter'] for h in ctook).most_common(2)
    drt = lambda p, t: sum(1 for e in E if (e['player_id'] == me) == p and e['type'] == t)
    raw_me, raw_opp = drt(True, 'raw drive rush'), drt(False, 'raw drive rush')
    pr_me, pr_opp = drt(True, 'pressure drive rush cancel'), drt(False, 'pressure drive rush cancel')
    co_me, co_opp = drt(True, 'combo drive rush cancel'), drt(False, 'combo drive rush cancel')
    burn_me, burn_opp = drt(True, 'burnout'), drt(False, 'burnout')
    di_me = use_me['Drive Impact']; dp_me, dp_opp = use_me['Drive Parry'], use_opp['Drive Parry']
    di_pun = [h for h in took if h['victim_move'] == 'Drive Impact']
    lens_drdi = lens('Drive Rush / Impact checked')
    gpg = lambda n: n / max(1, n_games)

    O = []
    def add(kind, area, title, detail, evidence, fix, seen_in, conf='High'):
        O.append(dict(ov_id=f'O{len(O) + 1}', rank=len(O) + 1, kind=kind, area=area, title=title, detail=detail, evidence=evidence, fix=fix, seen_in=seen_in, confidence=conf))

    add('Leak', 'Neutral', 'Neutral decides your sets, and your buttons at mid range are the biggest leak',
        f"{pct(neutral_t, tot_t)} of the damage you took came in neutral (your opponents took {pct(neutral_d, tot_d)} of theirs there). The single biggest source: pressing a button at mid range and getting hit first or whiff-punished, {pct(dmg(mid), tot_t)} of all damage taken ({len(mid)} hits, {about(dmg(mid))}). "
        f"{b0} is the button that gets hit most: {len(b0h)} times for {about(dmg(b0h))} ({b0_lens['Counter-hit at mid range']} at mid range, {b0_lens['Unsafe move punished']} punished on block, {b0_lens['Whiff punished']} whiff punished, {b0_lens['Challenging pressure'] + b0_lens['Challenging okizeme']} challenging pressure or okizeme)."
        + (f" {', '.join(top_btns[1:])} follow." if len(top_btns) > 1 else ''),
        f"Damage taken by what you were doing (chart below); 'Counter-hit at mid range' is the top leak in {mid_top} of {n_sets} sets" + (f" and 40% or more against {', '.join(big_mid)}." if big_mid else '.'),
        f"Pick one or two poke ranges per matchup and stop just outside their 2MK/5MP. Use {b0} as a frame trap up close, not as a neutral poke; at mid range let them press first and whiff-punish with 5HP or 2MK~Drive Rush (Using Pokes, Footsies 101, Footsies Handbook elements on baiting).",
        seen(lambda s: share(s, 'Counter-hit at mid range') >= 0.19))
    add('Leak', 'Neutral', 'Walking forward into throws and buttons',
        f"{pct(dmg(walk), tot_t)} of damage taken ({len(walk)} hits, {about(dmg(walk))}) came while walking forward: {len(walk_thr)} of those were throws (you were thrown {len(thrown)} times in all, {sum(h['situation'] == 'neutral' for h in thrown)} of them in neutral). "
        f"Separately, {len(my_thr_pun)} of your own throw attempts whiffed or were beaten and got punished for {about(dmg(my_thr_pun))}, about {f(round(dmg(my_thr_pun) / max(1, len(my_thr_pun)), -2))} each.",
        'Walked-in hits by starter: ' + ', '.join(f'{mv(k)} {v}' for k, v in walk_st) + f"; victim move 'Throw attempt' {len(my_thr_pun)} times.",
        "Walk-up throw is your best damage tool, but only when you've earned the right to it (after a knockdown or a plus button, or once they respect your pokes). In neutral, walk in smaller steps, stop at throw-range edge and hold a button or block; tech on reaction when they walk in (Improving Shimmy, Delayed Throw Offense, Footsies 101).",
        seen(lambda s: share(s, 'Walked in') >= 0.13))
    add('Leak', 'Neutral', 'Too many jumps and dive kicks for what they return',
        f"{jumps} forward jumps and about {dives} dive kicks in {n_games} games (about {gpg(jumps):.0f} jumps and {gpg(dives):.0f} dive kicks a game). You were anti-aired {len(aa_them)} times; air approaches and their landings cost {pct(dmg(jmp), tot_t)} of damage taken ({len(jmp)} hits). "
        f"You were hit during a dive kick {len(dive_hit)} times ({about(dmg(dive_hit))}); dive kicks started {len(dive_start)} of your combos ({about(dmg(dive_start))}). {len(ab_fj)} times you jumped forward straight out of blockstun.",
        'Anti-airs taken on: ' + ', '.join(f'{k} ×{v}' for k, v in C.Counter(mv(h['victim_move']) for h in aa_them if h['victim_move']).most_common(4)) + '.',
        "Before each jump ask what it's meant to land on (a whiffed button, a fireball you read). Dive kick only as a whiff punish, high enough to land plus; against anti-air-heavy characters cut jumps in half (How to Jump, Air Footsies, DPs and Divekicks, Footsies Handbook ch.5).",
        seen(lambda s: s['jumps_me'] >= 13))
    add('Leak' if len(aa_me) < len(aa_them) else 'Strength', 'Defense', f'Anti-airs: {len(aa_me)} for you, {len(aa_them)} for them',
        f"You landed {len(aa_me)} anti-airs across the {n_sets} sets, {aa_best['aa_me']} of them in one set ({aa_best['opp']}, {aa_best['opp_char']}). In {low_aa} of {n_sets} sets you landed one or none. Their jump-ins that you didn't anti-air cost {pct(dmg(noaa), tot_t)} of your damage taken ({len(noaa)} hits, {about(dmg(noaa))}).",
        'Your anti-airs: ' + ', '.join(f'{k} ×{v}' for k, v in aa_st) + f". The {aa_best['opp']} set shows you can: {aa_best['aa_me']} anti-airs and a {'win' if aa_best['set_won'] else 'loss'} {aa_best['games_won']}-{aa_best['games_lost']}.",
        'Pick one anti-air per range: Cannon Spike when they\'re close, 2HP / 5MK further out. Ten minutes of dummy jump-ins at random timing before ranked (Reactions, How to Jump).',
        seen(lambda s: s['aa_me'] <= 1))
    add('Strength', 'Offense', 'Your frame traps and counter hits are a real strength',
        f"{len(ch_me)} counter hits ({sum(h['hit_kind'] == 'counter hit' for h in ch_me)} counter hits and {sum(h['hit_kind'] == 'punish counter' for h in ch_me)} punish counters) across {n_games} games, mostly with " + ', '.join(f'{k} ({v})' for k, v in ch_st) + f". Your opponents landed {len(ch_them)}. They pressed on the first free frame after blocking {opp_f0} times, and your short gaps catch it.",
        'Counter hits by situation: ' + ', '.join(f'{k} {v}' for k, v in ch_sit) + '.',
        'Keep it: 5LP~5LP frame traps and a 5HP after a plus button. Make sure 5HP counter hit always gets the full confirm (Hit Confirms, Stagger Pressure).',
        seen(lambda s: s['ch_me'] >= 9))
    add('Strength', 'Offense', 'Throws are a top damage source' if top_starter[0] != 'Throw' else 'Throws are your top damage source',
        f"{len(my_thr)} throws for {about(dmg(my_thr))}" + (', more than any other starter' if top_starter[0] == 'Throw' else f' (your top starter is {top_starter[0]}, {about(top_starter[1])})') + f"; {sum(h['situation'] == 'oki' for h in my_thr)} of them on oki and {len(thr_dp)} on Drive Parries. Your opponents teched {opp_tech} throws.",
        'Throws by situation: ' + ', '.join(f'{k} {v}' for k, v in thr_sit) + '.',
        'Keep throwing until they tech twice in a row, then shimmy (Improving Shimmy). Keep throwing their Drive Parry.',
        seen(lambda s: s['thr_me'] >= 4))
    if cs:
        od = [t for t in cs if '(OD)' in t['action']]; plain = [t for t in cs if '(OD)' not in t['action']]
        hit = lambda ts: sum(1 for t in ts if any(h['replay_id'] == t['replay_id'] and h['round'] == t['round'] and abs(h['round_timer'] - t['round_timer']) <= 2
                                                  and (h['starter'] or '').startswith('Cannon Spike') for h in dealt))
        gno = {g['replay_id']: g['game_no'] for g in G}
        where = '; '.join(f"{sid_of[t['set_key']]} G{gno[t['replay_id']]} R{t['round']} @{t['round_timer']}" for t in plain)
        pun_od = [h for h in cs_pun if '(OD)' in (h['victim_move'] or '')]; pun_pl = [h for h in cs_pun if '(OD)' not in (h['victim_move'] or '')]
        add('Strength' if hit(od) >= len(od) / 2 else 'Pattern', 'Defense', 'Wake-up OD Cannon Spike pays at this level, but it is a read',
            f"You used Cannon Spike on wake-up {len(cs)} times: {len(od)} were OD (the invincible reversal, 2 Drive bars each) and hit about {hit(od)} times. "
            + (f"{len(plain)} came out without OD, which isn't a reversal (likely misinputs: {where})" + (f"; {hit(plain)} of those still hit. " if hit(plain) else '. ') if plain else '')
            + f"Across all situations (not just wake-up) you were punished out of a Cannon Spike {len(cs_pun)} times ({about(dmg(cs_pun))}), " + (f"{'all' if len(pun_pl) == len(cs_pun) else len(pun_pl)} of them without OD." if pun_pl else 'every one of them a blocked OD Cannon Spike.'),
            'Wake-up actions: ' + ', '.join(f'{k} {v}' for k, v in wk_act) + '. OD is told apart by the 2 Drive bars it spends (the game names every Cannon Spike animation H).',
            'Keep OD Cannon Spike as a read, but track it: once an opponent blocks one, stop for the rest of the set, and never use it when a punish would kill you or it would burn you out (Defense Equation). For the non-OD ones, practise 623+KK from a knockdown, 10 in a row. Wake-up forward jumps are the riskier habit.',
            seen(lambda s: True), 'Medium')
    add('Pattern', 'Defense', 'After blocking you either press immediately or jump',
        f"Your first action after blocking: {len(ab_att)} attacks ({len(ab_f0)} of them on frame 0-1), {len(ab_hold)} times you held still, {len(ab_jump)} jumps ({len(ab_fj)} forward). Challenging pressure or okizeme cost {pct(dmg(press), tot_t)} of damage taken ({len(press)} hits).",
        'Timings after blockstun; most frame-0 presses were ' + ', '.join(k for k, _ in ab_btn) + '.',
        'Against frame-trappers, hold block one more beat after their string; against throwers, delay tech. Drop the forward jump out of blockstun (Stagger Pressure, Delay Option Selects).',
        seen(lambda s: s['ab_f0'] >= 6), 'Medium')
    gtxt = '. '.join(f'Game {n} record: {w}-{l}' for n, (w, l) in sorted(rec.items()))
    add('Pattern', 'Mental / adaptation', 'You start slowly and adapt' if rec[1][0] < rec[1][1] else 'Game 1 is not the problem',
        f"{gtxt} (a game missing from a set counts as the loss your MR shows). Round 1 of each game: {r1[0]} won, {r1[1]} lost. You lost game 1 in {len(lost_g1)} sets and came back to take game 2 in {len(back_g2)} of them, winning {len(back_won)} of those sets.",
        f'Game results by game number across the {n_sets} sets.',
        'Start each set with your simplest, safest plan (Simple Gameplan): block more, poke less, anti-air, and gather what they do after blocking and on wake-up before taking risks.',
        seen(lambda s: True), 'Medium')
    if cn >= 2:
        add('Pattern', 'Matchups', f'{cmain} is the matchup that keeps coming up',
            f"{cn} of the {n_sets} sets were against {cmain} (" + ', '.join(f"{s['opp']} {s['games_won']}-{s['games_lost']}" for s in csets) + f"). Against {cmain} your top leaks were " + ', '.join(f'{LEAK[k].lower()} ({v / ctot:.0%})' for k, v in cleaks) + '; ' + ' and '.join(f'{mv(k)} hit you {v} times' for k, v in cst) + '.',
            f"{cmain} sets: " + ', '.join(f"{s['set_id']} ({s['opp']})" for s in csets) + '.',
            f'Lab the {cmain} plan: the answers to his two most damaging starters above, and anti-airs for his jump-ins (Matchups & Gameplans).',
            f'{cn} of {n_sets} sets', 'Medium')
    add('Pattern', 'Drive', 'Drive Rush: who uses it from neutral, and burnouts',
        f"Raw Drive Rushes (from neutral): {raw_me} for you, {raw_opp} for your opponents. Pressure Drive Rush cancels (in a blockstring): {pr_me} / {pr_opp}. Combo Drive Rush cancels: {co_me} / {co_opp}. Burnouts {burn_me} / {burn_opp}. Drive Parries {dp_me} / {dp_opp}. You used {di_me} Drive Impacts; {len(di_pun)} times you were hit during one." + (f" You were hit trying to check their Drive Rush or Drive Impact {len(lens_drdi)} times ({pct(dmg(lens_drdi), tot_t)} of damage taken)." if dmg(lens_drdi) else ''),
        'Events per set (Drive Rush type is set from what the opponent was doing when the rush started).',
        'Use pressure Drive Rush cancels off blocked 2MK / 5LP more and save raw Drive Rush for when you have a read; stop raw Drive Impact at mid range (Drive Rush Blockstrings, Dealing with Drive Rush).',
        seen(lambda s: s['dr_opp'] > s['dr_me']), 'Medium')
    json.dump(O, open(f'{out}/overview.json', 'w'), indent=1, ensure_ascii=False)

    Gp = [
     dict(plan_id='G1', rank=1, phase='Round start and neutral', title='You play neutral by pressing first',
          now=f"You walk forward and press {', '.join(top_btns[:3])} at mid range, or walk into throw range. That is where {pct(dmg(mid) + dmg(walk), tot_t)} of your damage taken comes from (buttons at mid range {pct(dmg(mid), tot_t)}, walking in {pct(dmg(walk), tot_t)}).",
          keep='5LP and 2MP as frame-trap buttons up close; 5HP as a counter-hit / whiff-punish button.', change='Hold your ground at the edge of their pokes and make them press first. Whiff-punish with 5HP or 2MK~Drive Rush; poke less, block more in game 1.'),
     dict(plan_id='G2', rank=2, phase='Approach', title='Air approaches are a habit, not a tool',
          now=f'About {gpg(jumps):.0f} forward jumps and {gpg(dives):.0f} dive kicks a game, with {len(aa_them)} anti-airs taken and {len(dive_hit)} hits taken during dive kicks.', keep='Dive kick as a whiff punish when they press at mid range.',
          change='Ground approach first: walk, 2MK~Drive Rush, Spiral Arrow at max range. Jump only when they commit (fireball, whiff).'),
     dict(plan_id='G3', rank=3, phase='Offense', title='Your offense works: frame traps and throws',
          now=f'{len(ch_me)} counter hits and {len(my_thr)} throws; throws on Drive Parries and oki.', keep='Strike / throw / frame-trap mix after knockdowns and plus buttons.',
          change='Confirm 5HP counter hits into the full route every time; shimmy once they tech twice.'),
     dict(plan_id='G4', rank=4, phase='Defense', title='Wake-up reads and jab presses',
          now=(f"Wake-up OD Cannon Spike: {sum('(OD)' in t['action'] for t in cs)} of {len(cs)} wake-up Cannon Spikes were OD. " if cs else '') + 'After blocking you press on frame 0-1 or jump forward.', keep='Wake-up OD Cannon Spike as an occasional read.',
          change=f'Hold block one more beat after their strings; stop forward-jumping out of blockstun; anti-air their jump-ins ({len(aa_me)} vs {len(aa_them)}).'),
     dict(plan_id='G5', rank=5, phase='Resources and adaptation', title='First games and Drive',
          now=f'Game 1 record {rec[1][0]}-{rec[1][1]}, game 2 {rec[2][0]}-{rec[2][1]}. Raw Drive Rush: {raw_me} for you, {raw_opp} for them; pressure cancels {pr_me} / {pr_opp}.', keep='Your game-2 adjustments.',
          change='Use the first game to gather information with low-risk options; Drive Rush after confirms and in blockstrings, not raw Drive Impact.')]
    json.dump(Gp, open(f'{out}/gameplan.json', 'w'), indent=1, ensure_ascii=False)
    Tr = [
     dict(tr_id='T1', rank=1, focus='Neutral spacing: stop pressing at mid range', minutes=20,
          drills=f"Dummy (any character) records walk forward + 2MK and walk forward + throw. Stand at the edge of its 2MK and whiff-punish with 5HP / 2MK~Drive Rush; no {b0} in neutral. Then play 5 ranked games with one rule: no {b0} at mid range.",
          why=f'Buttons at mid range are the top leak in {mid_top} of {n_sets} sets ({pct(dmg(mid), tot_t)} of all damage taken); {b0} got hit {len(b0h)} times.'),
     dict(tr_id='T2', rank=2, focus='Anti-airs', minutes=10, drills='Dummy jump-ins (forward, neutral, back) at random timing from mid range; Cannon Spike when close, 2HP / 5MK further out. 10 in a row before ranked.',
          why=f'{len(aa_me)} anti-airs vs {len(aa_them)} taken; {low_aa} of {n_sets} sets with 0-1 anti-airs.'),
     dict(tr_id='T3', rank=3, focus='Fewer jumps, better dive kicks', minutes=10, drills='Dive kick only as a whiff punish: dummy records 2MK / 5MK at random; dive kick its recovery from max height. In ranked, count your jumps per round and aim for half.',
          why=f'About {gpg(jumps):.0f} jumps and {gpg(dives):.0f} dive kicks a game; hit during a dive kick {len(dive_hit)} times.'),
     dict(tr_id='T4', rank=4, focus='Throw defence while walking forward', minutes=10, drills='Dummy walks forward and throws at random; walk in small steps, react with tech or a jab. Then the reverse: go for your walk-up throw only after a knockdown or a plus button.',
          why=f"Thrown {len(thrown)} times ({sum(h['situation'] == 'neutral' for h in thrown)} in neutral); {len(my_thr_pun)} of your throw attempts were punished for {about(dmg(my_thr_pun))}.")]
    if cn >= 2:
        Tr.append(dict(tr_id='T5', rank=5, focus=f'{cmain} matchup lab', minutes=10,
                       drills=f"Dummy {cmain}: record {' and '.join(mv(k) for k, _ in cst)} at the ranges they hit you from; practise the block, punish or whiff punish for each.",
                       why=f"{cn} of {n_sets} sets were {cmain} ({sum(s['set_won'] for s in csets)}-{cn - sum(s['set_won'] for s in csets)} in those sets)."))
    json.dump(Tr, open(f'{out}/ov_training.json', 'w'), indent=1, ensure_ascii=False)
    print(len(rows), 'sets,', len(O), 'patterns,', len(Gp), 'plan,', len(Tr), 'training')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
