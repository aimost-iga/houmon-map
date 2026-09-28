import openpyxl, glob, re, csv, json, hashlib, math, collections, os, unicodedata

SP = os.path.dirname(os.path.abspath(__file__))
GEO = os.path.join(SP, 'geo')

PREFS = {'08': '茨城県', '09': '栃木県', '10': '群馬県', '11': '埼玉県', '12': '千葉県', '13': '東京都', '14': '神奈川県', '22': '静岡県'}
PREF_NAMES = set(PREFS.values())

def z2h(s):
    return unicodedata.normalize('NFKC', s or '')

KN = '〇一二三四五六七八九'
def kan(n):
    n = int(n)
    if n < 10: return KN[n]
    t, o = divmod(n, 10)
    return (KN[t] if t > 1 else '') + '十' + (KN[o] if o else '')

def canon(s):
    s = z2h(s)
    s = s.replace('ヶ', 'ケ').replace('ヵ', 'ケ').replace('之', 'の').replace('ノ', 'の').replace('　', '').replace(' ', '')
    s = re.sub(r'(\d+)丁目', lambda m: kan(m.group(1)) + '丁目', s)
    return s

# ---------- town coordinates ----------
towns = collections.defaultdict(dict)    # (pref, city) -> {town canon: (lat, lng)}
citycode = {}
with open(os.path.join(GEO, 'latest.csv'), encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if r['都道府県名'] not in PREF_NAMES: continue
        key = (r['都道府県名'], r['市区町村名'])
        citycode[key] = r['市区町村コード']
        t = canon(r['大字町丁目名'])
        try:
            towns[key][t] = (float(r['緯度']), float(r['経度']))
        except ValueError:
            pass
citycent = {}
for k, d in towns.items():
    if d:
        citycent[k] = (sum(v[0] for v in d.values()) / len(d), sum(v[1] for v in d.values()) / len(d))
cities_by_pref = collections.defaultdict(list)
for (p, c) in towns:
    cities_by_pref[p].append(c)
for p in cities_by_pref:
    cities_by_pref[p].sort(key=len, reverse=True)

def geocode(addr):
    a = z2h(addr).replace(' ', '').replace('　', '')
    pref = next((p for p in PREF_NAMES if a.startswith(p)), None)
    if not pref: return None
    rest = a[len(pref):]
    city = None
    for c in cities_by_pref[pref]:
        cc = canon(c)
        if canon(rest).startswith(cc):
            city = c; rest = canon(rest)[len(cc):]; break
        if rest.startswith(cc):
            city = c; rest = rest[len(cc):]; break
        # 郡 omitted in address
        m = re.match(r'.+?郡(.+)', cc)
        if m and rest.startswith(m.group(1)):
            city = c; rest = rest[len(m.group(1)):]; break
    if not city:
        # ward reorganised (e.g. 浜松市中央区): try every ward of the parent city
        m = re.match(r'(.+?市)(.+?区)(.*)', rest)
        if m:
            r = canon(m.group(3)); best = None
            for c in cities_by_pref[pref]:
                if not c.startswith(m.group(1)): continue
                for t, ll in towns[(pref, c)].items():
                    if t and r.startswith(t) and (best is None or len(t) > len(best[1])):
                        best = (c, t, ll)
            if best:
                return pref, best[0], best[2], 'town', r[len(best[1]):]
        return None
    key = (pref, city)
    r = canon(rest)
    best = None
    for t, ll in towns[key].items():
        if t and r.startswith(t) and (best is None or len(t) > len(best[0])):
            best = (t, ll)
    level = 'town'
    if not best:
        r2 = re.sub(r'[一二三四五六七八九十]+丁目.*', '', r)
        for t, ll in towns[key].items():
            tt = re.sub(r'[一二三四五六七八九十]+丁目$', '', t)
            if tt and r2.startswith(tt) and (best is None or len(tt) > len(best[0])):
                best = (tt, ll)
        level = 'town2'
    if not best:
        return pref, city, citycent.get(key), 'city', rest
    return pref, city, best[1], level, r[len(best[0]):]

def jitter(latlng, seed, level):
    h = int(hashlib.md5(seed.encode()).hexdigest()[:8], 16)
    ang = (h % 3600) / 3600 * 2 * math.pi
    rad = {'town': 0.00045, 'town2': 0.0012, 'city': 0.006}[level] * (0.35 + ((h >> 12) % 1000) / 1540)
    return round(latlng[0] + rad * math.sin(ang), 6), round(latlng[1] + rad * math.cos(ang) * 1.22, 6)

# ---------- notes parsing ----------
def rooms_from(s):
    s = z2h(s or '')
    out = []
    for tok in re.split(r'[,、・/\s]+', s):
        m = re.match(r'^([A-Za-z]?-?\d{1,5}[A-Za-z]?)(号室|号)?$', tok.strip())
        if m:
            v = m.group(1)
            if v not in out: out.append(v)
    return out

KANYU = re.compile(r'((?:\d{2,5}(?:号室|号)?[・,、\s]*)+)勧誘禁止')
FLAG_RULES = [
    ('hanbai_ng', '訪販禁止', re.compile(r'訪販禁止|訪販(?:は|:|：)?\s*(?:NG|ＮＧ|×|不可|禁止)|直訪販×|訪問販売(?:は)?(?:NG|禁止|不可)|訪問NG')),
    ('hanbai_tri', '訪販△（条件付き）', re.compile(r'訪販[:：]?\s*△')),
    ('hanbai_ok', '訪販OK', re.compile(r'訪販[:：]\s*(?:OK|ＯＫ|〇|○)')),
    ('teikyo_ng', '一部提供不可あり', re.compile(r'提供不可|提供NG|提供ＮＧ|部分提供')),
    ('goui_ng', '合意不可の記載', re.compile(r'合意不可')),
    ('post_ng', 'ポスティングNG', re.compile(r'ポスティング(?:は)?\s*(?:NG|ＮＧ|×|不可|禁止)')),
    ('kanyu', '勧誘禁止の部屋あり', re.compile(r'勧誘禁止')),
]

def snippets(text, rx, n=2):
    out = []
    for m in rx.finditer(text):
        a = max(0, m.start() - 45); b = min(len(text), m.end() + 35)
        out.append(('…' if a else '') + text[a:b].strip() + ('…' if b < len(text) else ''))
        if len(out) >= n: break
    return out

def parse_list(src):
    # ---------- load list ----------
    ws = openpyxl.load_workbook(src, read_only=True).worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    hdr = rows[0]
    buildings, notes = [], {}
    stats = collections.Counter()
    for r in rows[1:]:
        bid, name, zipc, addr, mgmt, tel, kind, total, apps, month, note, inst = r[:12]
        if not addr or not any(z2h(addr).startswith(p) for p in PREF_NAMES):
            continue
        g = geocode(addr)
        if not g or not g[2]:
            stats['fail'] += 1
            continue
        pref, city, ll, level, tail = g
        stats[level] += 1
        lat, lng = jitter(ll, bid + (tail or ''), level)
        note = (note or '').strip()
        nz = z2h(note)
        flags = []
        warn = []
        for key, label, rx in FLAG_RULES:
            if rx.search(nz):
                flags.append(key)
                for s in snippets(nz, rx, 1):
                    warn.append([label, s])
        if 'hanbai_ng' in flags and 'hanbai_ok' in flags:
            flags.remove('hanbai_ok')
        kanyu = []
        for m in KANYU.finditer(nz):
            for v in rooms_from(m.group(1)):
                if 2 <= len(v) <= 4 and v not in kanyu: kanyu.append(v)
        b = {
            'id': bid, 'n': z2h(name or '').strip(), 'a': z2h(addr).strip(), 'z': str(zipc or ''),
            'p': pref, 'c': city, 'cc': citycode[(pref, city)],
            'la': lat, 'lo': lng, 'g': level[0],
            'm': (mgmt or '').strip(), 'mt': (lambda t: ('0' + t) if re.fullmatch(r'[1-9]\d{8,9}', t) else ('' if t in ('#N/A', 'None') else t))(str(tel or '').strip()), 't': total or 0, 'ap': apps or 0,
            'mo': str(month or '').replace('\n', ''), 'in': rooms_from(inst), 'kn': kanyu,
            'f': flags, 'w': warn,
        }
        buildings.append(b)
        if note: notes[bid] = note
    
    
    return buildings, notes, stats
