/**
 * 業務の自動通知と Googleカレンダーへの反映（Google Apps Script）
 * 「訪問マップ 毎晩の書き写し」と同じプロジェクトに、このファイルを足して使う（nightly.gs の道具を使うため）。
 *
 * 10分ごとに動いて：
 *  1. 今日の予定を Googleカレンダー「AImost 業務予定」に入れる。本人を招待するので、本人のカレンダーにも出る。
 *     開始・終了を押すと、実際にやった時間に書き換える。休みの日は終日の「休み」を入れる。
 *  2. 決まった時刻に、まだの人だけにメールで知らせる（予定の申告・開始の押し忘れ・終了の押し忘れ・日報）。
 *  3. 毎朝、代表へ昨日の全員分のまとめ。月曜の朝、本人へ先週の振り返り。
 * 最初に一度だけ setupNotify を実行する（10分ごとの自動実行が1つできる）。
 */
const APP_URL = 'https://aimost-iga.github.io/houmon-map/';
const CAL_NAME = 'AImost 業務予定';
const OWNER_MAIL = 'igarashi@aimost.co.jp';
// 知らせる時刻（ここを書き換えれば変えられる）
const NT = {
  plan: '09:30',    // 予定も休みも申告していない人へ
  lateStart: 15,    // 予定の開始時刻から、この分数たっても「開始」が押されていない人へ
  longRun: 4,       // 「開始」から、この時間たっても「終了」が押されていない人へ
  report: '20:30',  // 日報が出ていない人へ
  summary: '08:30', // 代表へ昨日のまとめ
  weekly: '08:00'   // 月曜：本人へ先週の振り返り
};
const KIND_J = { door: '訪販', call: '反響対応', post: '配布', other: 'その他' };

/** 10分ごとの自動実行を1つだけ作る（最初に一度だけ実行） */
function setupNotify() {
  ScriptApp.getProjectTriggers().filter(t => t.getHandlerFunction() === 'tick').forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('tick').timeBased().everyMinutes(10).create();
  cal_();
  log_('通知とカレンダー反映の自動実行をセットしました（10分ごと）');
}

function tick() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) return;
  try { tick_(new Date()); } catch (e) { log_('通知の失敗：' + e.message); throw e; } finally { lock.releaseLock(); }
}

/** 試し：今の時点で動かす（メールは送られる） */
function testTick() { tick_(new Date()); }

function tick_(now) {
  const today = ymdJst_(now);
  const hhmm = Utilities.formatDate(now, 'Asia/Tokyo', 'HH:mm');
  const P = PropertiesService.getScriptProperties();
  const props = P.getProperties();
  cleanup_(P, props, today);
  const was = k => !!props['n_' + k];
  const mark = k => { P.setProperty('n_' + k, today); props['n_' + k] = today; };

  const users = people_();
  const days = {};
  users.forEach(u => { days[u.email] = getDoc_('day/' + today + '_' + ukey_(u.email)); });

  try { syncCal_(today, now, users, days, P, props); } catch (e) { log_('カレンダー反映の失敗：' + e.message); }

  users.forEach(u => {
    if (u.nt === false) return;
    const d = days[u.email] || {};
    const uk = ukey_(u.email);
    const plans = Object.keys(d.plan || {}).map(id => Object.assign({ id }, d.plan[id]));
    const ses = Object.keys(d.ses || {}).map(id => Object.assign({ id }, d.ses[id]));
    const running = ses.find(s => !s.en);
    const active = plans.length || ses.length;

    // 朝：予定も休みも申告していない
    if (hhmm >= NT.plan && !d.off && !active && !was(today + '_plan_' + uk)) {
      mark(today + '_plan_' + uk);
      mail_(u, '今日の予定がまだ申告されていません',
        `${u.name}さん、おはようございます。<br>今日の予定がまだ申告されていません。アプリの「業務」から、今日やることを申告してください。<br>休みの日は「今日は休み」を押しておくと、連続記録が途切れません。`);
    }
    // 予定の開始時刻を過ぎても「開始」が押されていない
    plans.forEach(p => {
      const st = at_(today, p.s), en = at_(today, p.e);
      if (!st || !en || d.sub) return;
      if (now.getTime() < st.getTime() + NT.lateStart * 60000 || now >= en) return;
      if (ses.some(s => s.pid === p.id) || running) return;
      const k = today + '_ls_' + uk + '_' + p.id;
      if (was(k)) return; mark(k);
      mail_(u, `${p.s}からの${KIND_J[p.k] || ''}がまだ開始されていません`,
        `${u.name}さん、${p.s}〜${p.e}の「${KIND_J[p.k] || ''}」${p.m ? '（' + esc_(p.m) + '）' : ''}がまだ開始されていません。<br>始めているなら、アプリで「開始」を押してください。予定が変わったときは「予定を直す」からどうぞ。`);
    });
    // 「終了」の押し忘れ
    if (running && now.getTime() - running.st >= NT.longRun * 3600000 && !was('lr_' + uk + '_' + running.id)) {
      mark('lr_' + uk + '_' + running.id);
      mail_(u, `「${KIND_J[running.k] || ''}」を開始してから${NT.longRun}時間たちました`,
        `${u.name}さん、${Utilities.formatDate(new Date(running.st), 'Asia/Tokyo', 'H:mm')}に開始した「${KIND_J[running.k] || ''}」が続いています。<br>終わっているなら、アプリで「終了」を押してください（押し忘れがあると、今日の数字が正しく出ません）。`);
    }
    // 夜：日報がまだ
    if (hhmm >= NT.report && !d.off && active && !d.sub && !was(today + '_rep_' + uk)) {
      mark(today + '_rep_' + uk);
      mail_(u, '今日の日報がまだです',
        `${u.name}さん、おつかれさまです。<br>今日の日報がまだ出ていません。アプリの「業務」の一番下から、振り返りをひとこと書いて提出してください（1分で終わります）。`);
    }
    // 月曜：先週の振り返り
    if (now.getDay() === 1 && hhmm >= NT.weekly && !was(today + '_wk_' + uk)) {
      mark(today + '_wk_' + uk);
      try { weekly_(u, today); } catch (e) { log_('週の振り返りの失敗：' + u.email + ' ' + e.message); }
    }
  });

  // 朝：代表へ昨日のまとめ
  if (hhmm >= NT.summary && !was(today + '_sum')) {
    mark(today + '_sum');
    try { summary_(users, today); } catch (e) { log_('まとめの失敗：' + e.message); }
  }
}

