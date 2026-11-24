"""quick-dashboard data, built from the history database (sf6.db).

  python quick_dashboard_from_db.py DB OUTDIR [--write-reads] [--set SET_KEY ...]   (--set: just those sets, on a dashboard or not)

For every set numbered on the 'quick-dashboard' dashboard (table dashboard_sets) it writes the Set review datasets
(sets, games, hits, events, archetypes, habits, story, story_games, punish, findings, fixes, training).
Quick reviews are generated from the stored hits / events / timings / usage; Full reviews keep their
hand-written text from review_docs, with the tiles and tables built from the same stored data.
--write-reads stores the regenerated Quick-review reads and habits back into the database.
Then run overview_from_db.py for the Overview tab.
"""
import json
import spectra as SP, os, re, sys, sqlite3, collections as C
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

ME = paths.PLAYER   # the player in focus (shotokan.json / SHOTOKAN_PLAYER); callers may set it
CHAR_ALIAS = {'char_33': 'Yasmine', 'E_Honda': 'E. Honda', 'M_Bison': 'M. Bison', 'Dee_Jay': 'Dee Jay'}
TEXT_DS = ('story', 'story_games', 'habits', 'archetypes', 'fixes', 'training', 'findings', 'punish', 'set_gameplan', 'prediction', 'tournament')
fmt = lambda n: f'{int(round(n)):,}'


def char(c):
    return CHAR_ALIAS.get(c, c)




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




def usage_from(rows, games):
    """per game: {player: Counter(move)}"""
    out = []
    for g in games:
        d = C.defaultdict(C.Counter)
        for r in rows:
            if r['replay_id'] == g['game_id']: d[r['player']][r['move']] += r['n']
        out.append(d)
    return out


# Character-specific wording for the generated fixes. Moves the player actually used in the set come first;
# these defaults fill in when the set shows none. Characters not listed get neutral wording.
DIVE_KICK = {'Cammy': 'dive kick'}          # characters whose air special is used as a dive kick in these notes
KIT = {
    'Cammy': dict(aa='2MP / 5HP or Cannon Spike', wp='5MK or 2MK~Drive Rush'),
    'Ryu': dict(aa='Shoryuken'), 'Ken': dict(aa='Shoryuken'), 'Akuma': dict(aa='Goshoryuken'), 'Luke': dict(aa='Rising Uppercut'),
    'Terry': dict(aa='Rising Tackle'), 'Guile': dict(aa='Flash Kick'), 'Dee Jay': dict(aa='Jackknife Maximum'),
    'Chun-Li': dict(aa='Tenshokyaku or 2HP'), 'Ed': dict(aa='Psycho Upper'), 'Mai': dict(aa='Ryuuenbu or Hissatsu Shinobibachi'),
}


def kit_context(fchar, mine, theirs, aa_mine):
    """Fill the LENS_FIX templates for this player's character from what they did in the set."""
    def pretty(m):            # raw capture ids for specials the analyzer doesn't name, e.g. ATK_SPA_236P_01_L -> 236P special (L)
        m = str(m)
        if m.startswith('ATK_SPA_'):
            parts = m[8:].split('_')
            return f"{parts[0]} special" + (f" ({parts[-1]})" if parts[-1] in ('L', 'M', 'H', 'EX', 'OD') else '')
        return f'{m} special' if m[:3].isdigit() else m
    top = lambda rows, k: [pretty(m) for m, _ in C.Counter(r[k] for r in rows if r.get(k)).most_common(3)]
    # whiff punishes: ground medium / heavy normals only (no lights, jump-ins, DPs or supers)
    ground = lambda m: len(str(m)) == 3 and str(m)[0] in '1234566789' and str(m)[1:] in ('MP', 'HP', 'MK', 'HK')
    kd = KIT.get(fchar, {})
    aa = top(aa_mine, 'starter')[:2]
    wp = top([h for h in mine if h['situation'] in ('neutral', 'punish') and h['hit_kind'] != 'throw'
              and ground(h['starter'])], 'starter')[:2]
    unsafe = top([h for h in theirs if h['lens'] == 'Unsafe move punished' and h.get('victim_move') not in ('Throw attempt', 'Throw tech attempt')], 'victim_move')
    dive = DIVE_KICK.get(fchar)
    return dict(
        aa=' or '.join(aa) + ' (your anti-airs that landed this set)' if aa else kd.get('aa', f"{fchar}'s most reliable anti-air"),
        wp=' or '.join(wp) + ' (your best neutral starters this set)' if wp else kd.get('wp', 'your fastest long-range button'),
        unsafe=f" ({', '.join(unsafe)})" if unsafe else '',
        and_dives=f' and {dive}s' if dive else '', or_dive=f' or {dive}' if dive else '',
        dive_note=f', and {dive} high enough to land plus' if dive else '', dive_skill=', DPs and Divekicks' if dive else '')


