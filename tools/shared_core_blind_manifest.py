"""Pre-set facts for a blind prediction, with nothing that leaks the result.

  python shared_core_blind_manifest.py CAPTURE [CAPTURE ...] [--out manifest.json]

Prints, from the FIRST game's capture only: both players' names, CFN IDs, characters, control types, MR and LP
before the set, and the battle type. It withholds what gives results away: round results, every later game's
MR/LP (MR moves after each game), the number of games, and anything from the frames. Write the prediction from
this manifest and sf6.db history, save it (prediction.json with written_at), and only then run the analyzer.
Captures can be given in any order; the earliest is found by its timestamp, then by file time.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shared_core_analyze as A

KEEP = ('name', 'cfn_id', 'char', 'char_id', 'control', 'mr', 'lp')


def first_game(paths):
    def key(p):
        try:
            inf = A.load_capture(p)['info']
            for k in ('played_at', 'uploaded_at', 'date', 'time', 'timestamp'):
                if inf.get(k): return (0, str(inf[k]))
        except Exception:
            pass
        return (1, os.path.getmtime(p))
    return sorted(paths, key=key)[0]


def manifest(paths):
    inf = A.load_capture(first_game(paths))['info']
    out = {'battle_type': inf.get('battle_type'), 'players': []}
    for s in ('p1', 'p2'):
        out['players'].append({k: inf.get(f'{s}_{k}') for k in KEEP})
    ps = out['players']
    if len(ps) == 2 and all((x.get('mr') or 0) > 0 for x in ps):
        # MR at stake and win chances from the MR gap (shared_core_db.mr_odds: sfbuff's Elo, K=16). In sf6.db (117 ranked
        # sets, 2026-11-25) small gaps (FT2 odds under 0.6) played like coin flips and bigger gaps favoured the higher MR
        # more than the formula says (0.65 expected -> 0.84 won, 0.81 -> 0.93).
        from shared_core_db import mr_odds
        out['mr_odds'] = {x['name']: mr_odds(x['mr'], y['mr']) for x, y in ((ps[0], ps[1]), (ps[1], ps[0]))}
    out['withheld'] = 'round results, later games\' MR/LP, number of games, frame data'
    return out


if __name__ == '__main__':
    args = sys.argv[1:]
    out = None
    if '--out' in args:
        i = args.index('--out'); out = args[i + 1]; del args[i:i + 2]
    m = manifest(args)
    if out: json.dump(m, open(out, 'w'), indent=1)
    print(json.dumps(m, indent=1, ensure_ascii=False))
