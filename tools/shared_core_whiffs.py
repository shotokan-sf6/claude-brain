"""Whiff-punish windows for shared_core_analyze.py: every ground normal or throw that whiffed, how long its user was stuck
in recovery, how far apart the players were, and whether the other player punished it.

A move whiffed when the other player never went into hitstun, blockstun, a Drive Parry or guard while it was out, and it
ran to the end of its committed frames (margin_frame), or was cut short by getting hit. Its recovery window starts after
its last active frame (wiki startup + active, frame_data/<char>.json "frames") and lasts until margin_frame.

Each window is classed for the player who could punish it:
  punished      they hit the whiffer during the window (any window, any range)
  missed        a chance they didn't take: window >= MIN_WINDOW frames, they were free (walking, standing, crouching,
                dashing) when recovery started, and one of their ground normals reaches that far with startup no longer
                than the window, but no hit came
  pressed       the same kind of chance, they pressed something, and it didn't connect
  no chance     with a reason: 'short window' (under MIN_WINDOW: lights and fast mediums can't be whiff punished on
                reaction; a punish there comes from a spacing trap), 'edge of reach' (in reach only with a short step
                forward, EDGE), 'out of reach', 'busy' (in their own move, hit, jumping, getting up), 'no reach data'
Reach is frame_data "reach_vs_move" (whiff_reach.py): the 90th percentile distance, centre to centre, at which the button
hit an opponent who was attacking (limb out, as in a whiff punish); "reach" (all contacts) when that has under 5 hits.
It is approximate ("likely").
"""
import re

EDGE = 0.3            # about 6 frames of walking forward (Mai walks 0.05 a frame)
MIN_WINDOW = 15       # frames: a whiffed button recovering faster than this is not a reaction whiff punish (2026-11-27)
FREE = {'FOOTWORK', 'WALK', 'DASH', 'STAND', 'SIT', 'SITD', 'STAND_TURN', 'SIT_TURN', 'DUCK_WALK'}
CONTACT = ('DAMAGE', 'DEF', 'GUARD', 'PARRY', 'HOLD')
ACT = ('ATCK', 'SPECIAL', 'SUPER', 'THROW', 'CATCH')


def move_key(name):
    """Wiki input for a capture move name: ATK_2MK -> 2MK, ATK_5HP_... -> 5HP, NGS_* (a throw) -> LPLK; else None."""
    if not name: return None
    m = re.match(r'ATK_([1-9][LMH][PK])', name)
    if m: return m.group(1)
    return 'LPLK' if name.startswith('NGS') else None


def reach_of(fd, b):
    """A button's whiff-punish reach: reach_vs_move p90 (5+ hits), else all-contacts p90 (3+), else None."""
    vm, al = (fd.get('reach_vs_move') or {}).get(b), (fd.get('reach') or {}).get(b)
    return vm[0] if vm and vm[2] >= 5 else al[0] if al and al[2] >= 3 else None


def best_button(fd, dx, window, edge=False):
    """The fastest of the punisher's ground normals that reaches dx and starts within the window: (input, startup) or None.
    edge=True allows a short step forward (EDGE)."""
    fr = fd.get('frames') or {}
    ok = [(fr[b][0], b) for b in fr if b != 'LPLK' and reach_of(fd, b) is not None and reach_of(fd, b) + (EDGE if edge else 0) >= dx and fr[b][0] <= window]
    return (min(ok)[1], min(ok)[0]) if ok else None


def whiff_windows(fr, names, side_name, side_char, other, frame_data, mname, pretty, rid):
    out = []
    for w in ('p1', 'p2'):
        p = other[w]; fdw, fdp = frame_data(side_char[w]), frame_data(side_char[p])
        frames = fdw.get('frames') or {}
        i = 0
        while i < len(fr):
            f = fr[i]
            if f.get('fight_st') != 4: i += 1; continue
            aid = f[w].get('action_id'); key = move_key(mname(names, w, aid))
            if key not in frames or (i and fr[i - 1][w].get('action_id') == aid and fr[i - 1]['round'] == f['round']):
                i += 1; continue
            j = i
            while j + 1 < len(fr) and fr[j + 1][w].get('action_id') == aid and fr[j + 1]['round'] == f['round']: j += 1
            S, Ac = frames[key][0], frames[key][1]
            margin = f[w].get('margin_frame') or (j - i + 1)
            rec0 = S + Ac - 1                     # action frame where recovery starts (0-based)
            win = margin - rec0
            seg = fr[i:j + 1]
            contact = any((x[p].get('hitstun') or 0) > 0 or (x[p].get('blockstun') or 0) > 0 or x[p].get('act_st_name') in CONTACT for x in seg)
            cut_by_hit = j + 1 < len(fr) and fr[j + 1][w].get('act_st_name') == 'DAMAGE'
            ws = i + rec0
            if contact or win <= 0 or ws >= len(fr) or not ((j - i + 1) >= margin - 1 or cut_by_hit):
                i = j + 1; continue
            x0 = fr[ws]; dx = abs((x0[w].get('posX') or 0) - (x0[p].get('posX') or 0))
            pst = x0[p].get('act_st_name'); free = pst in FREE
            hit = tried = None
            for x in range(ws, min(len(fr), i + margin + 2)):
                if fr[x][w].get('act_st_name') == 'DAMAGE' and fr[x - 1][w].get('act_st_name') != 'DAMAGE':
                    hit = mname(names, p, fr[x][p].get('action_id')) or mname(names, p, fr[x - 1][p].get('action_id')); break
                if tried is None and fr[x][p].get('act_st_name') in ACT: tried = mname(names, p, fr[x][p].get('action_id'))
            best = best_button(fdp, dx, win)
            chance = win >= MIN_WINDOW and free and best is not None
            if hit: res = 'punished'
            elif chance: res = 'pressed' if tried else 'missed'
            else:
                res = 'no chance'
            why = None
            if not hit and not chance:
                why = ('short window' if win < MIN_WINDOW else 'busy' if not free else
                       'no reach data' if not fdp.get('reach') else 'edge of reach' if best_button(fdp, dx, win, edge=True) else 'out of reach')
                if why == 'edge of reach': best = best_button(fdp, dx, win, edge=True)
            out.append(dict(game_id=rid, round=f['round'] + 1, round_timer=f['round_timer'], whiffer=side_name[w], punisher=side_name[p],
                            move=key, window=win, distance=round(dx, 2), punisher_state=pst, result=res, why=why,
                            punish=pretty(hit, side_char[p]) if hit else None, pressed=pretty(tried, side_char[p]) if (tried and not hit) else None,
                            best=best[0] if best else None, best_startup=best[1] if best else None, chance=bool(chance or hit)))
            i = j + 1
    return out
