"""Ranked FT2 sets (.shog, Cammy) -> quick-dashboard data.

Reads analyzer output in ranked/a/<key>/ for every set in SETS (built from log.tsv),
writes ranked/data/*.json: per-set rows tagged with set_id (continuing after the quick-dashboard's
Set 1 and Set 2) plus overview datasets. Per-set notes are generated from capture stats.
"""
import json, os, sys, ast, re, collections as C
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

ROOT = os.environ.get('SHOTOKAN_RANKED_DIR') or os.path.join(paths.HOME, 'ranked')   # the working folder (ranked/a/<key>/, log.tsv)
OUT = f'{ROOT}/data'
os.makedirs(OUT, exist_ok=True)
ME = '.shog'
CHAR_ALIAS = {'char_33': 'Yasmine', 'E_Honda': 'E. Honda', 'M_Bison': 'M. Bison', 'Dee_Jay': 'Dee Jay'}
MISSING = {'5L78C3YHG_WYYXLXDUV': dict(progression='1-0, 1-1, 1-2',
    game_id='WYYXLXDUV', note='Game 2 (replay ID WBF54DB9G) was not found in CFN, so it is not analysed; the 1-2 result is inferred from your MR (1678 before game 1 and again before game 3)')}
fmt = lambda n: f'{int(round(n)):,}'


def char(c):
    return CHAR_ALIAS.get(c, c)


def W(n, d):
    json.dump(d, open(f'{OUT}/{n}.json', 'w'), indent=1, ensure_ascii=False)


def at(h):
    return f"G{h['game_no']} R{h['round']} @{h['round_timer']}"


def ats(rows, k=6):
    rows = sorted(rows, key=lambda h: -h['damage'])[:k]
    rows = sorted(rows, key=lambda h: (h['game_no'], h['round'], -h['round_timer']))
    return '; '.join(f"{at(h)} ({fmt(h['damage'])})" if h['damage'] else at(h) for h in rows)


def usage(report):
    """per game: {player: Counter(move)} from the analyzer's 'usage' lines"""
    games, cur = [], None
    for line in open(report):
        if line.startswith('# Game'):
            cur = {}; games.append(cur)
        m = re.match(r'\s+usage (.+?): (\[.*\])$', line)
        if m and cur is not None:
            cur[m.group(1)] = C.Counter(dict(ast.literal_eval(m.group(2))))
    return games


# ---------------------------------------------------------------- per-set build
LENS_FIX = {
    'Challenging pressure': ('Defense', 'Challenging their pressure',
        'Block one beat longer after a blocked string; press only after a minus move or on a read (Stagger Pressure, Defense Equation).'),
    'Challenging okizeme': ('Defense', 'Challenging their okizeme (pressing on wake-up)',
        'On wake-up, block or use a real reversal on a read; a wake-up button into a meaty is a guess (Defense Equation, coach .shog wake-up rule).'),
    'Whiff punished': ('Neutral', 'Whiffed buttons punished',
        'Space buttons so they reach or don\'t throw them out at that range; walk back after a poke instead of pressing again (Using Pokes, Footsies 101).'),
    'Counter-hit at mid range': ('Neutral', 'Counter-hit at mid range',
        'Stop at the edge of their poke range and let them press first; whiff-punish with 5MK or 2MK~Drive Rush (Using Pokes, Footsies 101).'),
    'Walked in': ('Neutral', 'Walking into their buttons or throws',
        'Walk forward in small steps and stop outside their best poke; hold a whiff punish instead of walking through it (Footsies 101).'),
    'Jumped': ('Neutral', 'Jumps and dive kicks into anti-airs',
        'Ask what each jump is meant to land on; dive kick only as a whiff punish, high enough to land plus (How to Jump, DPs and Divekicks).'),
    'Unsafe move punished': ('Offense', 'Unsafe moves punished',
        'Check the on-block advantage of what got punished (Spiral Arrow, Cannon Spike, dive kick landings) and end strings on something safe (Simple Gameplan).'),
    'Pressed after turn ended': ('Offense', 'Pressing again after your blocked string, once their turn had started',
        'After a blocked string, your turn is over once they recover: block, step back, or use a frame trap that closes the gap instead of a new button (Stagger Pressure, Jab Strings).'),
    'Blocking, opened up': ('Defense', 'Opened up while blocking (throws, overheads, mixups)',
        'Midscreen, taking the throw is fine; in the corner back-jump or back-dash instead of teching (Defense Equation, Delay Option Selects).'),
    'Own offense beaten by a reversal': ('Offense', 'Pressure beaten by reversals',
        'Respect their meter: block or bait the reversal when they have Drive or super and the read is likely (Defense & Offense 101).'),
    'Jumped in on (no anti-air)': ('Defense', 'Jump-ins not anti-aired',
        'Anti-air with 2MP/5HP or Cannon Spike; watch for the jump after your blocked 2MK (How to Jump, Reactions).'),
    'Drive Rush / Drive Impact': ('Neutral', 'Hit out of your Drive Rush or by their Drive Impact',
        'Drive Rush after a confirmed hit; answer their raw Drive Impact with your own (Dealing with Drive Rush, Reactions).'),
}