// ---------- 人 ----------
function people_() {
  const out = listDocs_('users').map(x => Object.assign({ email: x.id }, x.data)).filter(u => u.active !== false);
  if (!out.some(u => u.email === OWNER_MAIL)) out.push({ email: OWNER_MAIL, name: '代表', role: 'admin' });
  out.forEach(u => { u.name = (u.name || '').trim() || u.email.split('@')[0]; });
  return out;
}

// ---------- 1日の数字 ----------
function stat_(d) {
  d = d || {};
  const h = { door: 0, call: 0, post: 0, other: 0 }; let work = 0;
  Object.keys(d.ses || {}).forEach(id => { const s = d.ses[id]; if (!s || !s.st || !s.en) return; const ms = Math.max(0, s.en - s.st); h[s.k] = (h[s.k] || 0) + ms; work += ms; });
  const v = Object.assign({ doors: 0, face: 0, got: 0 }, d.v || {});
  const han = Object.assign({ call: 0, conn: 0, prop: 0, got: 0 }, d.han || {});
  let post = 0; Object.keys(d.post || {}).forEach(k => { post += Number(d.post[k].n) || 0; });
  return { h, work, v, han, post, got: (v.got || 0) + (han.got || 0), off: !!d.off, sub: !!d.sub, plan: Object.keys(d.plan || {}).length };
}
const hr_ = ms => (ms / 3600000).toFixed(1);

function summary_(users, today) {
  const y = ymdJst_(new Date(dateOf_(today).getTime() - 86400000));
  const yd = dateOf_(y);
  const rows = users.map(u => {
    const d = getDoc_('day/' + y + '_' + ukey_(u.email));
    const s = stat_(d);
    const state = s.off ? '休み' : s.sub ? '日報済み' : (s.plan || s.work) ? '<b style="color:#c0392b">日報なし</b>' : '<b style="color:#c0392b">申告なし</b>';
    return { u, s, state, refl: d && d.refl ? d.refl : '' };
  });
  const td = 'style="padding:6px 8px;border-bottom:1px solid #ddd;text-align:right"';
  const th = 'style="padding:6px 8px;border-bottom:1px solid #ddd;text-align:left"';
  let html = `<p>${yd.getMonth() + 1}月${yd.getDate()}日（${'日月火水木金土'[yd.getDay()]}）の全員分のまとめです。</p>`;
  html += `<table style="border-collapse:collapse;font-size:13px"><tr><th ${th}>名前</th><th ${th}>状態</th><th ${td}>稼働</th><th ${td}>訪問</th><th ${td}>対面</th><th ${td}>獲得</th><th ${td}>配布</th><th ${td}>反響電話</th><th ${td}>訪問/時</th></tr>`;
  rows.forEach(r => {
    const s = r.s; const per = s.h.door > 600000 ? (s.v.doors / (s.h.door / 3600000)).toFixed(1) : '—';
    html += `<tr><td ${th}>${esc_(r.u.name)}</td><td ${th}>${r.state}</td><td ${td}>${hr_(s.work)}h</td><td ${td}>${s.v.doors}</td><td ${td}>${s.v.face}</td><td ${td}>${s.got}</td><td ${td}>${s.post}</td><td ${td}>${s.han.call}</td><td ${td}>${per}</td></tr>`;
  });
  html += '</table>';
  const refl = rows.filter(r => r.refl);
  if (refl.length) html += '<p style="margin-top:14px"><b>振り返り</b></p>' + refl.map(r => `<p>・${esc_(r.u.name)}：${esc_(r.refl)}</p>`).join('');
  MailApp.sendEmail({ to: OWNER_MAIL, subject: `【業務まとめ】${yd.getMonth() + 1}/${yd.getDate()} の全員分`, htmlBody: wrap_(html), name: '訪問マップ（AImost）' });
}

