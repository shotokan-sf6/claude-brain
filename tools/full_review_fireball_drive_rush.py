"""Fireball Drive Rush (FDR): how often each player throws a fireball and Drive Rushes behind it, what follows
(strike / throw, low / other), what it's worth, and how it relates to winning rounds.

    python tools/full_review_fireball_drive_rush.py DB [--replays DIR] [--ranked-only] [--player NAME] [--min-uses N]
                                                         [--window F] [--out file.json] [--md file.md]

Definitions (from the captures, every reviewed game in sf6.db):
- fireball: a ground projectile special, by its analyzer label (FIREBALLS below). Characters without one, or whose
  projectile isn't named yet (JP), aren't measured.
- FDR: a Drive Rush (Drive Parry > Drive Rush) started within --window frames (default 30) of the fireball's recovery.
  Fireball state when the rush starts: 'hit' (the opponent was hit by it), 'blocked' (blockstun), 'neutral' (neither).
- follow-up: the first attack, throw or special started after the rush (within 45 frames): throw / low strike (2LK,
  2MK, 2HK and labels with 'low') / other strike (mid, overhead or unclear: overheads aren't told apart from mids) /
  none.
- outcome, over the exchange (from the rush start until 30 frames after both players are out of hit / block stun,
  capped at 300 frames): damage dealt and taken (HP lost, including the fireball's own damage if it lands after the
  rush starts), who was hit first ('opened up' / 'checked' / 'neither').
- Drive spent: Drive just before the fireball minus Drive 20 frames after the rush starts (OD fireball + the rush),
  in bars (10,000 a bar).
- comparison: other raw drive rushes by the same players (from Drive Parry, not within the window of a fireball, not
  in a combo), measured the same way.
- rounds: each player-round with its FDR count and net damage, and whether that player won the round.

Caveats: the winner of a round gets more chances to FDR (more time with the opponent in blockstun), so win rates by
usage show association, not cause. Damage in the exchange includes the follow-up combo and any punish of it.
"""
import argparse, collections as C, json, os, re, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shared_core_analyze as A

# label prefixes (after A.pretty) that are ground fireballs, per character; raw-name fallbacks for unnamed codes
FIREBALLS = {
    'Ryu': ('Hadoken',), 'Ken': ('Hadoken',), 'Akuma': ('Gou Hadoken',), 'Luke': ('Sand Blast',),
    'Chun-Li': ('Kikoken', 'KIKOUKEN'), 'Guile': ('Sonic Boom', 'SONICBOOM'), 'AKI': ('Nightshade Pulse',),
    'Mai': ('Kachousen',), 'Ingrid': ('Sun Shot',), 'Sagat': ('High Tiger Shot', 'Low Tiger Shot', 'Tiger Shot'),
    'Dhalsim': ('Yoga Fire', 'YOGAFIRE'), 'Dee Jay': ('Air Slasher',), 'Terry': ('Power Wave',),
    'Rashid': ('Whirlwind Shot',), 'Juri': ('Fuha (stock release)',),
}
NOT_FB = ('follow-up', 'Zanku')
LOW = re.compile(r'^2[LMH]K\b|low', re.I)
RUSH = ('ATK_CTA_RUSH', 'ATK_CTA_DASH')
STUN = ('DAMAGE', 'DEF', 'DOWN', 'HOLD', 'PASSIVE')


def is_fb(label, char):
    pre = FIREBALLS.get(char)
    return bool(pre) and label.startswith(pre) and not any(x in label for x in NOT_FB)


def exchange(fr, k, me, op):
    """From frame k: damage dealt / taken, who was hit first, and the end frame."""
    hp0m, hp0o = fr[k][me]['hp'], fr[k][op]['hp']
    first, quiet, end = None, 0, min(len(fr) - 1, k + 300)
    rnd = fr[k]['round']
    for q in range(k, min(len(fr), k + 300)):
        if fr[q]['round'] != rnd: end = q - 1; break
        a, b = fr[q][me], fr[q][op]
        if first is None:
            if b.get('act_st_name') in ('DAMAGE', 'HOLD') or b['hp'] < hp0o: first = 'opened up'
            elif a.get('act_st_name') in ('DAMAGE', 'HOLD') or a['hp'] < hp0m: first = 'checked'
        busy = a.get('act_st_name') in STUN or b.get('act_st_name') in STUN or (a.get('blockstun') or 0) or (b.get('blockstun') or 0)
        quiet = 0 if busy else quiet + 1
        if q > k + 20 and quiet >= 30: end = q; break
    dealt = max(0, hp0o - fr[end][op]['hp']); taken = max(0, hp0m - fr[end][me]['hp'])
    return dealt, taken, first or 'neither', end


