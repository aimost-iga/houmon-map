// 訪問マップ：Google（Firebase）とのつなぎ。
// アプリ本体（index.html）は、ここが用意する db / user を使って読み書きする。
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js';
import { getAuth, GoogleAuthProvider, signInWithPopup, signOut, onAuthStateChanged } from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js';
import {
  initializeFirestore,
  doc, collection, query, where, getDoc, getDocs, setDoc, updateDoc, deleteDoc,
  onSnapshot, writeBatch, FieldPath, documentId
} from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js';

const CONFIG = {
  apiKey: 'AIzaSyBCfihUw4vf46SoDEYYAKDEKckUsklLV4M',
  authDomain: 'aimost-houmon-map.firebaseapp.com',
  projectId: 'aimost-houmon-map',
  storageBucket: 'aimost-houmon-map.firebasestorage.app',
  messagingSenderId: '716268085137',
  appId: '1:716268085137:web:afa98d8adf185b23c4c430'
};
// 最初の管理者（ルールにも同じアドレスが書いてある）
const OWNER = 'igarashi@aimost.co.jp';

const app = initializeApp(CONFIG);
const auth = getAuth(app);
// 手元への保存はアプリ側（建物リストの控え）で行う。Firestore 自体は起動の速いメモリ保存にする（スマホで重くならないように）
const fs = initializeFirestore(app, {});

const isPlain = v => v && typeof v === 'object' && !Array.isArray(v);
const clean = v => JSON.parse(JSON.stringify(v === undefined ? null : v));
const code = e => {
  const c = (e && e.code) || '';
  if (c === 'not-found') return 'invalid_argument';
  if (c === 'permission-denied') return 'permission_denied';
  if (c === 'resource-exhausted') return 'quota_exceeded';
  return c || 'unknown';
};
const err = e => { const x = new Error((e && e.message) || 'error'); x.code = code(e); x.raw = e; return x; };
const snapOf = s => ({ id: s.id, exists: s.exists(), data: () => (s.exists() ? s.data() : undefined) });
const ref = p => { const parts = p.split('/'); return doc(fs, ...parts); };

// 部分更新：b/（建物の記録）は2段目（rooms.101 など）を丸ごと置き換え、それ以外は1段目を丸ごと置き換える
function flatten(path, patch) {
  const depth = path.startsWith('b/') ? 2 : 1;
  const out = [];
  const walk = (obj, pre) => {
    for (const k of Object.keys(obj)) {
      const v = obj[k]; const segs = pre.concat(k);
      if (isPlain(v) && segs.length < depth) walk(v, segs);
      else out.push([new FieldPath(...segs), clean(v)]);
    }
  };
  walk(patch, []);
  return out;
}

let ME = null; // { email, name, role, areas, vac, active }
const isStaff = () => ME && (ME.role === 'admin' || ME.role === 'staff');
const isAdmin = () => ME && ME.role === 'admin';
const myAreas = () => (ME && ME.areas) || [];

function docApi(path) {
  const r = ref(path);
  return {
    id: path.split('/').pop(), path,
    get: async () => { try { return snapOf(await getDoc(r)); } catch (e) { throw err(e); } },
    set: async d => { try { await setDoc(r, clean(d)); } catch (e) { throw err(e); } },
    update: async patch => {
      const pairs = flatten(path, patch);
      if (!pairs.length) return;
      const args = []; for (const [fp, v] of pairs) args.push(fp, v);
      try { await updateDoc(r, ...args); }
      catch (e) {
        // まだ無い文書への更新は、ルール上「許可なし」で返ってくることがある。無いなら「作る」に回す
        if (e && e.code === 'permission-denied') {
          let exists = true; try { exists = (await getDoc(r)).exists(); } catch (e2) {}
          if (!exists) { const x = new Error('not found'); x.code = 'invalid_argument'; throw x; }
        }
        throw err(e);
      }
    },
    delete: async () => { try { await deleteDoc(r); } catch (e) { throw err(e); } },
    onSnapshot: (next, onErr) => onSnapshot(r, s => next(snapOf(s)), e => onErr && onErr(err(e)))
  };
}
// コレクション全体の見張り。業務委託は担当エリアの文書だけを1つずつ見張る。
function collApi(name) {
  return {
    onSnapshot: (next, onErr) => {
      if (isStaff()) return onSnapshot(collection(fs, name), q => next({ docs: q.docs.map(snapOf), size: q.size, empty: q.empty }), e => onErr && onErr(err(e)));
      const cur = {}; const unsubs = myAreas().map(cc => onSnapshot(ref(name + '/' + cc), s => {
        if (s.exists()) cur[cc] = snapOf(s); else delete cur[cc];
        const docs = Object.values(cur); next({ docs, size: docs.length, empty: !docs.length });
      }, () => {}));
      if (!unsubs.length) setTimeout(() => next({ docs: [], size: 0, empty: true }));
      return () => unsubs.forEach(u => u());
    }
  };
}
// 活動記録：act/<日付>_<人> の1日1人1文書。社員・管理者は全員分、業務委託は自分の分だけ。
const ukey = email => (email || '').toLowerCase().replace(/[^a-z0-9]/g, '_');
function actDayQuery(day) {
  return isStaff() ? query(collection(fs, 'act'), where('d', '==', day)) : null;
}
const act = {
  ref: day => docApi('act/' + day + '_' + ukey(ME.email)),
  watchDay: (day, next) => {
    const q = actDayQuery(day);
    if (q) return onSnapshot(q, s => next(s.docs.map(d => d.data())), () => next([]));
    return onSnapshot(ref('act/' + day + '_' + ukey(ME.email)), s => next(s.exists() ? [s.data()] : []), () => next([]));
  },
  getDay: async day => {
    try {
      const q = actDayQuery(day);
      if (q) return (await getDocs(q)).docs.map(d => d.data());
      const s = await getDoc(ref('act/' + day + '_' + ukey(ME.email)));
      return s.exists() ? [s.data()] : [];
    } catch (e) { return []; }
  }
};