function weekly_(u, today) {
  const t0 = dateOf_(today).getTime();
  const sum = (from, n) => {
    const a = { work: 0, doors: 0, face: 0, got: 0, post: 0, call: 0, doorH: 0, subs: 0, offs: 0, none: 0 };
    for (let i = 0; i < n; i++) {
      const d = getDoc_('day/' + ymdJst_(new Date(t0 - (from + i) * 86400000)) + '_' + ukey_(u.email));
      const s = stat_(d);
      a.work += s.work; a.doors += s.v.doors; a.face += s.v.face; a.got += s.got; a.post += s.post; a.call += s.han.call; a.doorH += s.h.door;
      if (s.sub) a.subs++; if (s.off) a.offs++; if (!d || (!s.off && !s.plan && !s.work)) a.none++;
    }
    return a;
  };
  const w1 = sum(1, 7), w0 = sum(8, 7);
  if (!w1.work && !w0.work && !w1.doors) return;
  const cmp = (a, b) => b ? `（先々週 ${b}${a >= b ? '・▲' : '・▼'}${Math.abs(Math.round((a - b) / b * 100))}%）` : '';
  let html = `<p>${esc_(u.name)}さん、先週（月〜日）の振り返りです。</p><ul>`;
  html += `<li>稼働時間：<b>${hr_(w1.work)}時間</b>${cmp(+hr_(w1.work), +hr_(w0.work))}</li>`;
  html += `<li>訪問：<b>${w1.doors}</b>${cmp(w1.doors, w0.doors)}・対面：<b>${w1.face}</b>・対面率 ${w1.doors ? Math.round(w1.face / w1.doors * 100) : 0}%</li>`;
  if (w1.doorH > 600000) html += `<li>訪販1時間あたり訪問：<b>${(w1.doors / (w1.doorH / 3600000)).toFixed(1)}部屋</b></li>`;
  html += `<li>獲得：<b>${w1.got}件</b>${cmp(w1.got, w0.got)}</li>`;
  if (w1.post || w0.post) html += `<li>配布：<b>${w1.post}枚</b>${cmp(w1.post, w0.post)}</li>`;
  if (w1.call || w0.call) html += `<li>反響電話：<b>${w1.call}件</b>${cmp(w1.call, w0.call)}</li>`;
  html += `<li>日報：${w1.subs}日・休み：${w1.offs}日${w1.none ? `・<b style="color:#c0392b">申告なし：${w1.none}日</b>` : ''}</li></ul>`;
  html += '<p>くわしくはアプリの「業務」→「今月の成績」で、自分の流れのどこが弱いか見られます。今週もいきましょう！</p>';
  mail_(u, '先週の振り返り', html, true);
}

