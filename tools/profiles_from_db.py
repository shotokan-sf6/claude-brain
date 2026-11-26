"""Build player profiles from the history database, using only the data a Quick review stores.

  python profiles_from_db.py DB OUT.json [--levels Quick] [--players name,name] [--me NAME]   (default: the player in shotokan.json)

For each player in sets of the chosen review levels, it combines across those sets:
  - archetype reads (most common call; confidence grows with the number of sets that agree)
  - the eight spectra (mean score per axis, labelled on the same 1-5 percentile scale)
  - per-game stats (throws, techs, anti-airs, counter hits, burnouts, raw Drive Rushes,
    what they do after blocking and on wake-up, where their damage taken came from)
  - their most frequent Strength and Leak habits
  - how to beat them: the review's counter notes plus rules keyed to their extreme spectra
Every sentence is built from those numbers; nothing is hand-written per player.
"""
import sqlite3, json, os, sys, collections, statistics, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

ENDS = {'Temperament (defense)': ('Impulsive', 'Mindful'), 'Temperament (offense)': ('Impulsive', 'Mindful'),
        'Adaptability': ('Inelastic', 'Elastic'), 'Risk tolerance': ('Low', 'High'), 'Initiative': ('Reactive', 'Proactive'),
        'Composure': ('Steady', 'Tilts'), 'Variety': ('Scripted', 'Mixed'), 'Resource use': ('Conservative', 'Spendthrift')}
AXES = list(ENDS)

def label(axis, s):
    l, r = ENDS[axis]
    return {1: f'Very {l.lower()}', 2: f'Leans {l.lower()}', 3: 'Middle', 4: f'Leans {r.lower()}', 5: f'Very {r.lower()}'}[s]

# advice keyed to an extreme score (axis, score) -> how to beat it
RULES = {
    ('Temperament (defense)', 1): 'they act on reversal timing after blocking and on wake-up: frame trap and meaty them, and block-then-punish their reversal',
    ('Temperament (defense)', 2): 'their first action after blocking is often on reversal timing: short-gap frame traps catch it',
    ('Temperament (defense)', 4): 'they wait and block: throw them, and take their Drive with plus strings',
    ('Temperament (defense)', 5): 'they almost never press on defense: walk up and throw, and shimmy only after they tech',
    ('Temperament (offense)', 1): 'they press again straight after a blocked attack: block, then hit the gap with your fastest button or perfect parry',
    ('Temperament (offense)', 5): 'their offense waits after a blocked attack: take your turn back with a fast button or walk-up throw',
    ('Adaptability', 1): 'they keep doing what you have already punished: punish it the same way again',
    ('Adaptability', 2): 'they are slow to drop what gets punished: repeat what worked until they change',
    ('Adaptability', 5): 'they adjust between games: show a new option each game rather than repeating the one that worked',
    ('Risk tolerance', 5): 'they gamble (reversals, Drive Impact, raw Drive Rush, jumps): block, bait and punish the gambles',
    ('Risk tolerance', 1): 'they take few risks: open them up with throws and Drive pressure, not big reads',
    ('Risk tolerance', 4): 'they take more risks than most: block first and punish the reversal, Drive Impact or jump',
    ('Initiative', 4): 'they walk forward a lot: stand at your poke range and whiff-punish or counter-poke the walk-in',
    ('Initiative', 1): 'they wait for you: walk them to the corner in small steps instead of pressing into their pokes',
    ('Initiative', 5): 'they come forward: hold your space with pokes and anti-airs and whiff-punish their approach',
    ('Composure', 5): 'they press more after a big hit or a lost round: stay patient and block right after you land damage',
    ('Composure', 4): 'they get busier after taking damage: block first after you land a big combo',
    ('Variety', 1): 'their after-block and wake-up choices are scripted: read the default and hard-punish it',
    ('Variety', 2): 'they lean on one or two defensive defaults: find them early and call them out',
    ('Resource use', 5): 'they spend Drive freely: block their pressure, make them spend, and corner them when they burn out',
    ('Resource use', 1): 'they sit on Drive and super: respect their reversal and parry, and don\'t gamble into full meter',
}

