import json, os, sys, collections
src = sys.argv[1]
OUT = 'app/streets'; os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT): os.remove(os.path.join(OUT, f))
d = json.load(open(src))
ways = d['w'] if isinstance(d, dict) else d
CELL = 0.08; LO0, LA0 = 138.0, 34.0
def dp(pts, tol):
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]; dx, dy = b[0]-a[0], b[1]-a[1]; L = dx*dx+dy*dy
    best, bi = -1, 0
    for i in range(1, len(pts)-1):
        p = pts[i]
        if L == 0: dd = (p[0]-a[0])**2+(p[1]-a[1])**2
        else:
            t = max(0, min(1, ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/L)); dd = (p[0]-a[0]-t*dx)**2+(p[1]-a[1]-t*dy)**2
        if dd > best: best, bi = dd, i
    if best <= tol*tol: return [a, b]
    return dp(pts[:bi+1], tol)[:-1] + dp(pts[bi:], tol)
cells = collections.defaultdict(lambda: {'n': [''], 'ni': {'': 0}, 'r': []})
npts = 0
for cls, name, flat in ways:
    x, y = flat[0], flat[1]; pts = [(x, y)]
    for i in range(2, len(flat), 2): x += flat[i]; y += flat[i+1]; pts.append((x, y))
    pts = dp(pts, 2.0)   # units of 1e-5 deg (~2m)
    npts += len(pts)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    cx0, cx1 = int((min(xs)/1e5-LO0)//CELL), int((max(xs)/1e5-LO0)//CELL)
    cy0, cy1 = int((min(ys)/1e5-LA0)//CELL), int((max(ys)/1e5-LA0)//CELL)
    enc = [pts[0][0], pts[0][1]]
    for i in range(1, len(pts)): enc += [pts[i][0]-pts[i-1][0], pts[i][1]-pts[i-1][1]]
    for cx in range(cx0, cx1+1):
        for cy in range(cy0, cy1+1):
            b = cells[(cx, cy)]
            nm = name if cls in (4, 7, 8) else ''
            if nm not in b['ni']: b['ni'][nm] = len(b['n']); b['n'].append(nm)
            b['r'].append([cls, b['ni'][nm], enc])
tot = 0; idx = []
for (cx, cy), b in cells.items():
    s = json.dumps({'n': b['n'], 'r': b['r']}, ensure_ascii=False, separators=(',', ':'))
    open(os.path.join(OUT, f's_{cx}_{cy}.json'), 'w').write(s); tot += len(s); idx.append([cx, cy])
json.dump({'o': [LO0, LA0], 'cell': CELL, 'cells': idx}, open(os.path.join(OUT, 'index.json'), 'w'), separators=(',', ':'))
print('ways', len(ways), 'pts', npts, 'cells', len(idx), 'MB', round(tot/1e6, 1), 'max KB', max(os.path.getsize(os.path.join(OUT, f's_{c[0]}_{c[1]}.json')) for c in idx)//1024)