def follow_up(fr, r, me, char, names):
    for q in range(r + 1, min(len(fr), r + 45)):
        raw = A.mname(names, me, fr[q][me]['action_id'])
        if raw.startswith(RUSH) or raw.startswith(('DPA', 'BAS_', 'GRD', 'DMG', 'DEF')): continue
        lab = A.pretty(raw, char)
        if raw.startswith(('NGS', 'NGA')) or lab.startswith('Throw') or 'command grab' in lab.lower() or 'throw' in lab.lower():
            return 'throw', lab
        if re.match(r'^\d{4}_', raw): continue   # block / hit reactions
        if raw.startswith(('ATK_', 'SPA_', 'SAA', 'SA')) or re.match(r'^\d', raw):
            return ('low strike' if LOW.search(lab) else 'other strike'), lab
    return 'none', ''


STANCE = {0: 'stand', 1: 'crouch', 2: 'air'}


def contact(fr, r, me, op, names, span=60):
    """First contact from frame r: (result 'hit' | 'blocked' | 'thrown' | 'checked first' | 'no contact',
    the defender's stance the frame before (stand / crouch / air), frame of contact)."""
    for q in range(r + 1, min(len(fr), r + span)):
        b = fr[q][op]; st = b.get('act_st_name')
        res = 'thrown' if st == 'HOLD' else 'hit' if st == 'DAMAGE' else 'blocked' if (st == 'DEF' or (b.get('blockstun') or 0) > 0) else None
        if res:
            return res, STANCE.get(fr[q - 1][op].get('stance'), '?'), q
        if fr[q][me].get('act_st_name') in ('DAMAGE', 'HOLD'): return 'checked first', '-', q
    return 'no contact', '-', None


def classify(raw, lab):
    if raw.startswith(('NGS', 'NGA')) or lab.startswith('Throw') or 'command grab' in lab.lower() or 'throw' in lab.lower():
        return 'throw'
    if re.match(r'^\d{4}_', raw) or raw.startswith(RUSH) or raw.startswith(('DPA', 'BAS_', 'GRD', 'DMG', 'DEF')): return None
    if raw.startswith(('ATK_', 'SPA_', 'SAA', 'SA')) or re.match(r'^\d', raw):
        return 'low strike' if LOW.search(lab) else 'other strike'
    return None


def mixup(fr, q0, me, op, names, char):
    """The decision after the first blocked button: the attacker's next new attack or throw (within 40 frames of the
    defender leaving blockstun), its result and the defender's stance. Waiting (no new action) counts as 'wait'."""
    cur = A.mname(names, me, fr[q0][me]['action_id'])
    free = None
    for q in range(q0, min(len(fr), q0 + 120)):
        b = fr[q][op]
        if free is None and not (b.get('blockstun') or 0) and b.get('act_st_name') != 'DEF': free = q
        if free is not None and q > free + 40: break
        raw = A.mname(names, me, fr[q][me]['action_id'])
        if raw != cur:
            cur = raw; kind = classify(raw, A.pretty(raw, char))
            if kind:
                res, guard, _ = contact(fr, q - 1, me, op, names, 40)
                return kind, A.pretty(raw, char), res, guard
        if fr[q][me].get('act_st_name') == 'DAMAGE': return 'checked', '', 'checked first', '-'
    return 'wait', '', '-', '-'