RAW_NAMES = {'SIBERIA': 'Siberian Express', 'PILEDRIVER': 'Screw Piledriver', 'S_Headbutt': 'Sumo Headbutt', 'Gradius': 'Gladius',
             'CA_HIT': 'Critical Art', 'SOMERSAULT': 'Somersault Kick', 'HK_SHIDEN': 'HK Shiden', 'ATK_S_NGA_Near_CT': 'Command grab', 'Scutum_NGA': 'Scutum (grab)'}


def tidy(m):
    """leftover raw capture names in habit text -> readable (4HP_HIT -> 4HP, PILEDRIVER_EX -> Screw Piledriver (OD))"""
    m = str(m)
    od = bool(re.search(r'_(EX|Ex)$', m))
    m = re.sub(r'_(EX|Ex)$', '', m)
    m = re.sub(r'^(\d?[LMH][PK]|\d[LMH][PK])_HIT$', r'\1', m)
    m = re.sub(r'_(Start|START)$', '', m)
    for k, lab in RAW_NAMES.items():
        if m == k or m.startswith(k + '_'):
            m = lab
            break
    else:
        if '_' in m and not m.startswith('ATK_'):
            m = m.replace('_', ' ').title() if m.isupper() else m.replace('_', ' ')
    return m + (' (OD)' if od else '')


LENS_FIX = {
    'Challenging pressure': ('Defense', 'Challenging their pressure',
        'Block one beat longer after a blocked string; press only after a minus move or on a read (Stagger Pressure, Defense Equation).'),
    'Challenging okizeme': ('Defense', 'Challenging their okizeme (pressing on wake-up)',
        'On wake-up, block or use a real reversal on a read; a wake-up button into a meaty is a guess (Defense Equation, coach .shog wake-up rule).'),
    'Whiff punished': ('Neutral', 'Whiffed buttons punished',
        'Space buttons so they reach or don\'t throw them out at that range; walk back after a poke instead of pressing again (Using Pokes, Footsies 101).'),
    'Counter-hit at mid range': ('Neutral', 'Counter-hit at mid range',
        'Stop at the edge of their poke range and let them press first; whiff-punish with {wp} (Using Pokes, Footsies 101).'),
    'Walked in': ('Neutral', 'Walking into their buttons or throws',
        'Walk forward in small steps and stop outside their best poke; hold a whiff punish instead of walking through it (Footsies 101).'),
    'Jumped': ('Neutral', 'Jumps{and_dives} into anti-airs',
        'Ask what each jump is meant to land on; jump{or_dive} only to answer a button{dive_note} (How to Jump{dive_skill}).'),
    'Unsafe move punished': ('Offense', 'Unsafe moves punished',
        'Check the on-block advantage of what got punished{unsafe} and end strings on something safe (Simple Gameplan).'),
    'Pressed after turn ended': ('Offense', 'Pressing again after your blocked string, once their turn had started',
        'After a blocked string, your turn is over once they recover: block, step back, or use a frame trap that closes the gap instead of a new button (Stagger Pressure, Jab Strings).'),
    'Blocking, opened up': ('Defense', 'Opened up while blocking (throws, overheads, mixups)',
        'Midscreen, taking the throw is fine; in the corner back-jump or back-dash instead of teching (Defense Equation, Delay Option Selects).'),
    'Own offense beaten by a reversal': ('Offense', 'Pressure beaten by reversals',
        'Respect their meter: block or bait the reversal when they have Drive or super and the read is likely (Defense & Offense 101).'),
    'Jumped in on (no anti-air)': ('Defense', 'Jump-ins not anti-aired',
        'Anti-air with {aa}; watch for the jump after your blocked strings (How to Jump, Reactions).'),
    'Drive Rush / Drive Impact': ('Neutral', 'Hit out of your Drive Rush or by their Drive Impact',
        'Drive Rush after a confirmed hit; answer their raw Drive Impact with your own (Dealing with Drive Rush, Reactions).'),
}


