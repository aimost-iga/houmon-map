import gzip, json, os, math, collections
SRC = '/tmp/rvf/public'
OUT = 'app/roads'; os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT): os.remove(os.path.join(OUT, f))
BB = (138.4, 34.55, 140.95, 37.2)   # lon0 lat0 lon1 lat1
CELL = 0.2
CLS = {'motorway': 0, 'trunk': 1, 'primary': 2, 'secondary': 3}
def dp(pts, tol):
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]; dx, dy = b[0]-a[0], b[1]-a[1]; L = dx*dx+dy*dy
    best, bi = -1, 0
    for i in range(1, len(pts)-1):
        p = pts[i]
        if L == 0: d = (p[0]-a[0])**2+(p[1]-a[1])**2
        else:
            t = max(0, min(1, ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/L)); d = (p[0]-a[0]-t*dx)**2+(p[1]-a[1]-t*dy)**2
        if d > best: best, bi = d, i
    if best <= tol*tol: return [a, b]
    return dp(pts[:bi+1], tol)[:-1] + dp(pts[bi:], tol)
cells = collections.defaultdict(lambda: {'n': [], 'ni': {}, 'r': []})
low = {'n': [], 'ni': {}, 'r': []}
def add(bucket, cls, name, ref, pts):
    label = name or (('国道' if cls == 1 else '') + ref + ('号' if cls == 1 and ref else '') if ref else '')
    if label not in bucket['ni']: bucket['ni'][label] = len(bucket['n']); bucket['n'].append(label)
    q = [(round(x*1e5), round(y*1e5)) for x, y in pts]
    flat = [q[0][0], q[0][1]]
    for i in range(1, len(q)): flat += [q[i][0]-q[i-1][0], q[i][1]-q[i-1][1]]
    bucket['r'].append([cls, bucket['ni'][label], flat])
nfeat = 0
for fc, cls in CLS.items():
    d = json.load(gzip.open(f'{SRC}/osm_{fc}.geojson.gz'))
    for f in d['features']:
        g = f['geometry']
        lines = [g['coordinates']] if g['type'] == 'LineString' else g['coordinates'] if g['type'] == 'MultiLineString' else []
        p = f['properties']
        for ln in lines:
            xs = [c[0] for c in ln]; ys = [c[1] for c in ln]
            if max(xs) < BB[0] or min(xs) > BB[2] or max(ys) < BB[1] or min(ys) > BB[3]: continue
            pts = dp([tuple(c[:2]) for c in ln], 0.00004)
            nfeat += 1
            cx0, cx1 = int((min(xs)-BB[0])//CELL), int((max(xs)-BB[0])//CELL)
            cy0, cy1 = int((min(ys)-BB[1])//CELL), int((max(ys)-BB[1])//CELL)
            for cx in range(cx0, cx1+1):
                for cy in range(cy0, cy1+1):
                    add(cells[(cx, cy)], cls, p.get('name') or '', p.get('ref') or '', pts)
            if cls <= 1:
                add(low, cls, p.get('name') or '', p.get('ref') or '', dp(pts, 0.0004))
tot = 0
idx = []
for (cx, cy), b in cells.items():
    fn = f'r_{cx}_{cy}.json'
    s = json.dumps({'n': b['n'], 'r': b['r']}, ensure_ascii=False, separators=(',', ':'))
    open(os.path.join(OUT, fn), 'w').write(s); tot += len(s); idx.append([cx, cy])
s = json.dumps({'n': low['n'], 'r': low['r']}, ensure_ascii=False, separators=(',', ':'))
open(os.path.join(OUT, 'low.json'), 'w').write(s)
json.dump({'bb': BB, 'cell': CELL, 'cells': idx}, open(os.path.join(OUT, 'index.json'), 'w'), separators=(',', ':'))
print('features', nfeat, 'cells', len(cells), 'total KB', tot//1024, 'low KB', len(s)//1024, 'max cell KB', max(os.path.getsize(os.path.join(OUT, f'r_{c[0]}_{c[1]}.json')) for c in idx)//1024)
