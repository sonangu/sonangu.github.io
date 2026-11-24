#!/usr/bin/env python3
"""data/publications.json + tmp/teach.json -> supabase/seed.sql"""
import json, pathlib

base = pathlib.Path(__file__).parent.parent
data = json.loads((base / "data" / "publications.json").read_text(encoding="utf-8"))
teach = json.loads(pathlib.Path("/workspace/tmp/teach.json").read_text(encoding="utf-8"))


def q(v):
    if v is None:
        return "null"
    if isinstance(v, int):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def arr(v):
    if not v:
        return "'{}'::text[]"
    return "array[" + ",".join(q(x) for x in v) + "]::text[]"


def cols(vals, keys):
    return ", ".join(vals.get(k) and q(vals.get(k)) or "null" for k in keys)


PUB_COLS = ["id", "year", "month", "kind", "grade", "t", "te", "a", "v", "ve", "vol",
            "pages", "doi", "kci", "dbpia", "isbn", "abs", "langs"]

lines = ["-- 자동 생성: data/publications.json + 강의 6과목 (2026-11-21)", "begin;", ""]

def pub_row(p):
    vals = {
        "id": p["id"], "year": p["year"], "month": p.get("month"), "kind": p["kind"],
        "grade": p.get("grade"), "t": p.get("t"), "te": p.get("te"),
        "a": p.get("a"), "v": p.get("v"), "ve": p.get("ve"), "vol": p.get("vol"),
        "pages": p.get("pages"), "doi": p.get("doi"), "kci": p.get("kci"),
        "dbpia": p.get("dbpia"), "isbn": p.get("isbn"), "abs": p.get("abs"),
        "langs": p.get("langs") or ["ko"],
    }
    out = []
    for k in PUB_COLS:
        v = vals[k]
        out.append(arr(v) if k in ("a", "langs") else q(v))
    return "(" + ", ".join(out) + ")"

pubs = [p for p in data["items"] if p["kind"] != "book"]
books = [p for p in data["items"] if p["kind"] == "book"]

lines.append("insert into public.publications (" + ", ".join(PUB_COLS) + ") values")
lines.append(",\n".join(pub_row(p) for p in pubs))
lines.append("on conflict (id) do nothing;")
lines.append("")

BOOK_COLS = ["id", "year", "month", "grade", "t", "te", "a", "v", "ve", "vol", "pages", "isbn", "abs", "langs"]
def book_row(p):
    vals = {
        "id": p["id"], "year": p["year"], "month": p.get("month"), "grade": p.get("grade"),
        "t": p.get("t"), "te": p.get("te"), "a": p.get("a"), "v": p.get("v"), "ve": p.get("ve"),
        "vol": p.get("vol"), "pages": p.get("pages"), "isbn": p.get("isbn"),
        "abs": p.get("abs"), "langs": p.get("langs") or ["ko"],
    }
    out = []
    for k in BOOK_COLS:
        v = vals[k]
        out.append(arr(v) if k in ("a", "langs") else q(v))
    return "(" + ", ".join(out) + ")"

lines.append("insert into public.books (" + ", ".join(BOOK_COLS) + ") values")
lines.append(",\n".join(book_row(p) for p in books))
lines.append("on conflict (id) do nothing;")
lines.append("")

COURSE_COLS = ["sort", "t_ko", "k_ko", "d_ko", "t_en", "k_en", "d_en", "t_zh", "k_zh", "d_zh"]
rows = []
for i, c in enumerate(teach):
    ko, en, zh = c.get("ko", {}), c.get("en", {}), c.get("zh", {})
    rows.append("(" + ", ".join([
        q(i), q(ko.get("t")), q(ko.get("k")), q(ko.get("d")),
        q(en.get("t")), q(en.get("k")), q(en.get("d")),
        q(zh.get("t")), q(zh.get("k")), q(zh.get("d")),
    ]) + ")")
lines.append("insert into public.courses (" + ", ".join(COURSE_COLS) + ") values")
lines.append(",\n".join(rows) + ";")
lines.append("")
lines.append("commit;")

out = pathlib.Path(__file__).parent / "seed.sql"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"wrote {out} — {len(pubs)} publications, {len(books)} books, {len(teach)} courses, {out.stat().st_size} bytes")