def load_set(con, key):
    q = lambda sql, *a: [dict(r) for r in con.execute(sql, a).fetchall()]
    name = lambda pid: con.execute('SELECT name FROM players WHERE player_id=?', (pid,)).fetchone()[0]
    s = q('SELECT * FROM sets WHERE set_key=?', key)[0]
    gs = q('SELECT g.*, w.name AS winner FROM games g JOIN players w ON w.player_id=g.winner_player_id WHERE set_key=? ORDER BY game_no', key)
    a = b = 0; games = []
    for g in gs:
        if g['winner'] == ME: a += 1
        else: b += 1
        games.append(dict(game_id=g['replay_id'], game_no=g['game_no'], winner=g['winner'], round_score=g['round_score'],
                          round_winners=g['round_winners'], played_time=g['played_time'], p1_mr=g['p1_mr'], p2_mr=g['p2_mr'],
                          p1_rank=g['p1_rank'] or (f"{g['p1_mr']} MR" if g['p1_mr'] else None), p2_rank=g['p2_rank'] or (f"{g['p2_mr']} MR" if g['p2_mr'] else None),
                          p1=name(g['p1_player_id']), p1_control=g['p1_control'], p2_control=g['p2_control']))
    # set score after each game, counting a game missing from the set as the loss the MR shows
    gno = {g['game_id']: g['game_no'] for g in games}
    sc = [0, 0]; nos = sorted(g['game_no'] for g in games); prog = []
    allno = range(1, max(nos) + 1) if nos else []
    byno = {g['game_no']: g for g in games}
    for n in allno:
        g = byno.get(n)
        if g is None or g['winner'] != ME: sc[1] += 1
        else: sc[0] += 1
        prog.append(f'{sc[0]}-{sc[1]}')
        if g: g['set_score_after'] = f'{sc[0]}-{sc[1]}'
    hq = q("""SELECT h.*, a.name AS attacker, v.name AS victim FROM hits h JOIN players a ON a.player_id=h.attacker_id
              JOIN players v ON v.player_id=h.victim_id WHERE set_key=? ORDER BY hit_id""", key)
    hits = [dict(hit_id=None, game_id=h['replay_id'], game_no=gno[h['replay_id']], round=h['round'], round_timer=h['round_timer'],
                 frame=None, attacker=h['attacker'], victim=h['victim'], damage=h['damage'], hits_in_combo=h['hits_in_combo'],
                 starter=h['starter'], starter_raw=None, first_hit_type=None, hit_kind=h['hit_kind'], first_hit_damage=None,
                 first_hitstun=None, anti_air=bool(h['anti_air']), situation=h['situation'], lens=h['lens'],
                 victim_state=h['victim_state'], victim_move=h['victim_move'], note=h['note'],
                 drive_spent=h['drive_spent'], super_spent=h['super_spent'], drive_gained=h['drive_gained'], drive_damage=h['drive_damage'],
                 knockdown=h['knockdown'], kd_adv=h['kd_adv'], corner_dist=h['corner_dist']) for h in hq]
    ev = [dict(game_id=e['replay_id'], round=e['round'], round_timer=e['round_timer'], frame=None, player=e['player'], type=e['type'], note=e['note'])
          for e in q('SELECT e.*, p.name AS player FROM events e JOIN players p ON p.player_id=e.player_id WHERE set_key=? ORDER BY replay_id, round, round_timer DESC', key)]
    tim = [dict(game_id=t['replay_id'], round=t['round'], round_timer=t['round_timer'], player=t['player'], event=t['event'], action=t['action'], frames_until=t['frames_until'])
           for t in q('SELECT t.*, p.name AS player FROM timings t JOIN players p ON p.player_id=t.player_id WHERE set_key=? ORDER BY timing_id', key)]
    us = q('SELECT u.*, p.name AS player FROM usage u JOIN players p ON p.player_id=u.player_id WHERE set_key=?', key)
    opp = name(s['opp_player_id'])
    docs = {r['dataset']: json.loads(r['rows']) for r in q('SELECT * FROM review_docs WHERE set_key=?', key)}
    return dict(s=s, opp=opp, games=games, hits=hits, ev=ev, tim=tim, use=usage_from(us, games), prog=prog, docs=docs)


