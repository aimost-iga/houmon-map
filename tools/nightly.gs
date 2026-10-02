/**
 * 訪問マップ → スプレッドシート「訪問活動記録」への毎晩の書き写し（Google Apps Script）
 *
 * 毎晩0時15分ごろに動いて：
 *  1. 訪問マップ（Firebase：aimost-houmon-map）の、今日より前の活動記録（act）を読む
 *  2. 「明細」タブに1件1行で追記する（不在は 日付×担当者×建物 で1行にまとめ、S列に件数）
 *  3. 書き写しを確かめてから、その日の活動記録をアプリから消す
 * 建物・部屋の記録（b）や修正（typ / netx / pos）には一切さわらない。
 *
 * 置き場所：Apps Script のプロジェクト「訪問マップ 毎晩の書き写し」（スプレッドシートはIDで開く）
 */
const PROJECT = 'aimost-houmon-map';
const FS = 'https://firestore.googleapis.com/v1/projects/' + PROJECT + '/databases/(default)/documents';
const RES = { away: '不在', ihng: 'インターホンNG', fng: '対面NG', again: '再訪', got: '獲得', vac: '未入居' };
const TY = { S: '単身', M: '単身・セミ', F: 'ファミリー' };
const NET = { free: '無料ネットあり', paid: '個別契約（有料）' };
// スプレッドシート「訪問活動記録」
const SHEET_ID = '1m4KTzUK-rpDyYzSfR1jRPiyEEdBfSTWNDHIBLoGyeAQ';
function SS_() { return SpreadsheetApp.openById(SHEET_ID); }

/** 毎晩0時15分の自動実行を1つだけ作る */
function setup() {
  ScriptApp.getProjectTriggers().filter(t => t.getHandlerFunction() === 'nightly').forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('nightly').timeBased().atHour(0).nearMinute(15).everyDays(1).inTimezone('Asia/Tokyo').create();
  log_('自動実行をセットしました（毎晩0時15分ごろ）');
}

// ---------- Firestore（REST） ----------
function fsFetch_(url, opt) {
  opt = opt || {};
  const res = UrlFetchApp.fetch(url, Object.assign({
    headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() },
    muteHttpExceptions: true, contentType: 'application/json'
  }, opt));
  const code = res.getResponseCode();
  if (code === 404) return null;
  if (code >= 300) throw new Error('Firestore ' + code + ': ' + res.getContentText().slice(0, 300));
  const t = res.getContentText();
  return t ? JSON.parse(t) : {};
}
function val_(v) {
  if (!v) return null;
  if ('stringValue' in v) return v.stringValue;
  if ('integerValue' in v) return Number(v.integerValue);
  if ('doubleValue' in v) return v.doubleValue;
  if ('booleanValue' in v) return v.booleanValue;
  if ('nullValue' in v) return null;
  if ('mapValue' in v) { const o = {}; const f = v.mapValue.fields || {}; for (const k in f) o[k] = val_(f[k]); return o; }
  if ('arrayValue' in v) return (v.arrayValue.values || []).map(val_);
  if ('timestampValue' in v) return v.timestampValue;
  return null;
}
function doc_(d) { const o = {}; const f = d.fields || {}; for (const k in f) o[k] = val_(f[k]); return o; }
function getDoc_(path) { const d = fsFetch_(FS + '/' + path); return d ? doc_(d) : null; }
function listDocs_(coll) {
  const out = []; let tok = '';
  do {
    const d = fsFetch_(FS + '/' + coll + '?pageSize=300' + (tok ? '&pageToken=' + encodeURIComponent(tok) : ''));
    (d && d.documents || []).forEach(x => out.push({ id: x.name.split('/').pop(), updateTime: x.updateTime, data: doc_(x) }));
    tok = d && d.nextPageToken;
  } while (tok);
  return out;
}
function deleteDoc_(path, updateTime) {
  fsFetch_(FS + '/' + path + '?currentDocument.updateTime=' + encodeURIComponent(updateTime), { method: 'delete' });
}