def scan_game(cap, sides):
    fr, mn, inf = cap['frames'], cap['move_names'], cap['info']
    rr = inf.get('round_results') or []
    rows, rounds = [], C.defaultdict(lambda: dict(fdr=0, net=0, raw=0, raw_net=0, won=None))
    for me, op in (('p1', 'p2'), ('p2', 'p1')):
        pid, char = sides[me]
        name = lambda q: A.mname(mn, me, fr[q][me]['action_id'])
        fb_end = -10 ** 6; fb_k = None; prev = None; in_fb = False
        k = 0
        while k < len(fr):
            raw = name(k)
            if raw != prev:
                lab = A.pretty(raw, char)
                if is_fb(lab, char) and not in_fb:
                    in_fb, fb_k, fb_lab = True, k, lab
                elif in_fb and not is_fb(lab, char):
                    in_fb, fb_end = False, k
                if raw.startswith(RUSH) and not (prev or '').startswith(RUSH):
                    o = fr[k][op]; st = o.get('act_st_name')
                    # raw drive rush only: not a cancel (a cancel drops 3 bars at once)
                    cancel = any((fr[j - 1][me].get('drive') or 0) - (fr[j][me].get('drive') or 0) >= 25000 for j in range(max(1, k - 5), min(len(fr), k + 25)))
                    rnd = fr[k]['round']
                    won = None
                    if rnd < len(rr): won = (rr[rnd].get('win_player') == (0 if me == 'p1' else 1))
                    if not cancel and st not in ('DAMAGE', 'DOWN') and fr[k]['round_timer'] is not None:
                        fdr = fb_k is not None and k - fb_end <= ARGS.window and fb_end >= fb_k
                        if fdr:
                            seen = 'neutral'
                            for q in range(fb_k, k + 1):
                                s = fr[q][op].get('act_st_name')
                                if s == 'DAMAGE': seen = 'hit'; break
                                if s == 'DEF' or (fr[q][op].get('blockstun') or 0) > 0: seen = 'blocked'
                        k0 = k
                        for j in range(k - 1, max(0, k - 20), -1):   # include the Drive Parry the rush came from
                            if name(j).startswith('DPA'): k0 = j
                            elif k0 != k: break
                        d0 = fr[max(0, (fb_k if fdr else k0) - 1)][me].get('drive') or 0
                        d1 = fr[min(len(fr) - 1, k + 20)][me].get('drive') or 0
                        dealt, taken, first, end = exchange(fr, k, me, op)
                        fu, fu_lab = follow_up(fr, k, me, char, mn)
                        res, guard, cq = contact(fr, k, me, op, mn)
                        mx = mixup(fr, cq, me, op, mn, char) if res == 'blocked' else ('', '', '', '')
                        row = dict(kind='fdr' if fdr else 'raw', player_id=pid, char=char, round=rnd + 1, timer=fr[k]['round_timer'],
                                   fireball=fb_lab if fdr else '', od=bool(fdr and '(OD)' in fb_lab), state=seen if fdr else '',
                                   follow=fu, follow_move=fu_lab, contact=res, guard=guard, mix=mx[0], mix_move=mx[1], mix_result=mx[2], mix_guard=mx[3], dealt=dealt, taken=taken, net=dealt - taken, first=first,
                                   drive_bars=round(max(0, d0 - d1) / 10000, 1), won_round=won)
                        rows.append(row)
                        rk = rounds[(pid, rnd)]; rk['won'] = won; rk['char'] = char
                        if fdr: rk['fdr'] += 1; rk['net'] += row['net']
                        else: rk['raw'] += 1; rk['raw_net'] += row['net']
                prev = raw
            k += 1
        # rounds with no rush at all still count for the win-rate comparison
        for rnd in sorted({f['round'] for f in fr}):
            if rnd < len(rr):
                rk = rounds[(pid, rnd)]; rk['won'] = rr[rnd].get('win_player') == (0 if me == 'p1' else 1); rk['char'] = char
    return rows, rounds


