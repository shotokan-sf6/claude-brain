# usage: summary_md.py datadir out.md "Title" P1 P2
import sys,json,os
dd,out,title,P1,P2=sys.argv[1:6]
L=lambda n: json.load(open(f'{dd}/{n}.json')) if os.path.exists(f'{dd}/{n}.json') else []
o=[f'# {title}\n']
for s in L('sets'):
  hi,lo=max(s[k] for k in s if k.endswith('_games') and k!='games'),min(s[k] for k in s if k.endswith('_games') and k!='games')
  o.append(f"**{s['set_id']} ({s['format']}): {s['winner']} wins {hi}-{lo}.** Set score by game: {s['progression']}. Replays: {s['games']}.\n")
o.append('| Game | Replay | Winner | Rounds | Set score after |\n|---|---|---|---|---|')
for g in L('games'): o.append(f"| {g['game_no']} | {g['game_id']} | {g['winner']} | {g['round_score']} ({g['round_winners']}) | {g['set_score_after']} |")
st=L('story')
def item(r): 
  t=f"- **{(r['change']+': ') if r.get('change') else ''}{r['headline']}** ({r['polarity']}, {r['confidence']}). {r['detail']} _{r['evidence']} · {r['skills']}_"
  return t+(f"\n  - Try this: {r['try_this']}" if r.get('try_this') else '')
o.append('\n## Story of the Set\n')
for s in L('sets'):
  rows=[r for r in st if r['set_id']==s['set_id']]
  setr=[r for r in rows if r['scope']=='set']
  for t,p in (('Top highs','Worked well'),('Top lows','To improve')):
    o.append(f'### {t}'); [o.append(item(r)) for r in sorted([r for r in setr if r['polarity']==p and r['confidence']!='Low'],key=lambda r:(r['confidence']!='High',r['rank']))[:3]]
  o.append('### Other set findings'); [o.append(item(r)) for r in sorted(setr,key=lambda r:r['rank']) if r not in []]
  for g in sorted([g for g in L('story_games') if g['set_id']==s['set_id']],key=lambda g:g['game_no']):
    o.append(f"\n### Game {g['game_no']} · {g['game_id']} · {g['result']} · set {g['set_score_after']}\n{g['summary']}\n\nTurning point: {g['turning_point']}\n")
    [o.append(item(r)) for r in sorted([r for r in rows if r['scope']==g['game_id']],key=lambda r:r['rank'])]
o.append('\n## Habits')
for p in (P1,P2):
  o.append(f'\n### {p}')
  for h in L('habits'):
    if h['player']==p: o.append(f"- **{h['kind']} · {h['area']}: {h['habit']}** Seen: {h['seen']}. {h['fix']} _(confidence {h['confidence']})_")
o.append('\n## Punishes\n| Punisher | What | Example | Punish | Damage | Verdict |\n|---|---|---|---|---|---|')
for r in L('punish'): o.append(f"| {r['punisher']} | {r['what_was_punished']} | {r['example']} | {r['punish_used']} | {r['damage']} | {r['verdict']} |")
o.append('\n## Player reads')
for a in L('archetypes'): o.append(f"- **{a['player']} ({a['character']})**: {a['archetype']} ({a['lean']}), confidence {a['confidence']}. Risk tolerance: {a['doc_risk_tolerance']}. Temperament: {a['doc_temperament']}. Evidence: {a['evidence']}. How to beat this: {a['counter_note']}")
o.append('\n## Fixes and drills')
for f in sorted(L('fixes'),key=lambda f:(f['player']!=P1,f['rank'])): o.append(f"{f['rank']}. **{f['player']}: {f['fix']}** Drill: {f['drill']} Why: {f['why']}")
o.append(f'\n## Suggested training routine for {P1}')
for t in L('training'): o.append(f"- **{t['block']} ({t['minutes']} min): {t['focus']}.** {t['drills']}")
o.append('\n## Findings by skill')
for f in L('findings'): o.append(f"- **{f['skill']}** ({f.get('category','')}, {f['applies_to']}, {f['confidence']}): {f['finding']} _{f['evidence']}_")
open(out,'w').write('\n'.join(o)+'\n'); print(out)
