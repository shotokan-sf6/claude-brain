# Measure Drive gauge changes by situation across capture files: python3 drive_measure.py "replays/*.json"
import json,glob,collections,sys
R=collections.defaultdict(collections.Counter)
for f in sorted(glob.glob(sys.argv[1] if len(sys.argv)>1 else 'replays/*.json')):
    F=json.load(open(f))['frames']
    for a,b in zip(F,F[1:]):
        if a['round']!=b['round'] or b['fight_st']!=a['fight_st']: continue
        for p,o in (('p1','p2'),('p2','p1')):
            x,y=a[p],b[p]; dd=y['drive']-x['drive']
            if dd==0 or x['burnout'] or y['burnout']: continue
            s=y['act_st_name']; os_=b[o]['act_st_name']
            if s=='PARRY' or x['act_st_name']=='PARRY':
                k='parry '+('opp hitstop' if b[o]['hitstop']>0 or y['hitstop']>0 else 'plain')
            elif s=='DEF': k='blocking'
            elif s=='DAMAGE': k='getting hit'
            elif b[o]['act_st_name']=='DEF': k='attacking, opp blocking'
            elif b[o]['act_st_name']=='DAMAGE': k='attacking, opp hit'
            else: k='other:'+s
            R[(k,'+' if dd>0 else '-')][dd]+=1
for k in sorted(R):
    c=R[k]; n=sum(c.values())
    if n>30 or k[0].startswith(('parry','block','getting','attacking')): print(k,n,c.most_common(8))