def summarize(rows):
    n = len(rows)
    if not n: return dict(n=0)
    s = lambda k: sum(r[k] for r in rows)
    fu = C.Counter(r['follow'] for r in rows); first = C.Counter(r['first'] for r in rows)
    bars = s('drive_bars')
    return dict(n=n, dealt_per=round(s('dealt') / n), taken_per=round(s('taken') / n), net_per=round(s('net') / n),
                opened_up=round(first['opened up'] / n, 2), checked=round(first['checked'] / n, 2),
                drive_bars_per=round(bars / n, 2), net_per_bar=round(s('net') / bars) if bars else None,
                contact=dict(C.Counter(r['contact'] for r in rows).most_common()),
                first_button_vs_guard={f'{fu} vs {g}': dict(n=len(sel), landed=round(sum(r['contact'] in ('hit', 'thrown') for r in sel) / len(sel), 2), net_per=round(sum(r['net'] for r in sel) / len(sel)))
                       for fu in ('low strike', 'other strike', 'throw') for g in ('stand', 'crouch')
                       for sel in [[r for r in rows if r['follow'] == fu and r['guard'] == g]] if sel},
                after_block=dict(n=sum(r['contact'] == 'blocked' for r in rows), **{m: dict(
                    n=len(sel), share=round(len(sel) / max(1, sum(r['contact'] == 'blocked' for r in rows)), 2),
                    landed=round(sum(r['mix_result'] in ('hit', 'thrown') for r in sel) / len(sel), 2),
                    checked=round(sum(r['mix_result'] == 'checked first' for r in sel) / len(sel), 2),
                    net_per=round(sum(r['net'] for r in sel) / len(sel)),
                    vs_stand=round(sum(r['mix_result'] in ('hit', 'thrown') for r in sel if r['mix_guard'] == 'stand') / max(1, sum(r['mix_guard'] == 'stand' for r in sel)), 2),
                    vs_crouch=round(sum(r['mix_result'] in ('hit', 'thrown') for r in sel if r['mix_guard'] == 'crouch') / max(1, sum(r['mix_guard'] == 'crouch' for r in sel)), 2))
                    for m in ('throw', 'low strike', 'other strike', 'wait', 'checked')
                    for sel in [[r for r in rows if r['contact'] == 'blocked' and r['mix'] == m]] if sel}),
                follow={k: dict(n=v, net_per=round(sum(r['net'] for r in rows if r['follow'] == k) / v),
                                opened_up=round(sum(r['first'] == 'opened up' for r in rows if r['follow'] == k) / v, 2))
                        for k, v in fu.most_common()})


