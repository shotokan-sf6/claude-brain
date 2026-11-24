"""Frame-level behaviour counts from REFramework captures, for the player-read spectra (see spectra.py).

usage: behavior.py CAPTURE.json [...]   -> prints per-player counts as JSON
       import behavior; behavior.counts(path) -> {player_name: {...}}

Counts per player per replay (summed over a set before scoring):
- off_n / off_imp   offense: the opponent's blockstun just ended after blocking this player's attack;
                    off_imp = once free, this player started another attack, jump or dash within 0-3 frames (pressing
                    on a fixed timing); anything else (delay, throw later, walk back, block, nothing) counts as a deliberate choice.
- fwd / back        neutral movement frames toward / away from the opponent (walking, dashing, footwork)
- starts / starts_all  neutral exchanges this player started (first attack, jump or dash after 20 quiet frames) / all
- calm_act, calm_f, hot_act, hot_f   actions started (attack, jump, dash, parry) and free frames outside / inside "adversity"
                    windows: the 15 s after taking a 2,000+ combo, and the first 20 s of a round after losing the last one
- drive_spent, super_spent, rounds   Drive and super gauge spent by the player (gauge drops while not being hit or blocking)
"""
import json, sys, os, collections as C
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
from analyze_capture import load_capture, ATTACK_STATES, JUMP_STATES

ACT = ATTACK_STATES | JUMP_STATES | {'DASH', 'KDASH', 'PARRY'}
MOVE = {'WALK', 'FOOTWORK', 'DASH', 'KDASH'}
STUN = {'DAMAGE', 'DEF', 'GETUP', 'NOKI', 'UKEMI', 'HOLD', 'DOWN'}


def counts(path):
    d = load_capture(path); fr = d['frames']; info = d['info']
    name = {'p1': info['p1_name'], 'p2': info['p2_name']}
    out = {name[s]: C.Counter() for s in ('p1', 'p2')}
    N = len(fr)
    def st(k, s): return fr[k][s].get('act_st_name')
    def stun(k, s): return st(k, s) in STUN or (fr[k][s].get('blockstun') or 0) > 0 or (fr[k][s].get('hitstun') or 0) > 0
    # round winners, for "lost the last round"
    rounds = sorted(set(f['round'] for f in fr))
    last_hp = {}
    for f in fr: last_hp[f['round']] = (f['p1']['hp'], f['p2']['hp'])
    lost_prev = {s: set() for s in ('p1', 'p2')}
    for i, r in enumerate(rounds[1:], 1):
        h1, h2 = last_hp[rounds[i - 1]]
        if h1 < h2: lost_prev['p1'].add(r)
        elif h2 < h1: lost_prev['p2'].add(r)
    round_start = {}
    for k, f in enumerate(fr):
        round_start.setdefault(f['round'], k)
    for s, o in (('p1', 'p2'), ('p2', 'p1')):
        c = out[name[s]]
        c['rounds'] = len(rounds)
        # adversity windows: frames after taking a big combo, or early in a round after losing the previous one
        hot = [False] * N
        # big combos taken: HP drop of 2000+ within a run of hitstun
        k = 0
        while k < N:
            if (fr[k][s].get('hitstun') or 0) > 0 or st(k, s) == 'DAMAGE':
                j = k; hp0 = fr[k - 1][s]['hp'] if k else fr[k][s]['hp']
                while j < N and ((fr[j][s].get('hitstun') or 0) > 0 or st(j, s) in ('DAMAGE', 'DOWN')): j += 1
                if hp0 - fr[min(j, N - 1)][s]['hp'] >= 2000:
                    for x in range(j, min(N, j + 900)):
                        if fr[x]['round'] == fr[j - 1]['round']: hot[x] = True
                k = j + 1
            else:
                k += 1
        for r in lost_prev[s]:
            a = round_start[r]
            for x in range(a, min(N, a + 1200)):
                if fr[x]['round'] == r: hot[x] = True
        quiet = 0
        for k in range(1, N):
            a, b = fr[k][s], fr[k][o]; pa = fr[k - 1][s]
            sa, pas = a.get('act_st_name'), pa.get('act_st_name')
            started = sa in ACT and pas not in ACT
            neutral = not stun(k, s) and not stun(k, o) and sa not in ('WIN', 'LOSE')
            # offense: opponent leaves blockstun
            if (fr[k - 1][o].get('blockstun') or 0) > 0 and (b.get('blockstun') or 0) == 0 and b.get('act_st_name') != 'DAMAGE':
                # wait until this player is free (out of their own recovery); a new move before that is a chain/cancel
                j0 = k
                while j0 < min(N, k + 40) and st(j0, s) in ACT and fr[j0][s].get('action_id') == fr[k][s].get('action_id'): j0 += 1
                if j0 < N and st(j0, s) not in ACT and not stun(j0, s):
                    c['off_n'] += 1
                    for j in range(j0, min(N, j0 + 30)):
                        if stun(j, s): break
                        if st(j, s) in ACT:
                            if j - j0 <= 3: c['off_imp'] += 1
                            break
            if neutral:
                if sa in MOVE:
                    toward = (b['posX'] - a['posX']) * (a.get('spdX') or 0)
                    if toward > 0: c['fwd'] += 1
                    elif toward < 0: c['back'] += 1

            if not stun(k, s) and sa not in ('WIN', 'LOSE'):
                if hot[k]: c['hot_f'] += 1
                else: c['calm_f'] += 1
                if started:
                    if hot[k]: c['hot_act'] += 1
                    else: c['calm_act'] += 1
            # neutral exchange starts
            if not (st(k, s) in ACT or st(k, o) in ACT or stun(k, s) or stun(k, o)):
                quiet += 1
            else:
                if quiet >= 20:
                    if st(k, s) in ACT: out[name[s]]['starts'] += 1
                    out[name[s]]['starts_all'] += 1
                quiet = 0
            # gauges
            if not stun(k, s):
                dd = pa['drive'] - a['drive']
                if dd > 0 and not pa.get('burnout'): c['drive_spent'] += dd   # the drop that empties the gauge counts
                ds = pa['super'] - a['super']
                if ds > 0: c['super_spent'] += ds
            if a.get('burnout') and not pa.get('burnout'): c['burnouts'] += 1
    return {k: dict(v) for k, v in out.items()}


def set_counts(paths):
    tot = C.defaultdict(C.Counter)
    for p in paths:
        for k, v in counts(p).items(): tot[k].update(v)
    return {k: dict(v) for k, v in tot.items()}


if __name__ == '__main__':
    print(json.dumps({os.path.basename(p): counts(p) for p in sys.argv[1:]}, indent=1))