// ---------- 住所から町名 ----------
function nz_(t) { return String(t || '').normalize('NFKC').replace(/ヶ/g, 'ケ').replace(/[ 　]/g, ''); }
function townOf_(b) {
  let a = nz_(b.a); const p = nz_(b.p), c = nz_(b.c);
  if (a.indexOf(p) === 0) a = a.slice(p.length);
  let r;
  if (a.indexOf(c) === 0) r = a.slice(c.length);
  else { const m = a.match(/^(?:.+?郡)?.+?[市町村](?:.+?区)?/); r = m ? a.slice(m[0].length) : a; }
  r = r.replace(/^大字/, '');
  const m2 = r.match(/^[^0-9]+/); let t = m2 ? m2[0] : '';
  t = t.replace(/(丁目|番地|番)$/, '').replace(/[一二三四五六七八九十]+$/, '');
  return t || 'その他';
}

// ---------- 本体 ----------
function ymdJst_(d) { return Utilities.formatDate(d, 'Asia/Tokyo', 'yyyyMMdd'); }
function ukey_(e) { return String(e || '').toLowerCase().replace(/[^a-z0-9]/g, '_'); }

function nightly() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) { log_('ほかの実行中のため中止'); return; }
  try { run_(); } catch (e) { log_('失敗：' + e.message); throw e; } finally { lock.releaseLock(); }
}

function run_(todayOverride) {
  const today = todayOverride || ymdJst_(new Date());
  const acts = listDocs_('act').filter(x => x.data.d && x.data.d < today);
  if (!acts.length) { log_('前日までの登録なし'); return; }

  // 名前・建物の情報
  const names = {}; listDocs_('users').forEach(u => { names[u.id] = (u.data.name || '').trim(); });
  const ccs = {}; acts.forEach(a => { for (const k in a.data) { const e = a.data[k]; if (e && typeof e === 'object' && e.cc) ccs[e.cc] = 1; } });
  const B = {}, TYO = {}, NETO = {};
  Object.keys(ccs).forEach(cc => {
    const d = getDoc_('bld/' + cc); if (d && d.j) JSON.parse(d.j).forEach(b => { B[b.id] = b; });
    const t = getDoc_('typ/' + cc); if (t) Object.assign(TYO, t);
    const n = getDoc_('netx/' + cc); if (n) Object.assign(NETO, n);
  });

  const sh = SS_().getSheetByName('明細');
  const have = new Set(keysOf_(sh));

  // 行を作る（不在は まとめる）
  const items = []; const away = {};
  acts.forEach(a => {
    const day = a.data.d;
    for (const k in a.data) {
      const e = a.data[k];
      if (!e || typeof e !== 'object' || e.x || !e.bid || !RES[e.r]) continue;
      if (e.r === 'away') {
        const ak = 'away_' + day + '_' + e.bid + '_' + (e.u || '');
        if (!away[ak]) away[ak] = Object.assign({}, e, { n: 1 }); else { away[ak].n++; away[ak].t = Math.min(away[ak].t, e.t); }
      } else items.push([k, Object.assign({}, e, { n: 1 })]);
    }
  });
  Object.keys(away).forEach(k => items.push([k, away[k]]));
  items.sort((x, y) => x[1].t - y[1].t);

  const rows = [];
  items.forEach(([k, e]) => {
    if (have.has(k)) return;
    const b = B[e.bid] || { p: '', c: '', a: '', n: '(リストにない建物)' };
    const dt = new Date(e.t);
    const u = e.u || '';
    const who = u.indexOf('sh_') === 0 ? u.slice(3) : (names[u] || u || '担当者不明');
    const ty = TY[(TYO[e.bid] && TYO[e.bid].ty) || b.ty] || '判定なし';
    const nv = NETO[e.bid] && NETO[e.bid].v;
    const net = nv === 'unk' ? '不明' : (NET[nv || b.nf] || '不明');
    const isAway = e.r === 'away';
    rows.push([Utilities.formatDate(dt, 'Asia/Tokyo', 'yyyy/MM/dd'), Utilities.formatDate(dt, 'Asia/Tokyo', 'HH:mm'), who,
      b.p || '', b.c || '', b.a ? townOf_(b) : '', b.n || '', "'" + e.bid, isAway ? '不在まとめ' : "'" + (e.room || ''),
      RES[e.r], ty, net, e.why || '', e.net || '', e.what || '', e.when || '', isAway ? '' : String(e.m || '').replace(/\n/g, ' '), "'" + k, e.n]);
  });
  if (rows.length) {
    const start = Math.max(sh.getLastRow(), 1) + 1;
    const need = start + rows.length - 1 - sh.getMaxRows();
    if (need > 0) sh.insertRowsAfter(sh.getMaxRows(), need + 500);
    sh.getRange(start, 1, rows.length, 19).setValues(rows);
    SpreadsheetApp.flush();
  }

  // 業務管理アプリ用に、その日の訪問数を day/<日付>_<人> に残す（消す前に）
  acts.forEach(a => { try { saveVisits_(a); } catch (err) { log_('訪問数を残せなかった：' + a.id + ' ' + err.message); } });

  // 確かめてから消す：その日の記録が全部「明細」に入っている日だけ
  const have2 = new Set(keysOf_(sh));
  let deleted = 0;
  acts.forEach(a => {
    const day = a.data.d; const keys = [];
    for (const k in a.data) {
      const e = a.data[k];
      if (!e || typeof e !== 'object' || e.x || !e.bid || !RES[e.r]) continue;
      keys.push(e.r === 'away' ? 'away_' + day + '_' + e.bid + '_' + (e.u || '') : k);
    }
    if (keys.every(k => have2.has(k))) {
      try { deleteDoc_('act/' + a.id, a.updateTime); deleted++; } catch (err) { log_('消せなかった（次の晩にやり直し）：' + a.id + ' ' + err.message); }
    }
  });
  const sumN = rows.reduce((s, r) => s + Number(r[18] || 0), 0);
  log_('追記 ' + rows.length + '行（訪問 ' + sumN + '件）・アプリから消した記録 ' + deleted + '件');
}