def resource_rows(con, key, sid):
    """Drive / super spent per player per round (resources table), for the dashboard"""
    con.row_factory = sqlite3.Row
    g = {r['replay_id']: r['game_no'] for r in con.execute('SELECT replay_id, game_no FROM games WHERE set_key=?', (key,))}
    out = []
    for r in con.execute('SELECT r.*, p.name FROM resources r JOIN players p USING (player_id) WHERE set_key=? ORDER BY replay_id, round', (key,)):
        sup = json.loads(r['supers'] or '[]')
        out.append(dict(res_id=f"{sid}-{r['replay_id']}-{r['round']}-{r['name']}", set_id=sid, game_id=r['replay_id'], game_no=g.get(r['replay_id']), round=r['round'], player=r['name'],
                        drive_rush=r['drive_rush'], drive_rush_cancel=r['drive_rush_cancel'], drive_parry=r['drive_parry'], drive_impact=r['drive_impact'], drive_reversal=r['drive_reversal'],
                        od_specials=r['od_specials'], drive_other=r['drive_other'], drive_total=r['drive_total'], super_bars=r['super_bars'],
                        supers='; '.join(f"L{x.get('level') or min(3, max(1, round(x['bars'])))} {x['move']} ({x['bars']:g} bars{', +%g Drive' % x['drive'] if x.get('drive') else ''}) @{x['round_timer']}" for x in sup) or None, burnouts=r['burnouts'],
                        drive_end=r['drive_end'], super_end=r['super_end'],
                        gain_hit=r['gain_hit'], gain_block=r['gain_block'], parry_regain=r['parry_regain'], loss_block=r['loss_block'], loss_hit=r['loss_hit'],
                        loss_hit_drive_impact=r['loss_hit_drive_impact'], loss_hit_punish_counter=r['loss_hit_punish_counter']))
    out.sort(key=lambda x: (x['game_no'] or 0, x['round'], x['player']))
    return out


def parry_rows(con, key, sid):
    """Each Drive Parry (parries table): cost, hits parried, Drive regained, net, perfect, what happened next"""
    con.row_factory = sqlite3.Row
    g = {r['replay_id']: r['game_no'] for r in con.execute('SELECT replay_id, game_no FROM games WHERE set_key=?', (key,))}
    out = [dict(set_id=sid, game_id=r['replay_id'], game_no=g.get(r['replay_id']), round=r['round'], round_timer=r['round_timer'], player=r['name'],
                frames=r['frames'], drive_before=r['drive_before'], cost=r['cost'], hits_parried=r['hits_parried'], regained=r['regained'], net=r['net'],
                perfect=bool(r['perfect']), next=r['next'])
           for r in con.execute('SELECT x.*, p.name FROM parries x JOIN players p USING (player_id) WHERE set_key=?', (key,))]
    out.sort(key=lambda x: (x['game_no'] or 0, x['round'], -(x['round_timer'] or 0)))
    for i, x in enumerate(out, 1): x['parry_id'] = f'{sid}-P{i:02d}'
    return out