// 業務の記録：day/<日付>_<人> の1日1人1文書（予定・開始/終了・配布・反響対応・日報）。ずっと残す（小さいので）。
// 社員・管理者は全員分を読める。業務委託は自分の分だけ。
const day = {
  ref: d => docApi('day/' + d + '_' + ukey(ME.email)),
  watch: (d, next) => onSnapshot(ref('day/' + d + '_' + ukey(ME.email)), s => next(s.exists() ? s.data() : null), () => next(null)),
  mine: async () => { try { return (await getDocs(query(collection(fs, 'day'), where('u', '==', ME.email)))).docs.map(d => d.data()); } catch (e) { return null; } },
  range: async (from, to) => {
    if (!isStaff()) return [];
    try { return (await getDocs(query(collection(fs, 'day'), where('d', '>=', from), where('d', '<=', to)))).docs.map(d => d.data()); } catch (e) { return null; }
  }
};
// 会社の設定（お題の基準など）：だれでも読める、管理者だけ書ける
const cfg = {
  watch: (id, next) => onSnapshot(ref('cfg/' + id), s => next(s.exists() ? s.data() : null), () => next(null)),
  set: async (id, d) => { try { await setDoc(ref('cfg/' + id), clean(d)); } catch (e) { throw err(e); } }
};

// 人の名前（社員・管理者だけが一覧を読める）
let NAMES = {};
async function loadNames() {
  if (!isStaff()) return;
  try { const q = await getDocs(collection(fs, 'users')); NAMES = {}; q.docs.forEach(d => { NAMES[d.id] = (d.data().name || '').trim(); }); } catch (e) {}
}
const user = {
  me: async () => ({ id: ME.email, name: ME.name || ME.email }),
  isOwner: async () => isAdmin(),
  can: async () => true,
  profiles: async ids => { const o = {}; [].concat(ids).forEach(i => { o[i] = { id: i, name: i === ME.email ? (ME.name || '') : (NAMES[i] || '') }; }); return o; },
  search: async () => []
};

// 建物リスト（月1回入れ替え）。スマホの中に控え（IndexedDB）を持ち、版が同じなら通信せずにすぐ開く。
const IDB_NAME = 'houmon-map', IDB_STORE = 'kv';
function idb_() {
  return new Promise((res, rej) => {
    const r = indexedDB.open(IDB_NAME, 1);
    r.onupgradeneeded = () => r.result.createObjectStore(IDB_STORE);
    r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
  });
}
async function idbGet_(k) { try { const d = await idb_(); return await new Promise(r => { const q = d.transaction(IDB_STORE).objectStore(IDB_STORE).get(k); q.onsuccess = () => r(q.result); q.onerror = () => r(null); }); } catch (e) { return null; } }
async function idbSet_(k, v) { try { const d = await idb_(); await new Promise(r => { const t = d.transaction(IDB_STORE, 'readwrite'); t.objectStore(IDB_STORE).put(v, k); t.oncomplete = r; t.onerror = r; }); } catch (e) {} }
async function loadMaster(onProgress) {
  let meta;
  try { meta = (await getDoc(ref('meta/master'))).data(); } catch (e) { throw err(e); }
  if (!meta) return { meta: null, buildings: [] };
  const want = isStaff() ? (meta.ccs || []) : myAreas().filter(cc => (meta.ccs || []).includes(cc));
  const sig = meta.v + ':' + want.join(',');
  const cached = await idbGet_('master');
  if (cached && cached.sig === sig && Array.isArray(cached.buildings)) return { meta, buildings: cached.buildings };
  // 10市区町村ずつの問い合わせを、まとめて同時に出す
  const chunks = []; for (let i = 0; i < want.length; i += 10) chunks.push(want.slice(i, i + 10));
  let n = 0;
  const parts = await Promise.all(chunks.map(ch => getDocs(query(collection(fs, 'bld'), where(documentId(), 'in', ch))).then(q => {
    n += ch.length; onProgress && onProgress(n, want.length); return q.docs.map(d => d.data());
  })));
  const buildings = [];
  // 建物は市区町村ごとに文字列（j）でしまってある（入れ子の配列を保存できないため）
  for (const d of parts.flat()) for (const b of (d.b || (d.j ? JSON.parse(d.j) : []))) buildings.push(b);
  idbSet_('master', { sig, buildings });
  return { meta, buildings };
}
const noteCache = {};
function loadNotes(cc) {
  if (!noteCache[cc]) noteCache[cc] = getDoc(ref('note/' + cc)).then(s => (s.exists() ? (s.data().n || {}) : {})).catch(() => ({}));
  return noteCache[cc];
}

