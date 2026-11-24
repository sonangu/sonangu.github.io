/**
 * 이용승 교수님 홈페이지 방문·다운로드 카운터
 * 시트: https://docs.google.com/spreadsheets/d/12beSAYPwUunsRVp7uX4oiqqthxd7BcHajMSMVje5pDM/edit
 *
 * 웹 앱(GET) 엔드포인트 — 배포: 실행 주체 '나', 액세스 '모든 사용자'
 *   ?action=stats                          현재 통계 { ok, visits, downloads:{key:count} }
 *   ?action=visit                          site_visits 1 증가 후 최신 통계
 *   ?action=download&key=paper:<id>:<lang> 해당 논문·판본 1 증가 후 최신 통계
 *
 * CORS 프리플라이트를 피하려고 GET 단일 엔드포인트로 만들었고,
 * 동시 요청으로 숫자가 유실되지 않게 LockService로 잠그고 있습니다.
 */

var SHEET_ID = '12beSAYPwUunsRVp7uX4oiqqthxd7BcHajMSMVje5pDM';
var COUNTERS = 'Counters';
var DAILY = 'DailyLog';
var TZ = 'Asia/Seoul';

function doGet(e) {
  var p = (e && e.parameter) || {};
  var action = String(p.action || 'stats');
  try {
    if (action === 'stats') return json(stats('stats'));
    if (action === 'visit') return json(bump('site_visits'));
    if (action === 'download') {
      var key = String(p.key || '').trim();
      if (!/^paper:[a-z0-9_-]+:(ko|en|zh)$/.test(key)) return json({ ok: false, error: 'bad_key' });
      return json(bump(key));
    }
    return json({ ok: false, error: 'unknown_action' });
  } catch (err) {
    return json({ ok: false, error: String((err && err.message) || err) });
  }
}

function json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function countersSheet() {
  return SpreadsheetApp.openById(SHEET_ID).getSheetByName(COUNTERS);
}

function stamp() {
  return Utilities.formatDate(new Date(), TZ, 'yyyy-MM-dd HH:mm:ss');
}

function stats(action) {
  var rows = countersSheet().getDataRange().getValues();
  var visits = 0, downloads = {};
  for (var i = 1; i < rows.length; i++) {
    var key = String(rows[i][0]).trim();
    if (!key) continue;
    var n = Number(rows[i][1]) || 0;
    if (key === 'site_visits') visits = n;
    else if (key.indexOf('paper:') === 0) downloads[key] = n;
  }
  return { ok: true, action: action || 'stats', visits: visits, downloads: downloads, updated_at: stamp() };
}

function bump(key) {
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  var count = 0;
  try {
    var sh = countersSheet();
    var values = sh.getDataRange().getValues();
    var row = 0;
    for (var i = 1; i < values.length; i++) {
      if (String(values[i][0]).trim() === key) {
        row = i + 1;
        count = Number(values[i][1]) || 0;
        break;
      }
    }
    count = count + 1;
    if (row > 0) sh.getRange(row, 2, 1, 2).setValues([[count, stamp()]]);
    else sh.appendRow([key, count, stamp()]);
    logDaily(key);
  } finally {
    lock.releaseLock();
  }
  var out = stats(key === 'site_visits' ? 'visit' : 'download');
  out.key = key;
  out.count = count;
  return out;
}

/** 날짜 셀이 날짜형·숫자·문자열 어느 쪽으로 저장돼도 yyyy-MM-dd로 맞춘다 */
function dateKey(v) {
  if (v === null || v === '') return '';
  if (Object.prototype.toString.call(v) === '[object Date]') {
    return Utilities.formatDate(new Date(v.getTime()), TZ, 'yyyy-MM-dd');
  }
  if (typeof v === 'number') {
    return Utilities.formatDate(new Date(Math.round((v - 25569) * 86400000)), 'UTC', 'yyyy-MM-dd');
  }
  var s = String(v).trim();
  var digits = '';
  for (var i = 0; i < s.length; i++) {
    var c = s.charAt(i);
    if (c >= '0' && c <= '9') digits += c;
  }
  if (digits.length >= 8) return digits.slice(0, 4) + '-' + digits.slice(4, 6) + '-' + digits.slice(6, 8);
  return '';
}

/** DailyLog: 하루 한 줄(date · site_visits · downloads · updated_at · note)에 누적 */
function logDaily(key) {
  var sh = SpreadsheetApp.openById(SHEET_ID).getSheetByName(DAILY);
  if (!sh) return;
  var today = Utilities.formatDate(new Date(), TZ, 'yyyy-MM-dd');
  var values = sh.getDataRange().getValues();
  var row = 0, visits = 0, dls = 0;
  for (var i = 1; i < values.length; i++) {
    if (dateKey(values[i][0]) === today) {
      row = i + 1;
      visits = Number(values[i][1]) || 0;
      dls = Number(values[i][2]) || 0;
      break;
    }
  }
  if (key === 'site_visits') visits++; else dls++;
  if (row > 0) {
    sh.getRange(row, 2, 1, 3).setValues([[visits, dls, stamp()]]);
  } else {
    // 새 줄의 날짜 칸은 텍스트로 고정해 시트가 날짜로 바꿔 읽지 않게 한다
    var next = sh.getLastRow() + 1;
    sh.getRange(next, 1).setNumberFormat('@');
    sh.getRange(next, 1, 1, 5).setValues([[today, visits, dls, stamp(), '']]);
  }
}