/** 1人1日の訪問数（訪問・対面・獲得など）を day/<日付>_<人> の v に書く（業務管理アプリの成績で使う） */
function saveVisits_(a){
  const v = { doors: 0, face: 0, got: 0, away: 0, ihng: 0, fng: 0, again: 0, vac: 0 };
  for (const k in a.data) {
    const e = a.data[k];
    if (!e || typeof e !== 'object' || e.x || !e.bid || !RES[e.r]) continue;
    v.doors++; v[e.r] = (v[e.r] || 0) + 1;
    if (e.r === 'fng' || e.r === 'again' || e.r === 'got') v.face++;
  }
  const f = {}; for (const k in v) f[k] = { integerValue: String(v[k]) };
  const body = { fields: { u: { stringValue: a.data.u || '' }, d: { stringValue: a.data.d }, v: { mapValue: { fields: f } } } };
  fsFetch_(FS + '/day/' + a.id + '?updateMask.fieldPaths=u&updateMask.fieldPaths=d&updateMask.fieldPaths=v', { method: 'patch', payload: JSON.stringify(body) });
}

/** 試し：明日の日付として動かす（今日の分まで書き写して消す） */
function testAsTomorrow() { run_(ymdJst_(new Date(Date.now() + 86400000))); }

function keysOf_(sh) {
  const n = sh.getLastRow(); if (n < 2) return [];
  return sh.getRange(2, 18, n - 1, 1).getValues().map(r => String(r[0]).replace(/^'/, '')).filter(Boolean);
}
function log_(msg) {
  const ss = SS_();
  let sh = ss.getSheetByName('実行記録');
  if (!sh) { sh = ss.insertSheet('実行記録'); sh.appendRow(['日時', '内容']); }
  sh.appendRow([Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy/MM/dd HH:mm'), msg]);
}