def build_set(sid, order, key, D):
    opp, hits, ev, tim, games, s = D['opp'], D['hits'], D['ev'], D['tim'], D['games'], D['s']
    oppc = char(s['opp_char']); use = D['use']
    for i, x in enumerate(hits, 1):
        x['hit_id'] = f'{sid}-{i:03d}'; x['set_id'] = sid; x['starter_approx'] = x['starter']; x['video_time_s'] = x['round_timer']
        if x['victim'] != ME:
            x['lens'] = None
    for i, e in enumerate(ev, 1):
        e.update(set_id=sid, event_id=f'{sid}-E{i:02d}', video_time_s=None)
        e['note'] = f"burnt out for {e['note']}" if e['type'] == 'burnout' and not str(e['note'] or '').startswith('burnt') else (e['note'] or '')
    for g in games:
        g['set_id'] = sid
    for t in tim:
        t['set_id'] = sid
    mg, og = s['focus_games'], s['opp_games']
    mr = [(g['p1_mr'] if g['p1'] == ME else g['p2_mr']) for g in games]
    omr = [(g['p2_mr'] if g['p1'] == ME else g['p1_mr']) for g in games]
    ctl = {(g['p1_control'] if g['p1'] == ME else g['p2_control']) for g in games}
    times = [g['played_time'] for g in games if g['played_time']]
    when = s['played_date'] + (f" {times[0]}-{times[-1]}" if times else '')
    # rank labels (rank.py): MR at Master, 'MR unknown' for a Master with no MR, the league name below Master
    rk = [(g['p1_rank'] if g['p1'] == ME else g['p2_rank']) for g in games]
    ork = [(g['p2_rank'] if g['p1'] == ME else g['p1_rank']) for g in games]
    mine = next((r for r in rk if r and r != 'MR unknown'), None) or next((r for r in rk if r), None)
    theirs = next((r for r in ork if r and r != 'MR unknown'), None) or next((r for r in ork if r), None)
    mrs = f" · {ME} {mine}" if mine else ''
    mrs += f"{',' if mine else ' ·'} {opp} {theirs}" if theirs else ''
    kind = 'Ranked' if s['ranked'] else 'Casual'
    st = dict(set_id=sid, order=order, format=s['format'] or 'FT2', games=', '.join(g['game_id'] for g in games),
              winner=ME if mg > og else opp, progression=', '.join(D['prog']), max_deficit_overcome=None, note=s['note'] if s['games_missing'] else None,
              p1=ME, p1_char=char(s['focus_char']), p2=opp, p2_char=oppc, p1_games=mg, p2_games=og, ranked=bool(s['ranked']), in_overview=True,
              opp_char=oppc, review=s['review'], date=s['played_date'],
              sub=f"{kind} · Replays {', '.join(g['game_id'] for g in games)} · {when}{mrs} · {s['review']} review" + (f" · {s['note']}" if s['games_missing'] else ''))
    rows = None

    mine = [h for h in hits if h['attacker'] == ME]
    theirs = [h for h in hits if h['victim'] == ME]
    dealt, taken = sum(h['damage'] for h in mine), sum(h['damage'] for h in theirs)
    U = {p: sum((u.get(p, C.Counter()) for u in use), C.Counter()) for p in (ME, opp)}
    jumps = {p: U[p]['BAS_JUMP_F_START'] for p in U}
    dives = sum(max(u.get(ME, C.Counter())['Cannon Strike (dive kick)'], sum(n for m, n in u.get(ME, C.Counter()).items() if m.startswith('Cannon Strike (dive kick) ('))) for u in use)
    DRT = ('raw drive rush', 'pressure drive rush cancel', 'combo drive rush cancel', 'whiff drive rush cancel')
    drk = {p: C.Counter(e['type'] for e in ev if e['player'] == p and e['type'] in DRT) for p in (ME, opp)}
    # aggression counts raw + pressure Drive Rushes only; combo cancels are cashing in on a hit
    dr = {p: drk[p]['raw drive rush'] + drk[p]['pressure drive rush cancel'] for p in (ME, opp)}
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

    # ---- lens leaks (what the player in focus was doing when hit)
    lens = C.defaultdict(list)
    for h in theirs:
        lens[h['lens'] or 'Unclear / super'].append(h)
    leaks = sorted(((k, v) for k, v in lens.items() if k in LENS_FIX), key=lambda kv: -sum(h['damage'] for h in kv[1]))
    fchar = char(s['focus_char'])
    kctx = kit_context(fchar, mine, theirs, aa[ME])
    lf = lambda k: tuple(x.format(**kctx) for x in LENS_FIX[k])
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
        # raw Drive Rush counts half: a cheap, generally safe way to start pressure (1 bar, a hit if checked)
        drw = 0.5 * drk[p]['raw drive rush'] + drk[p]['pressure drive rush cancel']
        agg = rate > 0.35 or drw >= 8 or jumps[p] >= 12 or len(burn[p]) >= 2
        dfn = rate < 0.15 and dr[p] <= 3 and jumps[p] <= 4
        a = 'Aggressive' if agg and not dfn else 'Defensive' if dfn else 'Balanced'
        lean = []
        if jumps[p] >= 10: lean.append(f'air-heavy ({jumps[p]} forward jumps)')
        if dr[p] >= 6: lean.append(f'{dr[p]} raw / pressure Drive Rushes')
        if dp[p] >= 10: lean.append(f'{dp[p]} Drive Parries')
        if rate > 0.35: lean.append('presses early after blocking / on wake-up')
        conf = 'Medium' if len(games) >= 3 else 'Low'
        ev_ = (f"After blocking: {ab['press']} of {ab['n']} first actions were attacks ({ab['f0']} on the first free frame), {ab['nothing']} held still. "
               f"On wake-up: {wk['press']} of {wk['n']} were attacks. {jumps[p]} forward jumps, Drive Rush: {drk[p]['raw drive rush']} raw, {drk[p]['pressure drive rush cancel']} pressure cancels, {drk[p]['combo drive rush cancel']} combo cancels, {dp[p]} Drive Parries, {di[p]} Drive Impacts, "
               f"{len(burn[p])} burnouts. Anti-airs landed: {len(aa[p])}. Counter hits: {len(ch[p])}. Throws landed: {len(thr[p])}, throw techs: {len(techs[p])}.")
        return a, ', '.join(lean) or 'no strong lean', conf, ev_
    arch = []
    for i, p in enumerate((ME, opp)):
        a, lean, conf, e_ = arche(p)
        if p == ME:
            cn = 'What costs you in this set: ' + (', '.join(lf(k)[1].lower() for k, _ in leaks[:2]) or 'nothing stands out') + '.'
        else:
            cn = 'How to beat this: ' + ('block their early presses and frame-trap them' if T[p]['after block']['press'] > T[p]['after block']['nothing'] else 'they hold block: throw them and take their Drive') \
                 + ('; anti-air their jumps' if jumps[p] >= 6 else '') + ('; throw their Drive Parry' if dp[p] >= 8 else '') + '.'
        arch.append(dict(arch_id=f'{sid}-A{i + 1}', set_id=sid, player=p, character=fchar if p == ME else oppc, archetype=a, lean=lean, confidence=conf,
                         evidence=e_, doc_risk_tolerance='—', doc_temperament='—', counter_note=cn))

    # ---- habits
    hab = []
    def H(**k):
        hab.append(dict(habit_id=f'{sid}-H{len(hab) + 1}', set_id=sid, **k))
    for k, v in best[:2]:
        if sum(h['damage'] for h in v) >= 2500:
            H(player=ME, kind='Strength', area='Offense', habit=f'{tidy(k)} was a top damage starter', seen=ats(v, 5), times=len(v),
              fix=f"{len(v)} hits for {fmt(sum(h['damage'] for h in v))} damage. Keep it.", origin='Game data', confidence='High')
    if len(ch[ME]) >= 4:
        H(player=ME, kind='Strength', area='Offense', habit='Counter hits in pressure', seen=ats(ch[ME], 5), times=len(ch[ME]),
          fix='Your frame traps caught their presses. Keep the gaps short.', origin='Game data (first-hit damage, hitstun)', confidence='High')
    if len(thr[ME]) >= 3:
        H(player=ME, kind='Strength', area='Offense', habit='Throws landed', seen=ats(thr[ME], 5), times=len(thr[ME]),
          fix=f"{len(thr[ME])} throws landed vs {len(techs[opp])} teched. Keep throwing until they tech twice in a row (Improving Shimmy).", origin='Game data', confidence='High')
    for k, v in leaks[:3]:
        area, name, fx = lf(k)
        dmg = sum(h['damage'] for h in v)
        if dmg < 1500 and len(v) < 3:
            continue
        H(player=ME, kind='Leak', area=area, habit=name, seen=ats(v, 6), times=len(v),
          fix=f"{fmt(dmg)} damage ({dmg / max(1, taken):.0%} of what you took). {fx}", origin='Game data (what you were doing when hit)', confidence='High' if len(v) >= 3 else 'Medium')
    if len(aa[opp]) > len(aa[ME]) + 1:
        H(player=ME, kind='Leak', area='Anti-air', habit=f'Anti-airs {len(aa[ME])} vs {len(aa[opp])}', seen=ats(aa[opp], 6), times=len(aa[opp]),
          fix=f"You jumped forward {jumps[ME]} times" + (f" and dive kicked about {dives} times" if DIVE_KICK.get(fchar) else '') + f"; they anti-aired {len(aa[opp])}.", origin='Game data (anti-air)', confidence='High')
    # raw Drive Rush is only a leak when it keeps getting checked and the player doesn't adjust
    drc = [h for h in theirs if str(h.get('victim_move') or '').startswith('Drive Rush')]
    drc_games = sorted({h['game_no'] for h in drc})
    if len(drc) >= 3 and len(drc_games) >= 2 and drc_games[-1] == max(g['game_no'] for g in games):
        H(player=ME, kind='Leak', area='Drive', habit='Raw Drive Rush checked repeatedly, no adjustment', seen=ats(drc, 6), times=len(drc),
          fix=f"Checked {len(drc)} times for {fmt(sum(h['damage'] for h in drc))}, still checked in the last game. Drive Rush from further out, "
              "after a blocked button, or bait the check and punish it (Dealing with Drive Rush).", origin='Game data (hit out of Drive Rush)', confidence='Medium')
    if burn[ME]:
        H(player=ME, kind='Leak', area='Drive', habit=f'Burned out {len(burn[ME])}×', seen='; '.join(f"G{next(g['game_no'] for g in games if g['game_id'] == e['game_id'])} R{e['round']} @{e['round_timer']} ({e['note']})" for e in burn[ME]),
          times=len(burn[ME]), fix=f"{dr[ME]} raw / pressure Drive Rushes and {dp[ME]} Drive Parries in the set. Keep 2 bars when behind; Drive Rush after a hit (Holistic Lens).", origin='Game data (burnout flag)', confidence='High')
    ab = T[ME]['after block']
    if ab['n'] >= 8:
        H(player=ME, kind='Pattern', area='Defense', habit='Your first action after blocking', seen=f"{ab['press']} attacks ({ab['f0']} on frame 0-1), {ab['nothing']} held still, {ab['jump']} jumps, {ab['parry']} parries out of {ab['n']}",
          times=ab['n'], fix='Pressing on frame 0 is beaten by frame traps; holding is beaten by throws. Mix it based on what they do after their strings.', origin='Game data (timings) + Stagger Pressure', confidence='Medium')
    for k, v in obest[:2]:
        if sum(h['damage'] for h in v) >= 2000:
            H(player=opp, kind='Strength', area='Offense', habit=f'{tidy(k)} was their top damage starter', seen=ats(v, 5), times=len(v),
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
        area, name, fx = lf(k)
        dmg = sum(h['damage'] for h in v)
        add('set', area if area in ('Neutral', 'Offense', 'Defense') else 'Neutral', 'To improve', r, name, f"{len(v)} hits for {fmt(dmg)} ({dmg / max(1, taken):.0%} of your damage taken).", ats(v, 4), 'See fixes', 'High' if len(v) >= 3 else 'Medium', fx); r += 1
    if burn[ME]:
        add('set', 'Player reads / profile', 'To improve', r, f'{len(burn[ME])} burnout(s)', f"{dr[ME]} raw / pressure Drive Rushes, {dp[ME]} Drive Parries.", '; '.join(f"R{e['round']} @{e['round_timer']}" for e in burn[ME]), 'Holistic Lens', 'High'); r += 1
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
            add(g['game_id'], lf(k)[0] if lf(k)[0] in ('Neutral', 'Offense', 'Defense') else 'Neutral', 'To improve', i + 1, lf(k)[1],
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
                finding=f"Damage: {ME} dealt {fmt(dealt)}, took {fmt(taken)}. Counter hits {len(ch[ME])}/{len(ch[opp])}, anti-airs {len(aa[ME])}/{len(aa[opp])}, throws {len(thr[ME])}/{len(thr[opp])}, burnouts {len(burn[ME])}/{len(burn[opp])} ({ME} / {opp}).",
                evidence='hits, events')]
    fx, tr = [], []
    for i, (k, v) in enumerate(leaks[:3], 1):
        area, name, f_ = lf(k)
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




