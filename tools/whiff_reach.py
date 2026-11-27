"""Measure each character's ground-normal reach from the captures, for the whiff-punish step (shared_core_whiffs.py).

  python whiff_reach.py [REPLAYS_DIR]   (default: ./replays)

For every ground normal (ATK_<numpad><button>) that made contact (the opponent went into hitstun or blockstun while it was
out), the distance between the two players (posX, centre to centre) on the contact frame. Stored per character in
frame_data/<char>.json under "reach": {input: [p90 distance, max distance, contacts]}. The 90th percentile is used as the
button's reach so one odd spacing (a hurtbox stretched by the opponent's own move) doesn't set it.
"""
import collections as C, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shared_core_analyze as A

FD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frame_data')


def contacts(path):
    d = A.load_capture(path); fr = d['frames']; names = d.get('move_names', {}); info = d['info']
    out = []
    for side, o in (('p1', 'p2'), ('p2', 'p1')):
        ch = A._norm(info.get(side + '_char') or ''); ch = A._CHAR_ALIAS.get(ch, ch)
        for k in range(1, len(fr)):
            v, pv = fr[k][o], fr[k - 1][o]
            hit = (v.get('hitstun') or 0) > 0 and not (pv.get('hitstun') or 0) > 0
            blk = (v.get('blockstun') or 0) > 0 and not (pv.get('blockstun') or 0) > 0
            if not (hit or blk): continue
            m = re.match(r'ATK_([1-9][LMH][PK])', A.mname(names, side, fr[k][side].get('action_id')) or '')
            if m and fr[k][side].get('posX') is not None and v.get('posX') is not None:
                vs_move = hit and pv.get('act_st_name') in ('ATCK', 'THROW')   # hit them out of an attack: their limb was out, as in a whiff punish
                out.append((ch, m.group(1), abs(fr[k][side]['posX'] - v['posX']), vs_move))
    return out


def main(rep):
    by = C.defaultdict(list); bym = C.defaultdict(list)
    files = sorted(glob.glob(os.path.join(rep, '*.json.gz')) + glob.glob(os.path.join(rep, '*.json')))
    for i, p in enumerate(files, 1):
        try:
            for ch, b, dx, vm in contacts(p):
                by[(ch, b)].append(dx)
                if vm: bym[(ch, b)].append(dx)
        except Exception as e:
            print('skip', os.path.basename(p), e)
        if i % 100 == 0: print(i, 'of', len(files))
    q = lambda v: [round(v[min(len(v) - 1, int(0.9 * len(v)))], 2), round(v[-1], 2), len(v)]
    chars = C.defaultdict(dict); charm = C.defaultdict(dict)
    for (ch, b), v in by.items(): v.sort(); chars[ch][b] = q(v)
    for (ch, b), v in bym.items(): v.sort(); charm[ch][b] = q(v)
    for ch, r in chars.items():
        p = os.path.join(FD_DIR, ch + '.json')
        if not os.path.exists(p): print('no frame data file for', ch); continue
        d = json.load(open(p, encoding='utf-8'))
        d['reach'] = dict(sorted(r.items()))
        d['reach_vs_move'] = dict(sorted(charm.get(ch, {}).items()))
        d['reach_note'] = ('reach: posX distance (centre to centre) when the normal made contact (hit or block), '
                           '[90th percentile, max, contacts], measured by whiff_reach.py from %d captures. reach_vs_move: the same, only hits on an '
                           'opponent who was attacking (their limb out, as when whiff punishing)' % len(files))
        json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('reach stored for', len(chars), 'characters')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'replays')
