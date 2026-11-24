"""Per-character baselines for sf6-character-notes: how often each character jumps, Drive Rushes, parries and throws.

  python character_baselines.py DB [--include-player] [--min-rounds 9]

Rates are per round over every game-side of that character in sf6.db, leaving out the configured player (settings
'me', else shotokan.json) so a character the player mains isn't described by the player's own habits. Prints the
markdown table used in the skill. Throw presses include throw techs and whiffed throws.
"""
import collections as C, os, sqlite3, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spectra_calibrate as CAL

COLS = [('Forward jumps', 'BAS_JUMP_F_START'), ('Neutral jumps', 'BAS_JUMP_N_START'), ('Back jumps', 'BAS_JUMP_B_START'),
        ('Drive Rush', 'Drive Rush'), ('Drive Impact', 'Drive Impact'), ('Drive Parry', 'Drive Parry'), ('Throw presses', 'Throw')]


def table(db, include_player=False, min_rounds=9):
    con = sqlite3.connect(db)
    me = None if include_player else CAL.me_id(con)
    rounds, players, counts = C.Counter(), C.defaultdict(set), C.defaultdict(C.Counter)
    side = {}
    for rid, p1, p2, c1, c2, rs in con.execute('select replay_id, p1_player_id, p2_player_id, p1_char, p2_char, round_score from games'):
        try: r = sum(int(x) for x in str(rs).split('-'))
        except Exception: continue
        for pid, ch in ((p1, c1), (p2, c2)):
            if pid == me or not ch: continue
            rounds[ch] += r; players[ch].add(pid); side[(rid, pid)] = ch
    for rid, pid, move, n in con.execute('select replay_id, player_id, move, n from usage'):
        ch = side.get((rid, pid))
        if not ch: continue
        for label, key in COLS:
            if move == key or (key == 'Throw' and move.startswith('Throw')):
                counts[ch][label] += n
    rows = sorted((ch for ch in rounds if rounds[ch] >= min_rounds), key=lambda c: -rounds[c])
    out = ['| Character | Rounds | Players | ' + ' | '.join(l for l, _ in COLS) + ' |', '|' + '---|' * (3 + len(COLS))]
    for ch in rows:
        out.append(f'| {ch} | {rounds[ch]} | {len(players[ch])} | ' + ' | '.join(f'{counts[ch][l] / rounds[ch]:.2f}' for l, _ in COLS) + ' |')
    small = sorted(ch for ch in rounds if rounds[ch] < min_rounds)
    return '\n'.join(out), small, me


if __name__ == '__main__':
    mr = int(sys.argv[sys.argv.index('--min-rounds') + 1]) if '--min-rounds' in sys.argv else 9
    t, small, me = table(sys.argv[1], '--include-player' in sys.argv, mr)
    print(t)
    print(f'\nFewer than {mr} rounds: {", ".join(small)}' + ('' if me is None else '\n(configured player left out)'))