def build_set(sid, order, key, rows):
    A = f'{ROOT}/a/{key}'
    opp = rows[0]['opp']
    hits = json.load(open(f'{A}/hits.json'))
    ev = json.load(open(f'{A}/events.json'))
    tim = json.load(open(f'{A}/timings.json'))
    games = json.load(open(f'{A}/games.json'))
    st = json.load(open(f'{A}/sets.json'))[0]
    import sf6db
    info = [sf6db.load_info(paths.find_capture(r['id'])) for r in rows]
    side = ['p1' if i['p1_name'] == ME else 'p2' for i in info]
    oppc = char(info[0]['p2_char' if side[0] == 'p1' else 'p1_char'])
    use = usage(f'{A}/report.md')
    for x in hits:
        x['set_id'] = sid; x['starter_approx'] = x['starter']; x['video_time_s'] = x['round_timer']
        if x['victim'] != ME:
            x['lens'] = None
    for i, e in enumerate(ev, 1):
        e.update(set_id=sid, event_id=f'{sid}-E{i:02d}', video_time_s=None)
        e['note'] = f"burnt out for {e['note']}" if e['type'] == 'burnout' else (e['note'] or '')
    for g in games:
        g['set_id'] = sid
    for t in tim:
        t['set_id'] = sid
    mg = sum(g['winner'] == ME for g in games); og = len(games) - mg
    missing = MISSING.get(key)
    if missing:
        og += 1
        renum = {missing['game_id']: 3}
        for x in games + hits + tim:
            if x['game_id'] in renum: x['game_no'] = renum[x['game_id']]
        for x in games:
            if x['game_id'] in renum: x['set_score_after'] = '1-2'
    mr0, mr1 = rows[0]['mr'], rows[-1]['mr']
    st.update(set_id=sid, order=order, p1=ME, p1_char='Cammy', p2=opp, p2_char=oppc, p1_games=mg, p2_games=og, winner=ME if mg > og else opp,
              ranked=True, opp_char=oppc,
              sub=f"Ranked · Replays {', '.join(r['id'] for r in rows)} · {rows[0]['date']} {rows[0]['time']}-{rows[-1]['time']} · .shog {mr0} MR at the start")
    if missing:
        st.update(winner=opp, progression=missing['progression'], note=missing['note'],
                  sub=st['sub'] + ' · ' + missing['note'])
    for k in list(st):
        if k.endswith('_games') and k not in ('p1_games', 'p2_games'):
            del st[k]

    mine = [h for h in hits if h['attacker'] == ME]
    theirs = [h for h in hits if h['victim'] == ME]
    dealt, taken = sum(h['damage'] for h in mine), sum(h['damage'] for h in theirs)
    U = {p: sum((u.get(p, C.Counter()) for u in use), C.Counter()) for p in (ME, opp)}
    jumps = {p: U[p]['BAS_JUMP_F_START'] for p in U}
    dives = U[ME]['Cannon Strike (dive kick)'] + U[ME]['Cannon Strike (dive kick) (L)'] + U[ME]['Cannon Strike (dive kick) (H)'] + U[ME]['Cannon Strike (dive kick) (OD)']
    dr = {p: U[p]['Drive Rush'] for p in U}
    dp = {p: U[p]['Drive Parry'] for p in U}
    di = {p: U[p]['Drive Impact'] for p in U}
    burn = {p: [e for e in ev if e['player'] == p and e['type'] == 'burnout'] for p in (ME, opp)}
    aa = {p: [h for h in hits if h['attacker'] == p and h['anti_air']] for p in (ME, opp)}
    ch = {p: [h for h in hits if h['attacker'] == p and h['hit_kind'] in ('counter hit', 'punish counter')] for p in (ME, opp)}
    thr = {p: [h for h in hits if h['attacker'] == p and h['hit_kind'] == 'throw'] for p in (ME, opp)}
    techs = {p: [e for e in ev if e['player'] == p and e['type'] == 'throw tech'] for p in (ME, opp)}

    def timing(p, evn):
        ts = [t for t in tim if t['player'] == p and t['event'] == evn]
        acts = C.Counter(t['action'].split(':')[0] for t in ts)
        f0 = sum(1 for t in ts if t['frames_until'] is not None and t['frames_until'] <= 1 and not t['action'].startswith('blocked'))
        press = sum(n for a, n in acts.items() if a in ('atck', 'special', 'super', 'throw'))
        return dict(n=len(ts), f0=f0, press=press, nothing=acts.get('nothing (30f)', 0), jump=acts.get('jump', 0), parry=acts.get('parry', 0))
    T = {p: {e: timing(p, e) for e in ('after block', 'wake-up')} for p in (ME, opp)}

    # ---- lens leaks (what .shog was doing when hit)
    lens = C.defaultdict(list)
    for h in theirs:
        lens[h['lens'] or 'Unclear / super'].append(h)
    leaks = sorted(((k, v) for k, v in lens.items() if k in LENS_FIX), key=lambda kv: -sum(h['damage'] for h in kv[1]))
    starters = C.defaultdict(list)
    for h in mine:
        starters[h['starter']].append(h)
    best = sorted(starters.items(), key=lambda kv: -sum(h['damage'] for h in kv[1]))
    ostart = C.defaultdict(list)
    for h in theirs:
        ostart[h['starter']].append(h)
    obest = sorted(ostart.items(), key=lambda kv: -sum(h['damage'] for h in kv[1]))

    # ---- archetypes (rule of thumb, low/medium confidence)
    def arche(p):
        ab, wk = T[p]['after block'], T[p]['wake-up']
        rate = (ab['press'] + wk['press']) / max(1, ab['n'] + wk['n'])
        agg = rate > 0.35 or dr[p] >= 8 or jumps[p] >= 12 or len(burn[p]) >= 2
        dfn = rate < 0.15 and dr[p] <= 3 and jumps[p] <= 4
        a = 'Aggressive' if agg and not dfn else 'Defensive' if dfn else 'Balanced'
        lean = []
        if jumps[p] >= 10: lean.append(f'air-heavy ({jumps[p]} forward jumps)')
        if dr[p] >= 6: lean.append(f'{dr[p]} Drive Rushes')
        if dp[p] >= 10: lean.append(f'{dp[p]} Drive Parries')
        if rate > 0.35: lean.append('presses early after blocking / on wake-up')
        conf = 'Medium' if len(games) >= 3 else 'Low'
        ev_ = (f"After blocking: {ab['press']} of {ab['n']} first actions were attacks ({ab['f0']} on the first free frame), {ab['nothing']} held still. "
               f"On wake-up: {wk['press']} of {wk['n']} were attacks. {jumps[p]} forward jumps, {dr[p]} Drive Rushes, {dp[p]} Drive Parries, {di[p]} Drive Impacts, "
               f"{len(burn[p])} burnouts. Anti-airs landed: {len(aa[p])}. Counter hits: {len(ch[p])}. Throws landed: {len(thr[p])}, throw techs: {len(techs[p])}.")
        return a, ', '.join(lean) or 'no strong lean', conf, ev_
    arch = []
    for i, p in enumerate((ME, opp)):
        a, lean, conf, e_ = arche(p)
        if p == ME:
            cn = 'What costs you in this set: ' + (', '.join(LENS_FIX[k][1].lower() for k, _ in leaks[:2]) or 'nothing stands out') + '.'
        else:
            cn = 'How to beat this: ' + ('block their early presses and frame-trap them' if T[p]['after block']['press'] > T[p]['after block']['nothing'] else 'they hold block: throw them and take their Drive') \
                 + ('; anti-air their jumps' if jumps[p] >= 6 else '') + ('; throw their Drive Parry' if dp[p] >= 8 else '') + '.'
        arch.append(dict(arch_id=f'{sid}-A{i + 1}', set_id=sid, player=p, character='Cammy' if p == ME else oppc, archetype=a, lean=lean, confidence=conf,
                         evidence=e_, doc_risk_tolerance='—', doc_temperament='—', counter_note=cn))

    # ---- habits
    hab = []
    def H(**k):
        hab.append(dict(habit_id=f'{sid}-H{len(hab) + 1}', set_id=sid, **k))
    for k, v in best[:2]:
        if sum(h['damage'] for h in v) >= 2500:
            H(player=ME, kind='Strength', area='Offense', habit=f'{k} was a top damage starter', seen=ats(v, 5), times=len(v),
              fix=f"{len(v)} hits for {fmt(sum(h['damage'] for h in v))} damage. Keep it.", origin='Game data', confidence='High')
    if len(ch[ME]) >= 4:
        H(player=ME, kind='Strength', area='Offense', habit='Counter hits in pressure', seen=ats(ch[ME], 5), times=len(ch[ME]),
          fix='Your frame traps caught their presses. Keep the gaps short.', origin='Game data (first-hit damage, hitstun)', confidence='High')
    if len(thr[ME]) >= 3:
        H(player=ME, kind='Strength', area='Offense', habit='Throws landed', seen=ats(thr[ME], 5), times=len(thr[ME]),
          fix=f"{len(thr[ME])} throws landed vs {len(techs[opp])} teched. Keep throwing until they tech twice in a row (Improving Shimmy).", origin='Game data', confidence='High')
    for k, v in leaks[:3]:
        area, name, fx = LENS_FIX[k]
        dmg = sum(h['damage'] for h in v)
        if dmg < 1500 and len(v) < 3:
            continue
        H(player=ME, kind='Leak', area=area, habit=name, seen=ats(v, 6), times=len(v),
          fix=f"{fmt(dmg)} damage ({dmg / max(1, taken):.0%} of what you took). {fx}", origin='Game data (what you were doing when hit)', confidence='High' if len(v) >= 3 else 'Medium')
    if len(aa[opp]) > len(aa[ME]) + 1:
        H(player=ME, kind='Leak', area='Anti-air', habit=f'Anti-airs {len(aa[ME])} vs {len(aa[opp])}', seen=ats(aa[opp], 6), times=len(aa[opp]),
          fix=f"You jumped forward {jumps[ME]} times and dive kicked about {dives} times; they anti-aired {len(aa[opp])}.", origin='Game data (anti-air)', confidence='High')
    if burn[ME]:
        H(player=ME, kind='Leak', area='Drive', habit=f'Burned out {len(burn[ME])}×', seen='; '.join(f"G{next(g['game_no'] for g in games if g['game_id'] == e['game_id'])} R{e['round']} @{e['round_timer']} ({e['note']})" for e in burn[ME]),
          times=len(burn[ME]), fix=f"{dr[ME]} Drive Rushes and {dp[ME]} Drive Parries in the set. Keep 2 bars when behind; Drive Rush after a hit (Holistic Lens).", origin='Game data (burnout flag)', confidence='High')
    ab = T[ME]['after block']
    if ab['n'] >= 8:
        H(player=ME, kind='Pattern', area='Defense', habit='Your first action after blocking', seen=f"{ab['press']} attacks ({ab['f0']} on frame 0-1), {ab['nothing']} held still, {ab['jump']} jumps, {ab['parry']} parries out of {ab['n']}",
          times=ab['n'], fix='Pressing on frame 0 is beaten by frame traps; holding is beaten by throws. Mix it based on what they do after their strings.', origin='Game data (timings) + Stagger Pressure', confidence='Medium')
    for k, v in obest[:2]:
        if sum(h['damage'] for h in v) >= 2000:
            H(player=opp, kind='Strength', area='Offense', habit=f'{k} was their top damage starter', seen=ats(v, 5), times=len(v),
              fix=f"{fmt(sum(h['damage'] for h in v))} damage. (How to beat it) learn its range and answer it in the lab.", origin='Game data', confidence='High')
    oab = T[opp]['after block']
    if oab['n'] >= 6:
        H(player=opp, kind='Pattern', area='Defense', habit='Their first action after blocking', seen=f"{oab['press']} attacks ({oab['f0']} on frame 0-1), {oab['nothing']} held still, {oab['jump']} jumps, {oab['parry']} parries out of {oab['n']}",
          times=oab['n'], fix='(How to beat it) ' + ('frame-trap after your blocked strings' if oab['press'] > oab['nothing'] else 'throw after your blocked strings'), origin='Game data (timings)', confidence='Medium')
    if burn[opp]:
        H(player=opp, kind='Leak', area='Drive', habit=f'Burned out {len(burn[opp])}×', seen='; '.join(f"R{e['round']} @{e['round_timer']}" for e in burn[opp]), times=len(burn[opp]),
          fix='(How to beat it) pressure them while burnt out.', origin='Game data', confidence='High')

    # ---- story
    ST = []
    def add(scope, cat, pol, rank, head, det, evd, sk, conf, tr=None, chg=None):
        ST.append(dict(story_id=f'{sid}-S{len(ST) + 1:02d}', set_id=sid, scope=scope, category=cat, polarity=pol, change=chg, rank=rank,
                       headline=head, detail=det, evidence=evd, skills=sk, try_this=tr, confidence=conf))
    r = 1
    for k, v in best[:2]:
        add('set', 'Offense', 'Worked well', r, f'{k}: {fmt(sum(h["damage"] for h in v))} damage', f"{len(v)} hits started with {k}.", ats(v, 4), 'Hit Confirms', 'High'); r += 1
    if len(ch[ME]) >= 3:
        add('set', 'Offense', 'Worked well', r, f'{len(ch[ME])} counter hits', 'Frame traps and buttons into their presses.', ats(ch[ME], 4), 'Stagger Pressure', 'High'); r += 1
    if len(aa[ME]) >= 2:
        add('set', 'Defense', 'Worked well', r, f'{len(aa[ME])} anti-airs', 'Their jumps were answered.', ats(aa[ME], 4), 'How to Jump', 'High'); r += 1
    r = 1
    for k, v in leaks[:3]:
        area, name, fx = LENS_FIX[k]
        dmg = sum(h['damage'] for h in v)
        add('set', area if area in ('Neutral', 'Offense', 'Defense') else 'Neutral', 'To improve', r, name, f"{len(v)} hits for {fmt(dmg)} ({dmg / max(1, taken):.0%} of your damage taken).", ats(v, 4), 'See fixes', 'High' if len(v) >= 3 else 'Medium', fx); r += 1
    if burn[ME]:
        add('set', 'Player reads / profile', 'To improve', r, f'{len(burn[ME])} burnout(s)', f"{dr[ME]} Drive Rushes, {dp[ME]} Drive Parries.", '; '.join(f"R{e['round']} @{e['round_timer']}" for e in burn[ME]), 'Holistic Lens', 'High'); r += 1
    a_opp = arch[1]
    add('set', 'Player reads / profile', 'Change', 9, f"{opp}'s read: {a_opp['archetype']}", a_opp['lean'], 'Player reads', 'Player Archetypes', 'Low')
    sg = []
    for g in games:
        gh = [h for h in hits if h['game_id'] == g['game_id']]
        big = sorted(gh, key=lambda h: -h['damage'])[:3]
        rw = g['round_winners'].split(', ')
        summ = '; '.join(f"R{i + 1} {'won' if w == ME else 'lost'}" for i, w in enumerate(rw)) + '. Biggest hits: ' + '; '.join(f"{h['attacker']} {h['starter']} {fmt(h['damage'])} (R{h['round']} @{h['round_timer']})" for h in big) + '.'
        md = sum(h['damage'] for h in gh if h['attacker'] == ME); td = sum(h['damage'] for h in gh if h['victim'] == ME)
        tp = big[0] if big else None
        sg.append(dict(game_id=g['game_id'], set_id=sid, game_no=g['game_no'], result=f"{g['winner']} {g['round_score'] if g['winner'] == ME else '-'.join(reversed(g['round_score'].split('-')))}",
                       set_score_after=g['set_score_after'], summary=summ + f' Damage: dealt {fmt(md)}, took {fmt(td)}.',
                       turning_point=f"R{tp['round']} @{tp['round_timer']}: {tp['attacker']} {tp['starter']} for {fmt(tp['damage'])}." if tp else '—'))
        gl = C.defaultdict(list)
        for h in gh:
            if h['victim'] == ME and h['lens'] in LENS_FIX:
                gl[h['lens']].append(h)
        for i, (k, v) in enumerate(sorted(gl.items(), key=lambda kv: -sum(h['damage'] for h in kv[1]))[:2]):
            add(g['game_id'], LENS_FIX[k][0] if LENS_FIX[k][0] in ('Neutral', 'Offense', 'Defense') else 'Neutral', 'To improve', i + 1, LENS_FIX[k][1],
                f"{len(v)} hits, {fmt(sum(h['damage'] for h in v))}.", ats(v, 3), '—', 'Medium')
        gm = C.defaultdict(list)
        for h in gh:
            if h['attacker'] == ME: gm[h['starter']].append(h)
        for k, v in sorted(gm.items(), key=lambda kv: -sum(h['damage'] for h in kv[1]))[:1]:
            add(g['game_id'], 'Offense', 'Worked well', 3, f'{k}: {fmt(sum(h["damage"] for h in v))}', f'{len(v)} hits.', ats(v, 3), '—', 'Medium')

    # ---- punish table
    pun = []
    for p, o in ((ME, opp), (opp, ME)):
        ph = C.defaultdict(list)
        for h in hits:
            if h['attacker'] == p and h['situation'] == 'punish':
                ph[h['victim_move']].append(h)
        for vm, v in sorted(ph.items(), key=lambda kv: -sum(h['damage'] for h in kv[1]))[:4]:
            pun.append(dict(punish_id=f'{sid}-P{len(pun) + 1}', set_id=sid, punisher=p, what_was_punished=f"{o}'s {vm}", example=ats(v, 3),
                            punish_used=', '.join(sorted({h['starter'] for h in v})), damage=', '.join(fmt(h['damage']) for h in v[:3]), verdict='Punished.'))

    # ---- findings, fixes, training
    fnd = [dict(finding_id=f'{sid}-F1', set_id=sid, skill='game data', category='Summary', applies_to='both', confidence='High',
                finding=f"Damage: .shog dealt {fmt(dealt)}, took {fmt(taken)}. Counter hits {len(ch[ME])}/{len(ch[opp])}, anti-airs {len(aa[ME])}/{len(aa[opp])}, throws {len(thr[ME])}/{len(thr[opp])}, burnouts {len(burn[ME])}/{len(burn[opp])} (.shog / {opp}).",
                evidence='hits, events')]
    fx, tr = [], []
    for i, (k, v) in enumerate(leaks[:3], 1):
        area, name, f_ = LENS_FIX[k]
        fx.append(dict(fix_id=f'{sid}-X{i}', set_id=sid, player=ME, rank=i, fix=name, drill=f_, why=f"{len(v)} hits, {fmt(sum(h['damage'] for h in v))} damage."))
    for i, (b, m) in enumerate((('Primary 50%', 30), ('Secondary 25%', 15), ('Free play 25%', 15))):
        if i < len(fx):
            tr.append(dict(block_id=f'{sid}-T{i + 1}', set_id=sid, block=b, focus=fx[i]['fix'], drills=fx[i]['drill'], minutes=m))
    stats = dict(set_id=sid, opp=opp, opp_char=oppc, games_won=mg, games_lost=og, set_won=mg > og, dealt=dealt, taken=taken,
                 rounds_won=sum(w == ME for g in games for w in g['round_winners'].split(', ')), rounds_lost=sum(w != ME for g in games for w in g['round_winners'].split(', ')),
                 ch_me=len(ch[ME]), ch_opp=len(ch[opp]), aa_me=len(aa[ME]), aa_opp=len(aa[opp]), thr_me=len(thr[ME]), thr_opp=len(thr[opp]),
                 tech_me=len(techs[ME]), tech_opp=len(techs[opp]), burn_me=len(burn[ME]), burn_opp=len(burn[opp]), jumps_me=jumps[ME], dives_me=dives,
                 dr_me=dr[ME], dp_me=dp[ME], di_me=di[ME], dr_opp=dr[opp], dp_opp=dp[opp],
                 ab_n=T[ME]['after block']['n'], ab_press=T[ME]['after block']['press'], ab_f0=T[ME]['after block']['f0'], ab_hold=T[ME]['after block']['nothing'],
                 wk_n=T[ME]['wake-up']['n'], wk_press=T[ME]['wake-up']['press'], wk_f0=T[ME]['wake-up']['f0'],
                 starters_me=C.Counter({k: sum(h['damage'] for h in v) for k, v in starters.items()}), lens_me=C.Counter({k: sum(h['damage'] for h in v) for k, v in lens.items()}),
                 lens_n=C.Counter({k: len(v) for k, v in lens.items()}), sit_me=C.Counter(), sit_opp=C.Counter(), usage_me=U[ME])
    for h in theirs: stats['sit_me'][h['situation']] += h['damage']
    for h in mine: stats['sit_opp'][h['situation']] += h['damage']
    return dict(sets=[st], games=games, hits=hits, events=ev, archetypes=arch, habits=hab, story=ST, story_games=sg, punish=pun,
                findings=fnd, fixes=fx, training=tr, timings=tim), stats


