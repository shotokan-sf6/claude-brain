import json,glob,collections,re,statistics as S,sys
def cls(n):
    if not n: return '?'
    if n.startswith('ATK_CTA_4'): return 'Drive Reversal'
    if n.startswith('ATK_CTA'): return 'Drive Impact'
    if n.startswith(('SA','CA')): return 'super'
    if n.startswith('SP'): return 'OD special' if '_EX' in n else 'special'
    if n.startswith('NG'): return 'throw'
    m=re.match(r'ATK_(?:TC_)?\d?(\d)([LMH])',n) or re.match(r'ATK_.*?([LMH])[PK]',n)
    if m: return {'L':'light','M':'medium','H':'heavy'}[m.groups()[-1]]+(' (jump)' if n.startswith('ATK_8') else '')
    return 'other'
G=collections.defaultdict(list); B=collections.defaultdict(list); H=collections.defaultdict(list)
for f in sorted(glob.glob(sys.argv[1])):
    d=json.load(open(f)); F=d['frames']; MN=d['move_names']
    for i in range(1,len(F)-3):
        a,b=F[i-1],F[i]
        if a['round']!=b['round']: continue
        for p,o in (('p1','p2'),('p2','p1')):
            vb,vh=b[o]['blockstun']>a[o]['blockstun']+3, b[o]['hitstun']>a[o]['hitstun']+3
            if not (vb or vh) or b[p]['burnout'] or b[o]['burnout']: continue
            mv=MN.get(p,{}).get('%04d'%b[p]['action_id'])
            c=cls(mv); e=F[i+2]
            ga=e[p]['drive']-a[p]['drive']; gd=e[o]['drive']-a[o]['drive']
            ga-=120; gd-=60   # remove ~3 frames of passive regen
            G[(c,'block' if vb else 'hit')].append(ga)
            (B if vb else H)[c].append(gd)
def summ(v): v=sorted(v); return f"n={len(v):5} median={S.median(v):7.0f} p10={v[len(v)//10]:7.0f} p90={v[len(v)*9//10]:7.0f}"
print('ATTACKER GAIN on contact'); [print(f'  {k[0]:16} {k[1]:5}',summ(v)) for k,v in sorted(G.items()) if len(v)>=10]
print('BLOCKER LOSS'); [print(f'  {k:16}',summ(v)) for k,v in sorted(B.items()) if len(v)>=10]
print('VICTIM DRIVE CHANGE on hit'); [print(f'  {k:16}',summ(v)) for k,v in sorted(H.items()) if len(v)>=10]