LENS_SHORT = {'Challenging pressure': 'challenging pressure', 'Challenging okizeme': 'challenging okizeme', 'Counter-hit at mid range': 'getting counter-hit at mid range', 'Whiff punished': 'getting whiff punished',
              'Pressed in their pressure / on wake-up': 'pressing in pressure or on wake-up', 'Pressed at mid range': 'pressing at mid range',
              'Walked in': 'walking in', 'Teched a throw': 'teching throws', 'Blocking, opened up': 'getting opened up while blocking',
              'Jumped': 'jumping', 'Jumped in on (no anti-air)': 'being jumped in on', 'Own offense beaten by a reversal': 'their offense beaten by a reversal',
              'Drive Rush / Impact checked': 'Drive Rush / Impact getting checked', 'Unsafe move punished': 'unsafe moves punished', 'Pressed after turn ended': 'pressing again after their turn started', 'Unclear / super': 'supers or unclear'}

MOVE_NAMES = {'SOMERSAULT_Start': 'Flash Kick', 'SONICBOOM': 'Sonic Boom', 'Akidako_Ganzigarame': 'Entrapment (Sinister Slide grab)'}
SKIP_PATTERNS = ('first action after blocking',)

def clean(h):
    for k, v in MOVE_NAMES.items(): h = h.replace(k, v)
    return h