def load_sets():
    rows = [dict(zip(['id', 'time', 'opp', 'result', 'mr', 'video'], l.rstrip('\n').split('\t'))) for l in list(open(f'{ROOT}/log.tsv'))[1:] if l.strip()]
    for r in rows:
        r['mr'] = int(r['mr']); r['date'] = '11/16/2026'
    rows.reverse()  # log.tsv follows Sean's list, newest first
    sets, cur = [], []
    for r in rows:
        if cur and (r['opp'] != cur[-1]['opp'] or len([x for x in cur if x['result'] == 'W']) >= 2 or len([x for x in cur if x['result'] == 'L']) >= 2):
            sets.append(cur); cur = []
        cur.append(r)
    if cur: sets.append(cur)
    return sets


if __name__ == '__main__':
    import sys
    sets = load_sets()
    allD = C.defaultdict(list); allS = []
    for n, rows in enumerate(sets, 3):
        key = '_'.join(r['id'] for r in rows)
        if not os.path.exists(f'{ROOT}/a/{key}/hits.json'):
            print('missing analysis', key, file=sys.stderr); continue
        d, s = build_set(f'Set {n}', n, key, rows)
        for k, v in d.items(): allD[k] += v
        allS.append(s)
    for k, v in allD.items():
        W(k, v)
    json.dump(allS, open(f'{ROOT}/stats.json', 'w'), indent=1, default=dict)
    print(len(allS), 'sets built')
