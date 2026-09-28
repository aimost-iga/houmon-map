import re
RX_FREE_OTHER = re.compile(r'無料インターネット|インターネット無料|ネット無料|無料ネット')
RX_IKKATSU = re.compile(r'一括契約|一括導入|一括インターネット|一括案件|全戸一括')
RX_TO_KOBETSU = re.compile(r'一括契約\s*(⇒|→|から)\s*個別契約|個別契約に変更')
RX_MAYBE = re.compile(r'(検討|協議).{0,10}$')
def detect(note):
    if not note: return None
    if RX_TO_KOBETSU.search(note): return ('paid', '一括契約から個別契約に変更（特記事項）')
    m = RX_FREE_OTHER.search(note)
    if m: return ('free', '無料インターネットあり（特記事項）')
    for m in RX_IKKATSU.finditer(note):
        tail = note[m.end():m.end()+30]
        if re.search(r'について(協議|検討)|を?(協議|検討)', tail): continue
        return ('free', 'オーナー一括契約のNURO（特記事項）')
    return None