def main(db, out, levels=('Quick',), only=None, me=None):
    me = paths.require_player(me)
    c = sqlite3.connect(db); c.row_factory = sqlite3.Row
    name = {r['player_id']: r['name'] for r in c.execute('select player_id, name from players')}
    q = 'select * from sets where review in (%s)' % ','.join('?' * len(levels))
    sets = list(c.execute(q, levels))
    by = collections.defaultdict(list)            # player_id -> [(set row, side, char, opp_id)]
    for s in sets:
        by[s['focus_player_id']].append((s, 'focus', s['focus_char'], s['opp_player_id']))
        by[s['opp_player_id']].append((s, 'opp', s['opp_char'], s['focus_player_id']))
    rows = []
    for pid, items in by.items():
        if only and name[pid] not in only: continue
        keys = [s['set_key'] for s, *_ in items]
        ph = ','.join('?' * len(keys))
        chars = collections.Counter(ch for _, _, ch, _ in items)
        won = sum(1 for s, *_ in items if s['winner_player_id'] == pid)
        g_w = sum(s['focus_games'] if side == 'focus' else s['opp_games'] for s, side, *_ in items)
        g_l = sum(s['opp_games'] if side == 'focus' else s['focus_games'] for s, side, *_ in items)
        # stats summed over sets, then per game
        st = collections.defaultdict(float); games = 0
        for r in c.execute(f'select set_key, metric, value from set_stats where player_id=? and set_key in ({ph})', [pid, *keys]):
            if r['metric'] == 'games': games += r['value']
            elif not r['metric'].startswith('taken_'): st[r['metric']] += r['value']
        share = collections.defaultdict(list)
        for r in c.execute(f"select metric, value from set_stats where player_id=? and set_key in ({ph}) and metric like 'taken_share:%'", [pid, *keys]):
            share[r['metric'].split(': ', 1)[1]].append(r['value'])
        games = games or (g_w + g_l) or 1
        pg = lambda m: round(st.get(m, 0) / games, 1)
        pct = lambda a, n: round(100 * st.get(a, 0) / st[n]) if st.get(n) else None
        # spectra
        sp = collections.defaultdict(list); ev = collections.defaultdict(list)
        for r in c.execute(f'select axis, score, evidence from spectra where player_id=? and set_key in ({ph})', [pid, *keys]):
            if r['score']: sp[r['axis']].append(r['score']); ev[r['axis']].append(r['evidence'])
        spectra = []
        for a in AXES:
            if not sp[a]:
                spectra.append(dict(axis=a, left=ENDS[a][0], right=ENDS[a][1], score=None, label=None, evidence='not enough data')); continue
            m = statistics.mean(sp[a]); s = int(round(m))
            e = ev[a][-1] if len(sp[a]) == 1 else f'mean {m:.1f} over {len(sp[a])} sets (range {min(sp[a])}-{max(sp[a])}); latest: {ev[a][-1]}'
            spectra.append(dict(axis=a, left=ENDS[a][0], right=ENDS[a][1], score=s, label=label(a, s), evidence=e))
        # archetype
        reads = list(c.execute(f'select * from reads where player_id=? and set_key in ({ph})', [pid, *keys]))
        arch = collections.Counter(r['archetype'] for r in reads)
        top_arch, n_arch = arch.most_common(1)[0] if arch else ('Unknown', 0)
        lean = next((r['lean'] for r in reversed(reads) if r['archetype'] == top_arch and r['lean']), '')
        conf = 'Low' if len(items) == 1 else 'High' if n_arch / len(items) >= 0.75 and len(items) >= 4 else 'Medium'
        arch_txt = f'{top_arch} ({n_arch} of {len(items)} sets)' if len(items) > 1 else top_arch
        if len(arch) > 1: arch_txt += '; also ' + ', '.join(f'{a} ({n})' for a, n in arch.most_common()[1:])
        # habits
        hab = collections.defaultdict(lambda: [0, 0, ''])
        for r in c.execute(f'select kind, habit, times from habits where player_id=? and set_key in ({ph})', [pid, *keys]):
            if any(p in r['habit'] for p in SKIP_PATTERNS): continue
            k = (r['kind'], clean(r['habit'])); hab[k][0] += 1; hab[k][1] += r['times'] or 0
        def top(kind, n=4):
            xs = sorted(((v[0], v[1], h) for (k, h), v in hab.items() if k == kind), reverse=True)[:n]
            return '; '.join(h + ((f' ({t}×' + (f' in {s} sets' if s > 1 else '') + ')') if t and '×' not in h else (f' (in {s} sets)' if s > 1 else '')) for s, t, h in xs)
        ab = pct('after_block_attack', 'after_block_n'); wu = pct('wake_up_attack', 'wake_up_n')
        # where damage taken came from
        sh = sorted(((statistics.mean(v), k) for k, v in share.items() if k != 'Unclear / super'), reverse=True)
        taken = ', '.join(f'{LENS_SHORT.get(k, k)} {round(100 * v)}%' for v, k in sh[:3]); taken_lbl = 'Most damage taken came from '
        if not taken:
            sit = collections.defaultdict(list)
            for r in c.execute(f"select metric, value from set_stats where player_id=? and set_key in ({ph}) and metric like 'taken_situation_share:%'", [pid, *keys]):
                sit[r['metric'].split(': ', 1)[1]].append(r['value'])
            ss = sorted(((statistics.mean(v), k) for k, v in sit.items()), reverse=True)
            taken = ', '.join(f'{k} {round(100 * v)}%' for v, k in ss[:3]); taken_lbl = 'Damage taken by situation: '
        # what their opponents did to them (per game): the opponent's counter hits, anti-airs and throws are this player's leaks
        os_ = collections.defaultdict(float)
        for s_, side, ch, o in items:
            for r in c.execute('select metric, value from set_stats where player_id=? and set_key=?', [o, s_['set_key']]):
                os_[r['metric']] += r['value'] if r['metric'] != 'games' else 0
        opg = lambda m: round(os_.get(m, 0) / games, 1)
        derived = []
        if opg('counter_hits') + opg('punish_counters') >= 5: derived.append(f"got counter-hit {round(opg('counter_hits') + opg('punish_counters'), 1)}× a game (pressing into the opponent's buttons)")
        if opg('anti_airs') >= 1.5: derived.append(f"anti-aired {opg('anti_airs')}× a game")
        if opg('throws') >= 1.5 and pg('throw_techs') < opg('throws') / 2: derived.append(f"thrown {opg('throws')}× a game, teching {pg('throw_techs')}")
        if pg('burnouts') >= 0.5 and not any(h.startswith('Burn') for (k, h) in hab if k == 'Leak'): derived.append(f"burned out {pg('burnouts')}× a game")
        if (ab or 0) >= 40: derived.append(f'attacks first after blocking {ab}% of the time')
        # summary
        extremes = [x for x in spectra if x['score'] in (1, 5)]
        opp_names = sorted({name[o] for *_, o in items})
        vs = f"vs {', '.join(opp_names)}" if len(opp_names) <= 3 else f'vs {len(opp_names)} opponents'
        summ = (f"{top_arch} {chars.most_common(1)[0][0]} player"
                f"{' (' + lean + ')' if lean and not any(ch.isdigit() for ch in lean) else ''}. Played {vs.replace('vs ', '')}. "
                f"Per game: {pg('throws')} throws, {pg('throw_techs')} throw techs, {pg('anti_airs')} anti-airs, {pg('counter_hits')} counter hits, "
                f"{pg('raw_drive_rush')} raw Drive Rushes, {pg('burnouts')} burnouts. ")
        if ab is not None: summ += f'Attacks first after blocking {ab}% of the time' + (f' and on wake-up {wu}%' if wu is not None else '') + '. '
        if taken: summ += f'{taken_lbl}{taken}. '
        if extremes: summ += 'Stands out on: ' + ', '.join(f"{x['axis']} ({x['label'].lower()})" for x in extremes) + '.'
        # how to beat
        tips = [RULES[(x['axis'], x['score'])] for x in spectra if (x['axis'], x['score']) in RULES]
        notes = []
        for r in reads:
            n = (r['counter_note'] or '').strip()
            for pre in ('How to beat this: ', 'What costs you in this set: '):
                if n.startswith(pre): n = n[len(pre):]
            for frag in [f.strip().rstrip('.') for f in re.split(r'[;,]\s(?![^()]*\))', n)]:
                if frag and frag not in notes: notes.append(frag)
        beat = ' '.join(t[0].upper() + t[1:] + '.' for t in tips[:4])
        if notes:
            mine = all((r['counter_note'] or '').startswith('What costs you') for r in reads if r['counter_note'])
            what = 'What cost them' if mine else ('From the reviews' if len(reads) > 1 else 'From the review')
            beat += (' ' if beat else '') + what + ': ' + '; '.join(notes[:5]) + '.'
        mr = [s['focus_mr_start'] for s, side, *_ in items if side == 'focus' and s['focus_mr_start']]
        rank = (f'Master, {round(statistics.mean(mr)):,} MR on average' if mr else 'MR unknown')
        rows.append(dict(player=name[pid], character=' / '.join(f'{ch}' + (f' ({n})' if len(chars) > 1 else '') for ch, n in chars.most_common()),
                         sets=len(items), record=f'{won}-{len(items) - won}', games=f'{int(g_w)}-{int(g_l)}', rank=rank,
                         basis=f"{len(items)} {'/'.join(levels)}-review set{'s' if len(items) > 1 else ''} ({int(games)} games)",
                         archetype=arch_txt, confidence=conf, summary=summ.strip(), strengths=top('Strength') or '—', leaks='; '.join(x for x in [top('Leak'), '; '.join(derived)] if x) or '—',
                         patterns=top('Pattern', 3) or '—', how_to_beat=beat or '—', spectra=spectra,
                         per_game=dict(throws=pg('throws'), throw_techs=pg('throw_techs'), anti_airs=pg('anti_airs'), counter_hits=pg('counter_hits'),
                                       punish_counters=pg('punish_counters'), raw_drive_rush=pg('raw_drive_rush'), burnouts=pg('burnouts'),
                                       after_block_attack_pct=ab, wake_up_attack_pct=wu)))
    rows.sort(key=lambda r: (r['player'] != me, -r['sets'], r['player'].lower()))
    for i, r in enumerate(rows, 1): r['order'] = i; r['profile_id'] = 'P%02d' % i
    json.dump(rows, open(out, 'w'), indent=1, ensure_ascii=False)
    print(len(rows), 'profiles ->', out)

if __name__ == '__main__':
    a = sys.argv; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    main(a[1], a[2], tuple(opt('--levels', 'Quick').split(',')), opt('--players') and opt('--players').split(','), opt('--me', None))