def main(db, out, write_reads=False, only=None):
    """Build the Set review datasets for every set on the (retired) quick-dashboard, or, with `only` (--set SET_KEY,
    repeatable), for just those sets whether or not they were ever on a dashboard. --write-reads writes a Quick review's
    generated player reads and habits to the database."""
    global ME
    os.makedirs(out, exist_ok=True)
    con = sqlite3.connect(db); con.row_factory = sqlite3.Row
    allD = C.defaultdict(list); allS = []
    if only:
        rows = []
        for i, key in enumerate(only, 1):
            n = con.execute("SELECT set_no FROM dashboard_sets WHERE dashboard='quick-dashboard' AND set_key=?", (key,)).fetchone()
            if not con.execute('SELECT 1 FROM sets WHERE set_key=?', (key,)).fetchone(): raise SystemExit(f'no set {key} in {db}')
            rows.append({'set_key': key, 'set_no': n[0] if n else i})
        focus = con.execute('SELECT p.name FROM sets s JOIN players p ON p.player_id = s.focus_player_id WHERE s.set_key=?', (only[0],)).fetchone()
        if focus and focus[0]: ME = focus[0]   # the set's own focus player
    else:
        rows = con.execute("SELECT set_key, set_no FROM dashboard_sets WHERE dashboard='quick-dashboard' ORDER BY set_no").fetchall()
    paths.require_player(ME)
    for r in rows:
        key, no = r['set_key'], r['set_no']
        sid = f'Set {no}'
        D = load_set(con, key)
        d, stt = build_set(sid, no, key, D)
        stt['set_key'] = key; stt['review'] = D['s']['review']; stt['date'] = D['s']['played_date']; stt['ranked'] = bool(D['s']['ranked'])
        if D['s']['review'] in ('Full', 'Tournament') and D['docs']:
            for ds in TEXT_DS:
                if ds in D['docs']: d[ds] = [dict(x, set_id=sid) for x in D['docs'][ds]]
            if D['docs'].get('sets'):   # keep the hand-written subtitle and notes
                old = D['docs']['sets'][0]
                for k in ('sub', 'note', 'max_deficit_overcome'):
                    if old.get(k): d['sets'][0][k] = old[k]
        SP.attach(d['archetypes'], sid, D['games'], D['hits'], D['tim'], D['ev'], D['use'])
        pids = {ME: con.execute('SELECT player_id FROM players WHERE name=?', (ME,)).fetchone()[0], D['opp']: D['s']['opp_player_id']}
        con.execute('CREATE TABLE IF NOT EXISTS spectra (set_key TEXT, player_id INTEGER, axis TEXT, score INTEGER, label TEXT, evidence TEXT, PRIMARY KEY (set_key, player_id, axis))')
        for a in d['archetypes']:
            for sp in a['spectra']:
                con.execute('INSERT OR REPLACE INTO spectra VALUES (?,?,?,?,?,?)', (key, pids[a['player']], sp['axis'], sp['score'], sp['label'], sp['evidence']))
        if D['s']['review'] in ('Full', 'Tournament') and D['docs']:
            pass
        elif write_reads:
            me_id = con.execute('SELECT player_id FROM players WHERE name=?', (ME,)).fetchone()[0]
            pid = {ME: me_id, D['opp']: D['s']['opp_player_id']}
            src = f'generated from capture stats (quick-dashboard, {sid})'
            con.execute('DELETE FROM reads WHERE set_key=?', (key,)); con.execute('DELETE FROM habits WHERE set_key=?', (key,))
            for a in d['archetypes']:
                con.execute('INSERT INTO reads VALUES (?,?,?,?,?,?,?,?,?,?,?)', (key, pid[a['player']], a['character'], a['archetype'], a['lean'], a['confidence'],
                            a['evidence'], a['counter_note'], a['doc_risk_tolerance'], a['doc_temperament'], src))
            con.executemany('INSERT INTO habits (set_key, player_id, kind, area, habit, seen, times, fix, confidence, source) VALUES (?,?,?,?,?,?,?,?,?,?)',
                            [(key, pid[h['player']], h['kind'], h['area'], h['habit'], h['seen'], h['times'], h['fix'], h['confidence'], src) for h in d['habits']])
        d['resources'] = resource_rows(con, key, sid)
        d['parries'] = parry_rows(con, key, sid)
        for k, v in d.items(): allD[k] += v
        allS.append(stt)
    con.commit()
    for k, v in allD.items():
        json.dump(v, open(f'{out}/{k}.json', 'w'), indent=1, ensure_ascii=False)
    json.dump(allS, open(f'{out}/stats.json', 'w'), indent=1, default=dict)
    print(len(allS), 'sets built ->', out)


if __name__ == '__main__':
    only = [sys.argv[i + 1] for i, x in enumerate(sys.argv) if x == '--set' and i + 1 < len(sys.argv)]
    main(sys.argv[1], sys.argv[2], '--write-reads' in sys.argv, only or None)