def main():
    global ARGS
    ap = argparse.ArgumentParser(); ap.add_argument('db'); ap.add_argument('--replays', default=None)
    ap.add_argument('--ranked-only', action='store_true'); ap.add_argument('--player'); ap.add_argument('--min-uses', type=int, default=8)
    ap.add_argument('--window', type=int, default=30); ap.add_argument('--out'); ap.add_argument('--md')
    ARGS = ap.parse_args()
    rep = ARGS.replays or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(ARGS.db))), 'replays')
    c = sqlite3.connect(ARGS.db)
    names = dict(c.execute('select player_id, name from players'))
    q = 'select g.replay_id, g.p1_player_id, g.p2_player_id, g.p1_char, g.p2_char from games g join sets s using(set_key)'
    if ARGS.ranked_only: q += ' where s.ranked = 1'
    games = c.execute(q).fetchall()
    rows, rounds, done = [], {}, 0
    for rid, p1, p2, c1, c2 in games:
        if FIREBALLS.get(c1) is None and FIREBALLS.get(c2) is None: continue
        path = next((p for p in (f'{rep}/{rid}.json.gz', f'{rep}/{rid}.json') if os.path.exists(p)), None)
        if not path: continue
        cap = A.load_capture(path)
        rw, rd = scan_game(cap, {'p1': (p1, c1), 'p2': (p2, c2)})
        for r in rw: r['replay_id'] = rid; r['player'] = names.get(r['player_id'])
        rows += rw
        for (pid, rnd), v in rd.items(): rounds[(rid, pid, rnd)] = v
        done += 1
    if ARGS.player:
        want = {x.strip().lower() for x in ARGS.player.split(',')}
        rows = [r for r in rows if (r['player'] or '').lower() in want]
        rounds = {k: v for k, v in rounds.items() if (names.get(k[1]) or '').lower() in want}
    fdr = [r for r in rows if r['kind'] == 'fdr']; raw = [r for r in rows if r['kind'] == 'raw']
    out = dict(games=done, window=ARGS.window, fdr_all=summarize(fdr), raw_drive_rush_all=summarize(raw),
               fdr_by_state={st: summarize([r for r in fdr if r['state'] == st]) for st in ('blocked', 'neutral', 'hit')},
               fdr_od=summarize([r for r in fdr if r['od']]), fdr_not_od=summarize([r for r in fdr if not r['od']]))
    # characters (only rounds where the player is a fireball character)
    fb_rounds = [v for v in rounds.values() if v.get('char') in FIREBALLS and v['won'] is not None]
    out['by_char'] = {}
    for ch in sorted(FIREBALLS):
        rr = [v for v in fb_rounds if v['char'] == ch]
        if not rr: continue
        f = [r for r in fdr if r['char'] == ch]
        out['by_char'][ch] = dict(rounds=len(rr), fdr_per_round=round(len(f) / len(rr), 2), **{'fdr': summarize(f)},
                                  raw=summarize([r for r in raw if r['char'] == ch]))
    # players
    pl = C.defaultdict(list)
    for r in fdr: pl[(r['player'], r['char'])].append(r)
    prounds = C.Counter((names.get(k[1]), v['char']) for k, v in rounds.items() if v['won'] is not None)
    out['by_player'] = sorted(([dict(player=p, char=ch, rounds=prounds[(p, ch)], fdr_per_round=round(len(v) / max(1, prounds[(p, ch)]), 2), **summarize(v))
                                for (p, ch), v in pl.items() if len(v) >= ARGS.min_uses]), key=lambda d: -d['n'])
    # contribution to wins: player-rounds of fireball characters
    def wr(sel):
        sel = list(sel); return dict(rounds=len(sel), win_rate=round(sum(v['won'] for v in sel) / len(sel), 3) if sel else None)
    out['rounds'] = dict(
        no_fdr=wr(v for v in fb_rounds if v['fdr'] == 0),
        fdr_any=wr(v for v in fb_rounds if v['fdr'] > 0),
        fdr_net_positive=wr(v for v in fb_rounds if v['fdr'] > 0 and v['net'] > 0),
        fdr_net_zero=wr(v for v in fb_rounds if v['fdr'] > 0 and v['net'] == 0),
        fdr_net_negative=wr(v for v in fb_rounds if v['fdr'] > 0 and v['net'] < 0),
        fdr_2plus=wr(v for v in fb_rounds if v['fdr'] >= 2))
    byp = C.defaultdict(lambda: [[], []])
    for (rid, pid, rnd), v in rounds.items():
        if v.get('char') in FIREBALLS and v['won'] is not None: byp[pid][v['fdr'] > 0].append(v['won'])
    diffs = [(len(a) + len(b), sum(b) / len(b) - sum(a) / len(a)) for a, b in byp.values() if len(a) >= 3 and len(b) >= 3]
    out['rounds']['within_player'] = dict(players=len(diffs), win_rate_gain_with_fdr=round(sum(w * d for w, d in diffs) / sum(w for w, _ in diffs), 3) if diffs else None)
    won = [v for v in fb_rounds if v['won']]; lost = [v for v in fb_rounds if not v['won']]
    out['rounds']['fdr_per_round_won'] = round(sum(v['fdr'] for v in won) / max(1, len(won)), 2)
    out['rounds']['fdr_per_round_lost'] = round(sum(v['fdr'] for v in lost) / max(1, len(lost)), 2)
    out['rounds']['fdr_net_per_round_won'] = round(sum(v['net'] for v in won) / max(1, len(won)))
    out['rounds']['fdr_net_per_round_lost'] = round(sum(v['net'] for v in lost) / max(1, len(lost)))
    out['rounds']['fdr_net_share_of_round'] = round(sum(v['net'] for v in fb_rounds) / max(1, len(fb_rounds)) / 10000, 3)
    if ARGS.out: json.dump(dict(summary=out, rows=rows), open(ARGS.out, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
