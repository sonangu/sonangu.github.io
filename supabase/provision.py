#!/usr/bin/env python3
"""Supabase 프로젝트 프로비저닝 (Management API).

사용:
  SUPABASE_PAT=sbp_xxx python3 supabase/provision.py

하는 일:
  1) 조직 조회(없으면 생성)
  2) 무료 프로젝트 생성 (기본: leeyongseung-research / ap-northeast-2 서울)
  3) ACTIVE_HEALTHY 될 때까지 대기
  4) schema.sql, seed.sql 실행
  5) anon / service_role 키 조회
  6) 관리자 auth 계정 생성 + public.admins 등록
  7) data/supabase.json, tmp/supabase-notes.md 기록
"""
import json, os, sys, time, urllib.request, urllib.error, pathlib, secrets, string

API = "https://api.supabase.com/v1"
PAT = os.environ.get("SUPABASE_PAT", "").strip()
HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent
PROJECT_NAME = os.environ.get("PROJECT_NAME", "leeyongseung-research")
REGION = os.environ.get("REGION", "ap-northeast-2")
ADMIN_EMAIL = "yiyongseung@gmail.com"
DB_PASS = os.environ.get("DB_PASS") or ("".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(24)))
ADMIN_PASS = os.environ.get("ADMIN_PASS") or ("".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(14)) + "!")

if not PAT:
    sys.exit("SUPABASE_PAT 환경변수가 필요합니다.")


def call(method, path, body=None, token=None, base=API, timeout=120):
    url = base + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + (token or PAT))
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "pickle-site-provision/1.0")
    if base != API:
        req.add_header("apikey", token or PAT)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw.strip() else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw
        return e.code, parsed


def must(status, obj, what):
    if status >= 300:
        raise SystemExit(f"{what} 실패 ({status}): {obj}")
    return obj


state_path = HERE / "state.json"
state = json.loads(state_path.read_text()) if state_path.exists() else {}
state.setdefault("db_pass", DB_PASS)
state.setdefault("admin_pass", ADMIN_PASS)
DB_PASS = state["db_pass"]
ADMIN_PASS = state["admin_pass"]

# 1) 조직
orgs = must(*call("GET", "/organizations"), what="조직 조회")
orgs = orgs or []
if not orgs:
    org = must(*call("POST", "/organizations", {"name": "leeyongseung"}), what="조직 생성")
    orgs = [org]
org = orgs[0]
state["organization_id"] = org["id"]
print("organization:", org["id"], org.get("name"))

# 2) 기존 프로젝트 확인
projects = must(*call("GET", "/projects"), what="프로젝트 목록") or []
mine = [p for p in projects if p.get("name") == PROJECT_NAME]
if mine:
    proj = mine[0]
    print("existing project:", proj["id"], proj.get("status"))
else:
    proj = must(*call("POST", "/projects", {
        "organization_id": org["id"],
        "name": PROJECT_NAME,
        "db_pass": DB_PASS,
        "region": REGION,
        "plan": "free",
    }), what="프로젝트 생성")
    print("created project:", proj["id"], proj.get("status"))

ref = proj["id"]
state["ref"] = ref
state_path.write_text(json.dumps(state, indent=1))

# 3) 상태 대기
deadline = time.time() + 300
while time.time() < deadline:
    st, info = call("GET", f"/projects/{ref}")
    status = (info or {}).get("status") if isinstance(info, dict) else None
    print("  status:", status)
    if status in ("ACTIVE_HEALTHY", "ACTIVE"):
        break
    if status in ("INIT_FAILED", "INACTIVE"):
        raise SystemExit(f"프로젝트 생성 실패 상태: {info}")
    time.sleep(10)
else:
    print("경고: 5분 안에 ACTIVE 상태가 되지 않았습니다. 계속 진행합니다.")

def run_sql(sql, label):
    st, res = call("POST", f"/projects/{ref}/database/query", {"query": sql}, timeout=180)
    if st >= 300:
        raise SystemExit(f"{label} SQL 실패 ({st}): {res}")
    print(f"{label}: ok")
    return res

# 4) 스키마 · 데이터
run_sql((HERE / "schema.sql").read_text(), "schema")
run_sql((HERE / "seed.sql").read_text(), "seed")

# 5) API 키
keys = must(*call("GET", f"/projects/{ref}/api-keys?reveal=true"), what="API 키 조회")
km = {k.get("name"): k.get("api_key") for k in (keys or [])}
anon = km.get("anon") or km.get("anon key")
service = km.get("service_role") or km.get("service_role key")
if not anon:
    raise SystemExit(f"anon 키를 찾지 못했습니다: {keys}")
state["anon_key"] = anon
state["service_key"] = service
state["url"] = f"https://{ref}.supabase.co"
state_path.write_text(json.dumps(state, indent=1))

# 6) 관리자 auth 계정
base = f"https://{ref}.supabase.co"
st, res = call("PUT", f"/projects/{ref}/config/auth",
               {"disable_signup": True, "site_url": "https://leeyongseung.surge.sh",
                "mailer_autoconfirm": True}, timeout=60)
print("auth 설정:", st, res if st >= 300 else "ok")
st, res = call("POST", "/auth/v1/admin/users",
               {"email": ADMIN_EMAIL, "password": ADMIN_PASS, "email_confirm": True},
               token=service, base=base)
if st >= 300:
    print("auth 사용자 생성 결과:", st, res)
else:
    print("auth 사용자 생성:", res.get("id"))

run_sql("insert into public.admins (email, name) values "
        f"('{ADMIN_EMAIL}', '이용승') on conflict (email) do nothing;", "admin 등록")
run_sql("select table_name, (select count(*) from public.publications) as pubs, "
        "(select count(*) from public.books) as books, "
        "(select count(*) from public.courses) as courses, "
        "(select count(*) from public.admins) as admins from information_schema.tables "
        "where table_schema='public' and table_name='publications';", "검증")

# 7) 사이트 설정 저장
(SITE / "data" / "supabase.json").write_text(json.dumps(
    {"url": state["url"], "anon_key": anon}, indent=1), encoding="utf-8")

notes = SITE.parent.parent / "tmp" / "supabase-notes.md"
notes.parent.mkdir(parents=True, exist_ok=True)
notes.write_text(f"""# Supabase — 이용승 교수님 홈페이지 DB

- 대시보드 로그인: GitHub `@sonangu` (교수님이 2026-11-21 가입)
- 프로젝트: `{PROJECT_NAME}` ({ref}), 리전 `{REGION}`, 무료 플랜
- Project URL: {state['url']}
- anon(publishable) key: {anon}
- service_role key: {service}  ← 공개 금지
- DB 비밀번호: {DB_PASS}
- DB 접속: postgres://postgres.{ref}:{DB_PASS}@aws-0-{REGION}.pooler.supabase.com:5432/postgres
- 사이트 관리자 로그인: {ADMIN_EMAIL} / {ADMIN_PASS}
- Management API PAT는 교수님이 만든 것을 사용 (파일에 저장하지 않음)
""", encoding="utf-8")
print("wrote", SITE / "data" / "supabase.json")
print("url:", state["url"])
print("admin:", ADMIN_EMAIL, ADMIN_PASS)
