"""Player rank labels from a capture's LP and MR (Sean, 2026-11-18):
- below Master: the league name only ("Diamond", not "Diamond 3");
- Master with an MR: "<MR> MR";  Master without one: "MR unknown";
- no LP in the capture (older capture scripts): fall back to the MR if there is one, else None.
LP thresholds (league starts): Rookie 0, Iron 1,000, Bronze 3,000, Silver 5,000, Gold 9,000, Platinum 13,000, Diamond 19,000, Master 25,000.
LP -1 = no rank yet (shown in game as "New Challenger")."""
LEAGUES = [(25000, 'Master'), (19000, 'Diamond'), (13000, 'Platinum'), (9000, 'Gold'), (5000, 'Silver'), (3000, 'Bronze'), (1000, 'Iron'), (0, 'Rookie')]


def league(lp):
    if lp is None: return None
    if lp < 0: return 'Unranked'
    return next(name for start, name in LEAGUES if lp >= start)


def label(lp, mr):
    lg = league(lp)
    if lg is None: return f'{mr} MR' if mr else None
    if lg == 'Master': return f'{mr} MR' if mr else 'MR unknown'
    return lg


if __name__ == '__main__':
    for lp, mr in [(395464, 1751), (30000, 0), (22266, 0), (20120, 0), (-1, 0), (None, 1704), (None, None), (12999, 0), (13000, 0)]:
        print(lp, mr, '->', label(lp, mr))
