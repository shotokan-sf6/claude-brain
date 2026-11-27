"""Jump-ins and anti-airs for shared_core_analyze.py: every jump toward the opponent, what it led to, and whether the
defender was free to anti-air it.

A jump starts on a BAS_JUMP_<F|N|B>_START action and ends when the jumper is back on the ground (posY ~ 0). Back jumps
are left out. A forward or neutral jump counts as a jump-in when something happened (contact either way) or it landed
within IN_RANGE of the defender (centre to centre; round start is 3.0 apart). Results, by the first thing that happened:
  anti-air      the jumper was hit in the air by a grounded defender
  air-to-air    the jumper was hit in the air by an airborne defender (counts as answered)
  trade         both were hit on the same frame
  parried       the defender Drive Parried the jump-in attack
  hit           the jump-in attack hit the defender
  blocked       the defender blocked it (the jumper lands plus and starts offense); `opened` = the defender was hit within
                OPEN_FRAMES after that block
  landing punished  the jump whiffed and the jumper was hit right after landing (in range, no attack or a whiffed one)
  empty         landed in range with no contact either way (an empty jump into a throw or low, or nothing)
Whether the defender could anti-air it:
  free          at some point from REACT frames after the jump started to AA_LEAD frames before the jumper's attack
                connected (or landed), the defender was walking, standing, crouching or turning, so an anti-air was possible
  busy          never free in that window: in their own attack or its recovery, blockstun, hitstun, a knockdown, or jumping.
                A hit or block taken while busy isn't a failure to anti-air.
Anti-air rate = anti-air + air-to-air + trade over the jump-ins the defender was free for (an answered jump always counts
as free: pressing the anti-air isn't being busy). Stopped rate adds parried and landing punished (the jump got nothing).
Jumps hit during their pre-jump frames never leave the ground and aren't counted.
`pressed` notes an attack the defender started after reacting (an anti-air attempt that didn't land, or that traded).
"""
REACT = 12          # frames: about the time to see a jump start (Structure note #2: 12-15 visual)
AA_LEAD = 5         # frames before the jump-in connects by which an anti-air must have started (fast anti-air normals)
IN_RANGE = 1.8      # posX distance at landing for a contact-less jump to count as a jump-in (about a crouching 2MK away)
OPEN_FRAMES = 120   # a blocked jump-in "opened" the defender when they were hit within 2 seconds of leaving blockstun
FREE = {'FOOTWORK', 'WALK', 'STAND', 'SIT', 'SITD', 'STAND_TURN', 'SIT_TURN', 'DUCK_WALK'}
ATTACKS = ('ATCK', 'SPECIAL', 'SUPER', 'THROW', 'CATCH')
GROUND_Y = 0.05
ANTI_AIRED = ('anti-air', 'air-to-air', 'trade')
ANSWERED = ANTI_AIRED + ('parried', 'landing punished')   # stopped: the jump-in got nothing


def _dir(name):
    for d, k in (('forward', 'JUMP_F'), ('neutral', 'JUMP_N'), ('back', 'JUMP_B')):
        if k in name: return d
    return None


