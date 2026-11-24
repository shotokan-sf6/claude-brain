"""Decision presses in detail: where players press, with which buttons, and what it leads to.

A decision press is a new button, special, super or throw while the opponent isn't being hit, knocked down or
getting up (the same count as the `decision_presses` stat). For each one, analyze_capture.py records the situation
(from the 20 frames before), the move, what the opponent was doing, and the first outcome within about 70 frames
(hit / counter hit / blocked / parried / whiffed / got hit / whiff punished).

  python decision_presses.py DB --player Coosco   (your own names from shotokan.json are added first unless --no-me) [--char Cammy] [--replays DIR] [--out decisions.json]

--player takes a name, or several names of one player separated by commas (the first is the label).
Prints, per player, presses per round by situation, outcome rates per situation and the top moves per situation.
Throw presses on wake-up or after blocking are defensive, so the summary calls them throw techs.
Captures are found by the file name in games.capture_file (.json or .json.gz), in --replays DIR first, then the capture
folders from paths.py (SHOTOKAN_REPLAYS, SHOTOKAN_CAPTURE_DIRS). DB defaults to SHOTOKAN_DB.
"""
import argparse, collections as C, json, os, sqlite3, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_capture as A, paths

GOOD = ('clean hit', 'counter hit', 'punish counter', 'throw', 'reversal')
CTX = ['neutral close', 'neutral mid', 'neutral far', 'after blocking', 'wake-up', 'own pressure', 'oki', 'after a hit', 'vs a jump', 'air button']


def find_capture(cf, rdir):
    return paths.find_capture(cf, extra=(rdir,))


def collect(db, players, char, rdir):
    c = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    out = []
    for spec in players:
        name = spec.split(',')[0]; ids = []
        for nm in spec.split(','):
            ids += [r[0] for r in c.execute("select player_id from players where name = ? union select player_id from player_names where name = ?", (nm, nm))]
        if not ids: print('no player', name, file=sys.stderr); continue
        q = ','.join('?' * len(ids))
        for sk, rid, p1, c1, c2, cf, gn in c.execute(f"select set_key, replay_id, p1_player_id, p1_char, p2_char, capture_file, game_no from games "
                                                      f"where (p1_player_id in ({q}) or p2_player_id in ({q})) and capture_file is not null", ids + ids).fetchall():
            side = 'p1' if p1 in ids else 'p2'
            if char and (c1 if side == 'p1' else c2) != char: continue
            path = find_capture(cf, rdir)
            if not path: print('missing capture', cf, file=sys.stderr); continue
            try:
                d = A.analyze(path, gn, name)
            except Exception as e:
                print('skipped', rid, repr(e), file=sys.stderr); continue
            for x in d['decisions']:
                if x['side'] == side: x.update(who=name, set_key=sk); out.append(x)
    return out


def summary(D, players):
    rounds = {w: len({(x['game_id'], x['round']) for x in D if x['who'] == w}) or 1 for w in players}
    for x in D:
        if x['move'] == 'Throw attempt' and x['ctx'] in ('wake-up', 'after blocking'): x['move'] = 'Throw tech'
    head = ''.join(f'{w[:12]:>14s}' for w in players)
    print('rounds', rounds)
    print(f"\nPresses per round{'':5s}{head}")
    cnt = {w: C.Counter(x['ctx'] for x in D if x['who'] == w) for w in players}
    for k in CTX + ['ALL']:
        print(f"  {k:20s}" + ''.join(f"{(sum(cnt[w].values()) if k == 'ALL' else cnt[w][k]) / rounds[w]:14.2f}" for w in players))
    for k in CTX + ['ALL']:
        print(f"\n## {k}")
        for w in players:
            xs = [x for x in D if x['who'] == w and (k == 'ALL' or x['ctx'] == k)]
            if not xs: continue
            n = len(xs); o = C.Counter(x['outcome'] for x in xs)
            bad = sum(v for kk, v in o.items() if kk.startswith('got') or kk == 'whiff punished')
            print(f"  {w[:15]:15s} landed {sum(o[g] for g in GOOD) / n:.0%}  blocked {o['blocked'] / n:.0%}  whiffed {o['whiffed / nothing'] / n:.0%}  "
                  f"parried {o['parried'] / n:.0%}  got hit {bad / n:.0%}  net damage/press {sum(x['damage'] for x in xs) / n:+.0f}")
            mc = C.Counter(x['move'] for x in xs)
            parts = []
            for m, kk in mc.most_common(6):
                ys = [x for x in xs if x['move'] == m]
                g = sum(x['outcome'] in GOOD for x in ys); b = sum(x['outcome'].startswith('got') or x['outcome'] == 'whiff punished' for x in ys)
                parts.append(f"{m} {kk / n:.0%} ({g / len(ys):.0%} landed, {b / len(ys):.0%} got hit)")
            print('    ' + '; '.join(parts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('db', nargs='?', default=paths.DB); ap.add_argument('--player', action='append', default=[])
    ap.add_argument('--no-me', action='store_true', help="don't add the player from shotokan.json")
    ap.add_argument('--char'); ap.add_argument('--replays'); ap.add_argument('--out')
    a = ap.parse_args()
    if not a.no_me and paths.PLAYER_NAMES and not any(paths.PLAYER in p.split(',') for p in a.player):
        a.player.insert(0, ','.join(paths.PLAYER_NAMES))
    if not a.player: ap.error('no players: pass --player NAME or set player_name in shotokan.json')
    D = collect(a.db, a.player, a.char, a.replays)
    if a.out: json.dump(D, open(a.out, 'w'))
    summary(D, [p.split(',')[0] for p in a.player])


if __name__ == '__main__':
    main()
