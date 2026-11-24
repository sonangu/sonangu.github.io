#!/usr/bin/env python3
"""Build sites/leeyongseung/index.html from index.template.html + data/publications.json

정적 사이트입니다. (Supabase 연동은 2026-11-21 취소되어 코드에서 제거됨)
"""
import json, pathlib

base = pathlib.Path(__file__).parent
data = json.loads((base / "data" / "publications.json").read_text(encoding="utf-8"))
tpl = (base / "index.template.html").read_text(encoding="utf-8")
js = json.dumps({"items": data["items"]}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

out = tpl.replace("__DATA__", js)
(base / "index.html").write_text(out, encoding="utf-8")
arts = [p for p in data["items"] if p["kind"] == "article"]
books = [p for p in data["items"] if p["kind"] == "book"]
print(f"built index.html ({len(out.encode())} bytes) — {len(arts)} articles, {len(books)} books")
