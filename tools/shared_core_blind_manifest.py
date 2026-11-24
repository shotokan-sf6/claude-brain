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