def jump_ins(fr, names, side_name, side_char, other, mname, pretty, rid):
    out = []
    for j in ('p1', 'p2'):
        d = other[j]; k = 1
        while k < len(fr):
            nm = mname(names, j, fr[k][j].get('action_id')) or ''
            pn = mname(names, j, fr[k - 1][j].get('action_id')) or ''
            if fr[k].get('fight_st') != 4 or not ('JUMP_' in nm and nm.endswith('_START')) or pn == nm:
                k += 1; continue
            dirn = _dir(nm); s0 = k; rnd = fr[k]['round']
            # airborne span: first frame off the ground, then back on it
            up = next((x for x in range(s0, min(len(fr), s0 + 20)) if (fr[x][j].get('posY') or 0) > GROUND_Y), None)
            if up is None: k += 1; continue
            land = next((x for x in range(up, min(len(fr), up + 150)) if (fr[x][j].get('posY') or 0) <= GROUND_Y or fr[x]['round'] != rnd), None)
            if land is None: k = up + 1; continue
            if dirn == 'back': k = land; continue
            res = None; at = None; jmove = None; trade = False
            for x in range(up, min(len(fr), land + 3)):
                J, D, pJ, pD = fr[x][j], fr[x][d], fr[x - 1][j], fr[x - 1][d]
                n_j = mname(names, j, J.get('action_id')) or ''
                if J.get('act_st_name') in ATTACKS and jmove is None and x <= land: jmove = n_j
                jh = J.get('act_st_name') == 'DAMAGE' and pJ.get('act_st_name') != 'DAMAGE'
                dh = D.get('act_st_name') == 'DAMAGE' and pD.get('act_st_name') != 'DAMAGE'
                db = (D.get('blockstun') or 0) > 0 and not (pD.get('blockstun') or 0) > 0
                if jh and dh: res, trade = 'trade', True
                elif jh and x < land: res = 'air-to-air' if (D.get('posY') or 0) > GROUND_Y else 'anti-air'
                elif jh: res = 'landing punished'
                elif dh: res = 'hit'
                elif db: res = 'parried' if D.get('act_st_name') == 'PARRY' else 'blocked'
                if res: at = x; break
            dx = abs((fr[land][j].get('posX') or 0) - (fr[land][d].get('posX') or 0))
            if res is None:
                if dx > IN_RANGE or dirn is None: k = land; continue
                res = 'empty'
            ref = at if at is not None else land
            w0, w1 = s0 + REACT, ref - AA_LEAD
            free = any(fr[x][d].get('act_st_name') in FREE for x in range(w0, max(w0, w1) + 1))
            if res in ANSWERED: free = True   # they answered it, so they could (pressing the anti-air itself isn't 'busy')
            pressed = None
            for x in range(w0, ref + 1):
                if fr[x][d].get('act_st_name') in ATTACKS and fr[x - 1][d].get('act_st_name') not in ATTACKS:
                    pressed = mname(names, d, fr[x][d].get('action_id')); break
            opened = None
            if res == 'blocked':
                e = next((x for x in range(at, min(len(fr), at + 60)) if not (fr[x][d].get('blockstun') or 0) > 0), at)
                opened = any(fr[x][d].get('act_st_name') == 'DAMAGE' for x in range(e, min(len(fr), e + OPEN_FRAMES)) if fr[x]['round'] == rnd)
            aa_by = None
            if res in ('anti-air', 'air-to-air', 'trade'):
                for x in range(at, max(s0, at - 30), -1):   # the defender's attack that connected (on a trade they're already in a damage state)
                    st_ = fr[x][d].get('act_st_name')
                    if st_ in ATTACKS: aa_by = mname(names, d, fr[x][d].get('action_id')); break
            out.append(dict(game_id=rid, round=rnd + 1, round_timer=fr[s0]['round_timer'], jumper=side_name[j], defender=side_name[d],
                            direction=dirn, jump_attack=pretty(jmove, side_char[j]) if jmove else None, result=res,
                            defender_free=free, pressed=pretty(pressed, side_char[d]) if pressed else None,
                            anti_air_with=pretty(aa_by, side_char[d]) if aa_by else None, opened=opened,
                            distance=round(abs((fr[s0][j].get('posX') or 0) - (fr[s0][d].get('posX') or 0)), 2), land_distance=round(dx, 2)))
            k = land
    return out




def summary(rows, name):
    """Per defender: jump-ins faced, how each ended, and the anti-air / stopped rates' parts over the free ones."""
    xs = [x for x in rows if x['defender'] == name]
    f_ = [x for x in xs if x['defender_free']]
    return dict(jump_ins=len(xs), jump_ins_free=len(f_),
                jump_ins_anti_aired=sum(x['result'] in ANTI_AIRED for x in f_), jump_ins_stopped=sum(x['result'] in ANSWERED for x in f_),
                jump_ins_hit=sum(x['result'] == 'hit' for x in f_), jump_ins_blocked=sum(x['result'] == 'blocked' for x in f_),
                jump_ins_empty=sum(x['result'] == 'empty' for x in f_),
                jump_ins_busy=len(xs) - len(f_), jump_ins_busy_hit=sum(x['result'] == 'hit' for x in xs if not x['defender_free']),
                jump_ins_busy_blocked=sum(x['result'] == 'blocked' for x in xs if not x['defender_free']),
                jump_ins_blocked_opened=sum(bool(x['opened']) for x in xs if x['result'] == 'blocked'))
