"""毎月のソニー訪販フリーリスト取り込み。
使い方: python3 update.py 新しいリスト.xlsx 2026-10 [前回データのフォルダ(既定 app)]
- 訪問記録は別保存（棟IDで紐づけ）なのでここでは触らない
- 前回のbuildings.json / notes_*.json と比べて 新着・消えた・変更 を記録する
"""
import sys, os, json, glob, difflib, collections
from listlib import parse_list, z2h
src, month = sys.argv[1], sys.argv[2]
prevdir = sys.argv[3] if len(sys.argv) > 3 else 'app'
OUT = os.environ.get('OUT', 'app'); os.makedirs(OUT, exist_ok=True)

prev_meta, prev = {}, {}
pb = os.path.join(prevdir, 'buildings.json')
if os.path.exists(pb):
    prev_meta = json.load(open(pb))
    prev = {b['id']: b for b in prev_meta['buildings']}
prev_notes = {}
for f in glob.glob(os.path.join(prevdir, 'notes_*.json')):
    prev_notes.update(json.load(open(f)))
baseline = not prev

buildings, notes, stats = parse_list(src)
cur = {b['id']: b for b in buildings}

def new_segments(old, new):
    old, new = z2h(old or ''), z2h(new or '')
    if old == new: return []
    sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
    segs = [new[j1:j2].strip() for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag in ('insert', 'replace') and j2 - j1 >= 8]
    return [s[:140] + ('…' if len(s) > 140 else '') for s in segs][:3]

cnt = collections.Counter()
out = []
for b in buildings:
    p = prev.get(b['id'])
    b['fs'] = p.get('fs', prev_meta.get('month', month)) if p else month
    b['ls'] = month
    if not baseline and (not p or p.get('x')):
        if not p: b['nw'] = 1; cnt['new'] += 1
        else: b['back'] = 1; cnt['back'] += 1
    if p and not p.get('x') and not baseline:
        ch = {}
        if p.get('ap') != b['ap']: ch['ap'] = [p.get('ap'), b['ap']]
        add_in = [r for r in b['in'] if r not in p.get('in', [])]
        if add_in: ch['in'] = add_in
        add_kn = [r for r in b['kn'] if r not in p.get('kn', [])]
        if add_kn: ch['kn'] = add_kn
        if p.get('mo') != b['mo']: ch['mo'] = [p.get('mo'), b['mo']]
        segs = new_segments(prev_notes.get(b['id']), notes.get(b['id']))
        if segs: ch['nt'] = segs
        newflags = [f for f in b['f'] if f not in p.get('f', [])]
        if newflags: ch['f'] = newflags
        # keep the exact map position so pins don't jump between months
        b['la'], b['lo'] = p['la'], p['lo']
        for k in ('g', 'ty', 'tu', 'tc', 'nf', 'nfs'):
            if k in p: b[k] = p[k]
        if ch: b['ch'] = ch; cnt['changed'] += 1
    elif p:
        b['la'], b['lo'] = p['la'], p['lo']
        for k in ('g', 'ty', 'tu', 'tc', 'nf', 'nfs'):
            if k in p: b[k] = p[k]
    out.append(b)
# building-wide free internet hints from the notes (only when not decided yet)
try:
    from netdetect import detect
    for b in out:
        if 'nf' not in b:
            r = detect(notes.get(b['id']))
            if r: b['nf'], b['nfs'] = r
except ImportError:
    pass
# buildings that disappeared: keep them, marked as off-list
for bid, p in prev.items():
    if bid in cur: continue
    q = dict(p); q.pop('ch', None); q.pop('nw', None); q.pop('back', None)
    if not q.get('x'): q['x'] = month; cnt['gone'] += 1
    out.append(q)
    if bid in prev_notes: notes[bid] = prev_notes[bid]

hist = prev_meta.get('history', [])
hist = [h for h in hist if h['month'] != month] + [{'month': month, 'total': len(buildings), 'new': cnt['new'], 'gone': cnt['gone'], 'changed': cnt['changed'], 'back': cnt['back'], 'source': os.path.basename(src)}]
meta = {'generated': month, 'month': month, 'source': os.path.basename(src), 'baseline': baseline, 'history': hist, 'buildings': out}
json.dump(meta, open(os.path.join(OUT, 'buildings.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
for f in glob.glob(os.path.join(OUT, 'notes_*.json')): os.remove(f)
pm = {x['id']: x['cc'][:2] for x in out}
g = collections.defaultdict(dict)
for k, v in notes.items():
    if k in pm: g[pm[k]][k] = v
for p, v in g.items():
    json.dump(v, open(os.path.join(OUT, f'notes_{p}.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
print(stats, 'this list', len(buildings), 'kept total', len(out), dict(cnt))