// ---------- Googleカレンダー ----------
function cal_() {
  const c = CalendarApp.getCalendarsByName(CAL_NAME)[0];
  return c || CalendarApp.createCalendar(CAL_NAME, { color: CalendarApp.Color.BLUE, summary: '訪問マップの「業務」で申告した予定（自動で入ります。ここで直してもアプリには戻りません）' });
}
function syncCal_(today, now, users, days, P, props) {
  let cal = null; const getCal = () => cal || (cal = cal_());
  users.forEach(u => {
    const d = days[u.email]; const uk = ukey_(u.email);
    const pre = 'ev_' + today + '_' + uk + '_';
    const want = {};
    if (d && d.off) want.off = { title: `【${u.name}】休み`, allDay: true };
    if (d && !d.off) {
      const ses = Object.keys(d.ses || {}).map(id => Object.assign({ id }, d.ses[id]));
      Object.keys(d.plan || {}).forEach(id => {
        const p = d.plan[id]; let st = at_(today, p.s), en = at_(today, p.e); if (!st || !en) return;
        const mine = ses.filter(s => s.pid === id);
        let mark = '';
        if (mine.length) {
          const run = mine.some(s => !s.en);
          st = new Date(Math.min.apply(null, mine.map(s => s.st)));
          const last = Math.max.apply(null, mine.map(s => s.en || now.getTime()));
          en = new Date(run ? Math.max(last, Math.min(en.getTime(), last + 3600000)) : last);
          if (en.getTime() - st.getTime() < 15 * 60000) en = new Date(st.getTime() + 15 * 60000);
          mark = run ? '▶ ' : '✔ ';
        }
        want[id] = { title: `${mark}【${u.name}】${KIND_J[p.k] || ''}${p.m ? '：' + p.m : ''}`, st, en };
      });
      ses.filter(s => !s.pid).forEach(s => {
        const st = new Date(s.st); let en = new Date(s.en || now.getTime());
        if (en.getTime() - st.getTime() < 15 * 60000) en = new Date(st.getTime() + 15 * 60000);
        want['s' + s.id] = { title: `${s.en ? '✔ ' : '▶ '}【${u.name}】${KIND_J[s.k] || ''}（予定外）`, st, en };
      });
    }
    // 作る・直す
    Object.keys(want).forEach(id => {
      const w = want[id]; const key = pre + id;
      const hash = w.title + '|' + (w.allDay ? 'all' : w.st.getTime() + '-' + w.en.getTime());
      const cur = (props[key] || '').split('|');
      if (cur[0] && cur.slice(1).join('|') === hash) return;
      let ev = null;
      if (cur[0]) { try { ev = getCal().getEventById(cur[0]); } catch (e) { ev = null; } }
      const guests = u.email === OWNER_MAIL ? '' : u.email;
      const desc = '訪問マップの「業務」から自動で入れた予定です。\n' + APP_URL;
      if (!ev) {
        ev = w.allDay ? getCal().createAllDayEvent(w.title, dateOf_(today), { guests, sendInvites: false, description: desc })
                      : getCal().createEvent(w.title, w.st, w.en, { guests, sendInvites: false, description: desc });
      } else {
        ev.setTitle(w.title);
        if (w.allDay) ev.setAllDayDate(dateOf_(today)); else ev.setTime(w.st, w.en);
      }
      const val = ev.getId() + '|' + hash; P.setProperty(key, val); props[key] = val;
    });
    // 消された予定はカレンダーからも消す
    Object.keys(props).filter(k => k.indexOf(pre) === 0 && !want[k.slice(pre.length)]).forEach(k => {
      try { const ev = getCal().getEventById(props[k].split('|')[0]); if (ev) ev.deleteEvent(); } catch (e) {}
      P.deleteProperty(k); delete props[k];
    });
  });
}

// ---------- 道具 ----------
function dateOf_(s) { return new Date(+s.slice(0, 4), +s.slice(4, 6) - 1, +s.slice(6, 8)); }
function at_(day, hm) { if (!hm || !/^\d{1,2}:\d{2}$/.test(hm)) return null; return Utilities.parseDate(day + ' ' + hm, 'Asia/Tokyo', 'yyyyMMdd HH:mm'); }
function esc_(t) { return String(t || '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }
function wrap_(html) { return `<div style="font-family:sans-serif;font-size:14px;line-height:1.7;color:#1b2233">${html}<p style="margin-top:18px"><a href="${APP_URL}" style="background:#1B1FA8;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;display:inline-block">アプリを開く</a></p><p style="color:#888;font-size:12px">このメールは訪問マップから自動で送っています。</p></div>`; }
function mail_(u, subject, html, isHtmlBlock) {
  if (MailApp.getRemainingDailyQuota() < 3) { log_('メールの1日の上限に近いので送りませんでした：' + u.email + ' ' + subject); return; }
  MailApp.sendEmail({ to: u.email, subject: '【訪問マップ】' + subject, htmlBody: wrap_(isHtmlBlock ? html : `<p>${html}</p>`), name: '訪問マップ（AImost）' });
}
// 3日より前の「送った印」とカレンダーの対応表を消す
function cleanup_(P, props, today) {
  if (props.n_cleaned === today) return;
  const lim = ymdJst_(new Date(dateOf_(today).getTime() - 3 * 86400000));
  Object.keys(props).forEach(k => {
    if (k.indexOf('n_') === 0 && props[k] < lim) { P.deleteProperty(k); delete props[k]; }
    else if (k.indexOf('ev_') === 0 && k.slice(3, 11) < lim) { P.deleteProperty(k); delete props[k]; }
  });
  P.setProperty('n_cleaned', today); props.n_cleaned = today;
}