// 管理者用：使える人の管理
const admin = {
  list: async () => (await getDocs(collection(fs, 'users'))).docs.map(d => Object.assign({ email: d.id }, d.data())),
  save: async (email, data) => { await setDoc(ref('users/' + email.toLowerCase()), clean(data)); await loadNames(); },
  remove: async email => { await deleteDoc(ref('users/' + email.toLowerCase())); await loadNames(); },
  // データの取り込み（Claude が使う）：[{path, data}] をまとめて書く
  put: async (items, onProgress) => {
    let n = 0;
    for (let i = 0; i < items.length;) {
      const batch = writeBatch(fs); let size = 0, cnt = 0;
      // 1回に送れる量には上限（約10MB）があるので、3MB・100件ずつに分けて書く
      while (i < items.length && cnt < 100) {
        const s = new TextEncoder().encode(JSON.stringify(items[i].data)).length;
        if (cnt && size + s > 3e6) break;
        batch.set(ref(items[i].path), items[i].data); size += s; cnt++; i++;
      }
      await batch.commit(); n += cnt; onProgress && onProgress(n, items.length);
    }
    return n;
  },
  // 取り込みファイル（.json または .json.gz）を読んで書き込む
  putFile: async (file, onProgress) => {
    let buf = new Uint8Array(await file.arrayBuffer());
    let txt;
    if (buf[0] === 0x1f && buf[1] === 0x8b) txt = await new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))).text();
    else txt = new TextDecoder().decode(buf);
    const items = JSON.parse(txt);
    if (!Array.isArray(items) || !items.every(x => x && typeof x.path === 'string' && /^(meta|bld|note|b|sum|typ|netx|pos)\/[A-Za-z0-9_\-]+$/.test(x.path) && x.data && typeof x.data === 'object')) throw new Error('取り込みファイルの形が正しくありません');
    const n = await admin.put(items, onProgress);
    await idbSet_('master', null);
    return n;
  },
  putGz: async (b64) => {
    const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
    const txt = await new Response(new Blob([bin]).stream().pipeThrough(new DecompressionStream('gzip'))).text();
    return admin.put(JSON.parse(txt));
  }
};

// ログイン
async function resolveMe(u) {
  const email = (u.email || '').toLowerCase();
  let d = null;
  try { const s = await getDoc(ref('users/' + email)); d = s.exists() ? s.data() : null; } catch (e) { d = null; }
  if (email === OWNER) d = Object.assign({ name: u.displayName || '', role: 'admin', active: true }, d || {}, { role: 'admin', active: true });
  if (!d || d.active === false) return null;
  return Object.assign({ email, name: d.name || u.displayName || email, role: d.role || 'staff', areas: d.areas || [], vac: !!d.vac, active: true });
}
function whenSignedIn() {
  return new Promise(resolve => {
    onAuthStateChanged(auth, async u => {
      if (!u) { resolve({ state: 'out' }); return; }
      const me = await resolveMe(u);
      if (!me) { resolve({ state: 'denied', email: u.email }); return; }
      ME = me; loadNames();
      resolve({ state: 'in', me });
    });
  });
}

window.FB = {
  db: { doc: docApi, collection: collApi },
  user, act, day, cfg, admin, loadMaster, loadNotes, ukey,
  me: () => ME, isStaff, isAdmin,
  whenSignedIn,
  signIn: async () => { const p = new GoogleAuthProvider(); p.setCustomParameters({ prompt: 'select_account' }); await signInWithPopup(auth, p); },
  signOut: async () => { await signOut(auth); location.reload(); }
};
window.dispatchEvent(new Event('fb-ready'));
