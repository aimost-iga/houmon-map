import json,re,collections,sys
B=json.load(open('app/buildings.json'))['buildings']
order=json.load(open('ga_order.json'))
FP=json.load(open('fp.json'))
PLl=open('pl_raw.txt').read().split('\n'); assert len(PLl)==8013
PL={bid:([] if l in('-','E','') else [list(map(float,c.split(','))) for c in l.split(';')]) for bid,l in zip(order,PLl)}
def fl(r):
    m=re.match(r'^(\d{1,2})(\d{2})$',r); return int(m.group(1)) if m else None
K=0.62
def est(b):
    t=b['t'] or 0
    fs=[fl(r) for r in b['in']+b['kn'] if fl(r)]
    F0=max(fs) if fs else None
    best=None
    if t<=0: return None
    if b['g']!='x': return {'u':None,'why':'位置おおよそ'}
    cands=[]
    for a,h,d in PL.get(b['id'],[]):
        if d>12 or a<30: continue
        Fh=max(1,round((h-1.5)/3.0)) if h>=2 else None
        F=max([x for x in (F0,Fh) if x] or [0]) or None
        cands.append(dict(a=a,d=d,F=F,src='pl',solid=h>=6))
    if not cands:
        for a,d,ft,edge in FP.get(b['id'],[]):
            if d>12 or a<30: continue
            cands.append(dict(a=a,d=d,F=F0,src='gsi',solid=ft in(3102,3103)))
    if not cands: return {'u':None,'why':'建物の形なし'}
    def u_of(c):
        F=c['F'] or max(2,round(t/ max(1,min(t,6))))  # unknown floors guess
        return c['a']*F*K/t
    ok=[c for c in cands if 14<=u_of(c)<=130]
    pool=[c for c in ok if c['solid']] or ok or cands
    c=min(pool,key=lambda c:(c['d']>3, not c['solid'], c['d']))
    u=u_of(c)
    conf='中' if (c['F'] and c in ok and c['d']<=6) else '低'
    return {'u':round(u,1),'a':c['a'],'F':c['F'],'d':c['d'],'src':c['src'],'conf':conf}
def cls(u):
    if u is None: return None
    return 'S' if u<30 else 'M' if u<48 else 'F'
if __name__=='__main__':
    truth={'M0168171':'S','M0146809':'S','M0197317':'S','M0176013':'S','M0192543':'S','M0119955':'S','M0117624':'S','M0139082':'S','M0193245':'S','M0208097':'S','M0183711':'S','M0211157':'S','M0187565':'S','M0060381':'S','M0000647':'S','M0092406':'S','M0205505':'F','M0000214':'F','M0167966':'M','M0193693':'M','M0193625':'M'}
    by={b['id']:b for b in B}; ok=0
    for bid,tr in truth.items():
        e=est(by[bid]); c=cls(e.get('u'))
        ok+= c==tr; print(bid,tr,c,e,by[bid]['t'])
    print('acc',ok,len(truth))
    R=[est(b) for b in B]; cnt=collections.Counter(cls(r['u']) if r else None for r in R); print(cnt)
    print(collections.Counter(r.get('conf') for r in R if r))
