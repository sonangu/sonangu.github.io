#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""이용승 교수 홈페이지 정적 빌드.

    1) index.template.html + data/publications.json  →  index.html
    2) 논문·이슈브리프·저서마다 개별 페이지           →  p/{id}.html  (+ 공용 스타일 p/detail.css)
    3) curation.template.html + data/curations.json   →  curation.html (추천 글 · 큐레이션)
    4) 메인 + 앱 3개 + 추천 글 + 개별 페이지 전부      →  sitemap.xml

정적 사이트입니다. (Supabase 연동은 2026-11-21 취소되어 코드에서 제거됨)

추천 글 항목(data/curations.json의 items 배열) 한 항목의 형식:
    {
      "id": "slug",                       # 카드 앵커(선택)
      "date": "2026-11-26",               # 게시·선별 날짜(정렬 기준, 최신이 위)
      "title": {"ko": "…", "en": "…", "zh": "…"},   # 문자열 한 개만 줘도 됨
      "source": "출처 매체·블로그",
      "author": "저자(선택)",
      "url": "https://…",                 # 원문 바로가기
      "quote": {"ko": "…"},              # Glasp 하이라이트 인용(선택)
      "note":  {"ko": "…"},              # 교수님 한 줄 평
      "lang": "ko",                       # 원문 언어 배지(선택)
      "tags": ["다문화주의"]              # 주제 칩(선택)
    }
"""
import datetime
import html as htmllib
import json
import pathlib
import re

BASE = pathlib.Path(__file__).parent
SITE = "https://yslee.pe.kr"
KST = datetime.timezone(datetime.timedelta(hours=9))
TODAY = datetime.datetime.now(KST).strftime("%Y-%m-%d")

STATS_API = ("https://script.google.com/macros/s/"
             "AKfycbwlbVkWp7bvusaxoPKDwKhcPy60jMCJdYJckjJzIIs96UgjEZZMu4ZRg68uqQgHNY5O/exec")

APPS = [
    ("apps/big-concept-compass.html", "0.7"),
    ("apps/power-duty-freedom.html", "0.7"),
    ("apps/what-is-justice.html", "0.7"),
]

GRADE_EN = {
    "KCI 등재": "KCI-indexed", "KCI 등재후보": "KCI candidate", "일반논문": "Article",
    "국제학술지": "International journal", "저서(공저)": "Co-authored book",
    "교재(공저)": "Co-authored textbook", "이슈브리프": "Issue brief",
}

# 개별 페이지 메타 키워드용 주제 사전 — 제목·초록에 실제로 나오는 말만 붙인다.
TOPIC_MAP = [
    ("다문화수용성", "다문화 수용성"),
    ("수용성", "다문화 수용성"),
    ("다문화", "다문화주의"),
    ("이민", "이민정책"),
    ("이주", "이주·이민"),
    ("통합", "사회통합"),
    ("시민권", "시민권"),
    ("주민권", "주민권"),
    ("성원", "성원권"),
    ("난민", "난민"),
    ("민족", "민족주의"),
    ("유학생", "유학생"),
    ("가짜뉴스", "가짜뉴스"),
    ("안보", "인간안보"),
    ("정의", "정의란 무엇인가"),
    ("권력", "권력·의무·자유"),
    ("빅컨셉", "빅컨셉"),
    ("교육", "다문화교육"),
    ("한국어", "한국어교육"),
    ("미국", "미국 이민정책"),
    ("호주", "호주 다문화주의"),
    ("퀘벡", "퀘벡"),
    ("사드", "사드"),
    ("정치", "정치"),
    ("폭력", "폭력"),
    ("윤리", "시민윤리"),
    ("공존", "공존"),
]

KIND_KO = {"article": "논문", "brief": "이슈브리프", "book": "저서"}
KIND_ZH = {"article": "论文", "brief": "议题简报", "book": "著作"}


def esc(s):
    return htmllib.escape("" if s is None else str(s), quote=True)


def cite_of(p):
    """메인 페이지 citationOf()와 같은 규칙으로 만든 인용 문구."""
    authors = ", ".join(p.get("a") or [])
    out = "%s (%s). " % (authors, p["year"])
    if p.get("kind") == "book":
        out += "『%s』. %s" % (p["t"], p.get("v") or "")
        if p.get("vol"):
            out += ", %s" % p["vol"]
        out += "."
        if p.get("isbn"):
            out += " ISBN %s." % p["isbn"]
    elif p.get("kind") == "brief":
        out += "%s. %s" % (p["t"], p.get("v") or "")
        if p.get("vol"):
            out += " %s" % p["vol"]
        out += "."
        if p.get("doi"):
            out += " https://doi.org/%s" % p["doi"]
    else:
        out += "%s. %s" % (p["t"], p.get("v") or "")
        if p.get("vol"):
            vol = p["vol"] if "(" in p["vol"] else "(%s)" % p["vol"]
            out += ", %s" % vol
        if p.get("pages"):
            out += ", %s" % re.sub(r"[–—]", "-", p["pages"])
        out += "."
        if p.get("doi"):
            out += " https://doi.org/%s" % p["doi"]
    return re.sub(r"\s+", " ", out).strip()


def topic_tags(p):
    hay = " ".join([p.get("t") or "", p.get("te") or "", p.get("tz") or "",
                    p.get("abs") or "", p.get("absEn") or ""])
    tags = []
    for trig, kw in TOPIC_MAP:
        if trig in hay and kw not in tags:
            tags.append(kw)
    return tags[:6]


def keywords_of(p):
    words = ["이용승", "이용승 교수", "대구대학교 이용승", p["t"]]
    if p.get("v"):
        words.append(p["v"])
    words += topic_tags(p)
    seen, out = set(), []
    for w in words:
        if w and w not in seen:
            seen.add(w)
            out.append(w)
    return ", ".join(out)


def desc_of(p):
    raw = re.sub(r"\s+", " ", (p.get("abs") or p.get("absEn") or "")).strip()
    if raw:
        if len(raw) <= 150:
            return raw
        cut = raw[:150]
        ends = list(re.finditer(r"[.?!。？！]", cut))
        if ends and ends[-1].end() > 60:
            return cut[:ends[-1].end()]
        return cut.rstrip() + "…"
    authors = ", ".join(p.get("a") or [])
    bits = [p["t"]]
    if authors:
        bits.append(authors)
    bits.append("%s년" % p["year"])
    if p.get("v"):
        bits.append(p["v"])
    return " · ".join(bits) + " — 이용승 교수(대구대학교 자유전공학부) %s." % KIND_KO.get(p["kind"], "글")


def pdf_entries(p):
    """(언어코드, href, 버튼 라벨, 집계 키) 목록."""
    out = []
    if p.get("pdf"):
        label = p.get("pdfKoLabel") or ("한국어판 PDF" if p.get("pdfKoTrans") else "원문 PDF")
        out.append(("ko", p["pdf"], label, "paper:%s:ko" % p["id"]))
    if p.get("pdfEn"):
        label = "영문 원문 PDF" if p.get("pdfEnOriginal") else "영문판 PDF"
        out.append(("en", p["pdfEn"], label, "paper:%s:en" % p["id"]))
    if p.get("pdfZh"):
        out.append(("zh", p["pdfZh"], "중문판 PDF", "paper:%s:zh" % p["id"]))
    return out


def ld_json(p, url):
    tags = topic_tags(p)
    authors = []
    for a in (p.get("a") or []):
        if "이용승" in a:
            authors.append({"@type": "Person", "name": "이용승", "alternateName": "Yongseung Lee",
                            "@id": SITE + "/#person"})
        else:
            authors.append({"@type": "Person", "name": a})
    pub = {"@type": "Organization", "name": p.get("v") or "대구대학교"}
    enc = []
    for code, href, label, key in pdf_entries(p):
        enc.append({
            "@type": "MediaObject",
            "name": label,
            "contentUrl": SITE + "/" + href,
            "fileFormat": "application/pdf",
            "inLanguage": code,
        })
    node = {
        "@type": "Book" if p.get("kind") == "book" else "ScholarlyArticle",
        "@id": url + "#publication",
        "name": p["t"],
        "headline": p["t"],
        "url": url,
        "mainEntityOfPage": url,
        "inLanguage": "ko",
        "author": authors,
        "publisher": pub,
        "datePublished": "%s-%02d" % (p["year"], p["month"]) if p.get("month") else str(p["year"]),
        "keywords": tags,
    }
    alt = [x for x in (p.get("te"), p.get("tz")) if x]
    if alt:
        node["alternateName"] = alt
    if p.get("abs"):
        node["abstract"] = p["abs"]
    elif p.get("absEn"):
        node["abstract"] = p["absEn"]
    if p.get("kind") == "book":
        node["bookFormat"] = "https://schema.org/Paperback"
        if p.get("isbn"):
            node["isbn"] = p["isbn"]
        if p.get("pages"):
            node["numberOfPages"] = re.sub(r"[^0-9]", "", p["pages"]) or None
            if not node["numberOfPages"]:
                del node["numberOfPages"]
    else:
        node["isPartOf"] = {"@type": "Periodical", "name": p.get("v") or "",
                            "alternateName": p.get("ve") or p.get("v") or ""}
        if p.get("vol"):
            node["volumeNumber"] = p["vol"]
        if p.get("pages"):
            node["pagination"] = re.sub(r"[–—]", "-", p["pages"])
    ident = []
    if p.get("doi"):
        ident.append({"@type": "PropertyValue", "propertyID": "DOI", "value": p["doi"]})
    if p.get("kci"):
        ident.append({"@type": "PropertyValue", "propertyID": "KCI", "value": p["kci"]})
    if p.get("isbn"):
        ident.append({"@type": "PropertyValue", "propertyID": "ISBN", "value": p["isbn"]})
    if ident:
        node["identifier"] = ident
    same = []
    if p.get("doi"):
        same.append("https://doi.org/" + p["doi"])
    if p.get("kci"):
        same.append("https://www.kci.go.kr/kciportal/ci/sereArticleSearch/"
                    "ciSereArtiView.kci?sereArticleSearchBean.artiId=" + p["kci"])
    if same:
        node["sameAs"] = same
    if enc:
        node["encoding"] = enc
    graph = [node, {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "이용승 교수 홈페이지", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": p["t"], "item": url},
        ],
    }]
    out = {"@context": "https://schema.org", "@graph": graph}
    return json.dumps(out, ensure_ascii=False, indent=2).replace("</", "<\\/")


def related_items(p, items, n=4):
    me = set(topic_tags(p))
    scored = []
    for q in items:
        if q["id"] == p["id"]:
            continue
        shared = len(me & set(topic_tags(q)))
        scored.append((-shared, abs(q["year"] - p["year"]), -q["year"], q))
    scored.sort(key=lambda x: x[:3])
    return [x[3] for x in scored[:n]]


DETAIL_CSS = """/* 이용승 교수 홈페이지 — 논문·저서 개별 페이지 (build.py가 p/detail.css로 생성) */
:root{
  --bg:#FAF8F5; --surface:#FFFFFF; --ink:#22262A; --ink-2:#4A5057; --muted:#7E7A73;
  --line:#E8E1D6; --line-soft:#F0EAE1; --sage:#5F7767; --sage-2:#7C9484; --sage-soft:#EDF1EC;
  --terra:#A9613F; --terra-soft:#F8EEE7; --gold:#C0A16B;
  --shadow:0 1px 2px rgba(52,44,34,.04), 0 8px 24px rgba(52,44,34,.05);
  --max:820px;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0; background:var(--bg); color:var(--ink); line-height:1.78; letter-spacing:-.01em;
  font-family:"Noto Sans KR","Noto Sans SC",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  background-image:radial-gradient(1200px 600px at 78% -10%, #F3EDE2 0%, rgba(243,237,226,0) 60%),
                   radial-gradient(900px 500px at 6% 8%, #EFF3EE 0%, rgba(239,243,238,0) 55%);
  background-repeat:no-repeat;
}
h1,h2,h3{font-family:"Noto Serif KR","Noto Serif SC",Georgia,"Times New Roman",serif; font-weight:600; letter-spacing:-.02em}
a{color:inherit; text-decoration:none}
p{margin:0 0 1em}
.wrap{max-width:var(--max); margin:0 auto; padding:0 24px}
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}

.topbar{border-bottom:1px solid var(--line-soft); background:rgba(250,248,245,.9)}
.topbar .wrap{display:flex; align-items:center; gap:16px; min-height:62px; flex-wrap:wrap; padding-top:8px; padding-bottom:8px}
.brand{font-family:"Noto Serif KR",Georgia,serif; font-size:18px; font-weight:600; white-space:nowrap}
.brand span{font-family:"Noto Sans KR",sans-serif; font-size:10.5px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); font-weight:500; margin-left:8px}
.topnav{margin-left:auto; display:flex; gap:14px; font-size:12.5px; color:var(--muted)}
.topnav a:hover{color:var(--sage)}

main{padding:44px 0 16px}
.pills{display:flex; flex-wrap:wrap; gap:7px; margin-bottom:16px}
.pill{font-size:11.5px; letter-spacing:.05em; padding:3px 10px; border-radius:999px; border:1px solid var(--line); color:var(--muted); background:var(--surface)}
.pill.grade{background:var(--sage-soft); border-color:#DCE5DC; color:#48604F}
.pill.kind{background:var(--terra-soft); border-color:#EFDDD2; color:#7A4630}
h1{font-size:clamp(24px,4vw,35px); line-height:1.42; margin:0 0 10px; word-break:keep-all}
.t-sub{margin:0 0 5px; font-size:15px; color:var(--muted); line-height:1.62; word-break:keep-all}
.t-sub.zh{font-size:14.5px}
.byline{margin:20px 0 0; padding-top:15px; border-top:1px solid var(--line-soft); font-size:14px; color:var(--ink-2); word-break:keep-all}
.byline .me{font-weight:600; color:var(--ink); border-bottom:1.5px solid #D9D0BE}
.byline em{font-style:normal; color:var(--muted)}

.acts{display:flex; flex-wrap:wrap; gap:9px; margin:22px 0 8px; align-items:center}
a.pdflink, button.citebtn, a.ghostbtn{
  display:inline-flex; align-items:center; gap:6px; border:1px solid var(--line); background:#fff;
  border-radius:999px; padding:6px 13px 6px 8px; font:inherit; font-size:12.8px; font-weight:500;
  color:var(--ink-2); cursor:pointer; transition:background .16s ease,border-color .16s ease,color .16s ease;
}
a.pdflink .tagpdf{font-size:10px; letter-spacing:.06em; font-weight:700; color:var(--sage); background:var(--sage-soft); border-radius:4px; padding:1px 5px}
a.pdflink:hover, button.citebtn:hover, a.ghostbtn:hover{border-color:var(--sage-2); background:var(--sage-soft); color:var(--sage)}
button.citebtn svg, a.ghostbtn svg{width:12px; height:12px; stroke:currentColor; fill:none; stroke-width:1.7}
button.citebtn.done{background:var(--sage); border-color:var(--sage); color:#fff}
.pcount{font-size:10.5px; font-weight:600; color:var(--muted); border-left:1px solid var(--line); padding-left:6px; margin-left:1px; min-width:12px; text-align:center}
.soon{display:inline-flex; align-items:center; font-size:12.5px; color:var(--muted); border:1px dashed var(--line); border-radius:999px; padding:5px 12px}

.block{margin:34px 0 0}
.block h2{font-size:15px; letter-spacing:.02em; margin:0 0 12px; color:var(--ink); display:flex; align-items:center; gap:10px}
.block h2::before{content:""; width:22px; height:1px; background:var(--sage-2); display:inline-block}
.abs{background:#FCFAF6; border-left:2px solid #DCD3C3; padding:14px 18px; font-size:14.5px; color:var(--ink-2); word-break:keep-all}
.abs p:last-child{margin-bottom:0}
.abs .lbl{display:block; font-size:10.5px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); font-weight:600; margin-bottom:7px}
.note{font-size:13.5px; color:var(--muted); margin:0}
dl.facts{margin:0; display:grid; gap:0; font-size:13.8px; color:var(--ink-2)}
dl.facts div{display:grid; grid-template-columns:110px 1fr; gap:14px; padding:9px 0; border-top:1px solid var(--line-soft)}
dl.facts div:first-child{border-top:0}
dl.facts dt{font-size:11px; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); padding-top:3px}
dl.facts dd{margin:0; word-break:keep-all}
dl.facts a{color:var(--sage); border-bottom:1px solid rgba(95,119,103,.28)}
dl.facts a:hover{color:var(--terra)}

.also{list-style:none; margin:0; padding:0; border-top:1px solid var(--line)}
.also li{padding:13px 0; border-bottom:1px solid var(--line-soft)}
.also a{display:block}
.also .t{font-size:14.5px; color:var(--ink); line-height:1.55; word-break:keep-all}
.also .m{font-size:12px; color:var(--muted); margin-top:3px}
.also a:hover .t{color:var(--sage)}

.author{margin:38px 0 0; padding:20px 22px; background:var(--surface); border:1px solid var(--line); border-radius:14px; box-shadow:var(--shadow); display:flex; gap:16px; align-items:flex-start}
.author img{width:56px; height:56px; border-radius:50%; object-fit:cover; object-position:center 30%; border:1px solid var(--line); flex:none}
.author p{margin:0; font-size:13px; color:var(--ink-2); line-height:1.7}
.author b{display:block; font-family:"Noto Serif KR",Georgia,serif; font-size:15px; color:var(--ink); margin-bottom:2px}
.author a{color:var(--sage); border-bottom:1px solid rgba(95,119,103,.28)}

.backrow{margin:30px 0 10px}
a.backbtn{display:inline-flex; align-items:center; gap:8px; font-size:13.5px; color:#fff; background:var(--sage); border-radius:999px; padding:10px 20px}
a.backbtn:hover{background:#4F6557}
footer{border-top:1px solid var(--line); margin-top:34px; padding:26px 0 44px; font-size:12px; color:var(--muted)}
footer .wrap{display:flex; flex-wrap:wrap; gap:8px 20px; justify-content:space-between}
footer a:hover{color:var(--sage)}

.toast{position:fixed; left:50%; bottom:28px; transform:translate(-50%,16px); background:#2E332F; color:#F6F2EA; font-size:13.5px; padding:12px 18px; border-radius:999px; box-shadow:0 10px 30px rgba(0,0,0,.18); opacity:0; pointer-events:none; transition:.22s ease; z-index:100; max-width:min(92vw,560px); text-align:center}
.toast.on{opacity:1; transform:translate(-50%,0)}

@media (max-width:640px){
  main{padding:30px 0 10px}
  .brand span{display:none}
  .topnav{gap:10px; font-size:12px; width:100%; margin-left:0}
  dl.facts div{grid-template-columns:1fr; gap:2px}
  .author{flex-direction:row}
}
@media print{
  .topbar,.acts,.backrow,footer,.toast{display:none !important}
  body{background:#fff}
}
"""

DETAIL_TPL = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%%TITLE%%</title>
<meta name="description" content="%%DESC%%">
<meta name="keywords" content="%%KEYWORDS%%">
<meta name="author" content="%%AUTHOR%%">
<meta name="robots" content="index,follow">
<link rel="canonical" href="%%URL%%">
<meta property="og:type" content="%%OGTYPE%%">
<meta property="og:site_name" content="이용승 교수 홈페이지">
<meta property="og:url" content="%%URL%%">
<meta property="og:title" content="%%TITLE%%">
<meta property="og:description" content="%%DESC%%">
<meta property="og:image" content="https://yslee.pe.kr/assets/profile-hero.jpg">
<meta property="og:locale" content="ko_KR">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="%%TITLE%%">
<meta name="twitter:description" content="%%DESC%%">
<meta name="twitter:image" content="https://yslee.pe.kr/assets/profile-hero.jpg">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%236E8574'/%3E%3Ctext x='32' y='45' font-family='Georgia,serif' font-size='34' fill='%23FAF8F5' text-anchor='middle'%3E이%3C/text%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&family=Noto+Serif+KR:wght@400;500;600;700&family=Noto+Serif+SC:wght@400;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="detail.css">
<script type="application/ld+json">
%%LD%%
</script>
</head>
<body>

<header class="topbar">
  <div class="wrap">
    <a class="brand" href="../index.html">이용승 <span>Lee, Yongseung</span></a>
    <nav class="topnav" aria-label="바로가기">
      <a href="../index.html">홈</a>
      <a href="../index.html#pubs">논문 목록</a>
      <a href="../curation.html">추천 글</a>
      <a href="../index.html#apps">연구 App</a>
      <a href="../index.html#contact">연락처</a>
    </nav>
  </div>
</header>

<main>
  <article class="wrap">
    <div class="pills">
      <span class="pill kind">%%KIND%%</span>
      <span class="pill">%%YEAR%%</span>
      %%GRADEPILL%%
    </div>
    <h1>%%H1%%</h1>
    %%SUBTITLES%%
    <p class="byline">%%BYLINE%%</p>

    <div class="acts">
      %%ACTIONS%%
      <button type="button" class="citebtn" data-copy="%%CITATION%%" title="인용 문구 복사">
        <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M15 5H6a2 2 0 0 0-2 2v9"/></svg>
        <span class="clabel">인용 복사</span>
      </button>
    </div>

    <section class="block" aria-labelledby="abs-h">
      <h2 id="abs-h">초록</h2>
      %%ABSTRACT%%
    </section>

    <section class="block" aria-labelledby="facts-h">
      <h2 id="facts-h">서지 정보</h2>
      %%FACTS%%
    </section>

    %%ALSO%%

    <div class="author">
      <img src="../assets/profile-hero.jpg" width="56" height="56" alt="이용승 교수" loading="lazy">
      <p>
        <b>이용승 (李容承, Yongseung Lee)</b>
        대구대학교 자유전공학부 부교수 · 정치학 박사. 이주와 이민정책, 다문화주의와 다문화 수용성, 사회통합과 성원권, 민족주의를 연구합니다.
        <a href="../index.html#about">소개 보기 →</a>
      </p>
    </div>

    <div class="backrow">
      <a class="backbtn" href="../index.html#pubs">← 이용승 교수 홈페이지로 돌아가기</a>
    </div>
  </article>
</main>

<footer>
  <div class="wrap">
    <span>© 2026 이용승 · 대구대학교 자유전공학부</span>
    <span>서지 정보: KCI · DBpia, 저자 제공 목록</span>
    <a href="https://yslee.pe.kr/">yslee.pe.kr</a>
  </div>
</footer>

<div class="toast" id="toast" role="status" aria-live="polite"></div>

<script>
(function(){
  var API = '%%STATS_API%%';
  var el = document.getElementById('toast'), tm;
  function toast(m){ el.textContent = m; el.classList.add('on'); clearTimeout(tm); tm = setTimeout(function(){ el.classList.remove('on'); }, 3200); }

  function fmt(n){ try{ return Number(n).toLocaleString('ko-KR'); }catch(e){ return String(n); } }
  function fill(d){
    if(!d || !d.downloads) return;
    document.querySelectorAll('[data-dlcount]').forEach(function(s){
      var n = d.downloads[s.getAttribute('data-dlcount')];
      if(typeof n === 'number') s.textContent = fmt(n);
    });
  }
  fetch(API + '?action=stats', {cache:'no-store'})
    .then(function(r){ return r.json(); }).then(fill).catch(function(){});

  /* PDF를 열면 메인 페이지와 같은 키로 다운로드를 센다 */
  document.addEventListener('click', function(e){
    var a = e.target.closest ? e.target.closest('[data-dlkey]') : null;
    if(!a) return;
    var k = a.getAttribute('data-dlkey');
    if(!k) return;
    var s = a.querySelector('[data-dlcount]');
    if(s && s.textContent !== '–'){ s.textContent = fmt((Number(String(s.textContent).replace(/[^0-9]/g,''))||0) + 1); }
    fetch(API + '?action=download&key=' + encodeURIComponent(k), {keepalive:true})
      .then(function(r){ return r.json(); }).then(fill).catch(function(){});
  });

  /* 인용 복사 */
  document.querySelectorAll('[data-copy]').forEach(function(b){
    b.addEventListener('click', function(){
      var text = b.getAttribute('data-copy');
      var label = b.querySelector('.clabel');
      function done(ok){
        if(!ok){ toast('복사하지 못했습니다. 다시 눌러 주세요.'); return; }
        b.classList.add('done');
        if(label) label.textContent = '✓ 복사됨';
        toast('✓ 인용 문구를 복사했습니다');
        setTimeout(function(){ b.classList.remove('done'); if(label) label.textContent = '인용 복사'; }, 1800);
      }
      if(navigator.clipboard && navigator.clipboard.writeText){
        navigator.clipboard.writeText(text).then(function(){ done(true); }).catch(function(){ done(false); });
      } else {
        try{
          var ta = document.createElement('textarea');
          ta.value = text; ta.setAttribute('readonly','');
          ta.style.position='fixed'; ta.style.top='-1000px';
          document.body.appendChild(ta); ta.select();
          var ok = document.execCommand('copy');
          document.body.removeChild(ta);
          done(ok);
        }catch(err){ done(false); }
      }
    });
  });
})();
</script>
</body>
</html>
"""


def detail_page(p, items):
    url = "%s/p/%s.html" % (SITE, p["id"])
    kind = KIND_KO.get(p["kind"], "글")
    title = "%s — 이용승 교수 | 대구대학교" % p["t"]
    desc = desc_of(p)

    subtitles = ""
    if p.get("te"):
        subtitles += '<p class="t-sub" lang="en">%s</p>\n    ' % esc(p["te"])
    if p.get("tz"):
        subtitles += '<p class="t-sub zh" lang="zh-Hans">%s</p>\n    ' % esc(p["tz"])

    grade_pill = ""
    if p.get("grade"):
        grade_pill = '<span class="pill grade">%s</span>' % esc(p["grade"])

    # byline
    authors = []
    for a in (p.get("a") or []):
        if "이용승" in a:
            authors.append('<span class="me">%s</span>' % esc(a))
        else:
            authors.append(esc(a))
    by = ", ".join(authors)
    venue = esc(p.get("v") or "")
    tail = []
    if p.get("vol"):
        tail.append(esc(p["vol"]))
    if p.get("pages"):
        tail.append(esc(p["pages"]))
    tail.append("%s년" % p["year"] + (" %d월" % p["month"] if p.get("month") else ""))
    byline = by + ' <em>·</em> ' + venue + (" " + ' <em>·</em> '.join(tail) if tail else "")

    # actions: PDF + 원문 링크
    acts = []
    for code, href, label, key in pdf_entries(p):
        acts.append(
            '<a class="pdflink" href="../%s" target="_blank" rel="noopener" data-dlkey="%s" '
            'title="%s 열기"><span class="tagpdf">%s</span>%s'
            '<span class="pcount" data-dlcount="%s" title="다운로드 수">–</span></a>'
            % (esc(href), esc(key), esc(label), code.upper(), esc(label), esc(key))
        )
    if not pdf_entries(p):
        acts.append('<span class="soon">PDF 준비 중</span>')
    if p.get("kci"):
        acts.append('<a class="ghostbtn" href="https://www.kci.go.kr/kciportal/ci/sereArticleSearch/'
                    'ciSereArtiView.kci?sereArticleSearchBean.artiId=%s" target="_blank" rel="noopener">'
                    'KCI 원문 <span aria-hidden="true">↗</span></a>' % esc(p["kci"]))
    if p.get("doi"):
        acts.append('<a class="ghostbtn" href="https://doi.org/%s" target="_blank" rel="noopener">'
                    'DOI <span aria-hidden="true">↗</span></a>' % esc(p["doi"]))
    if p.get("dbpia"):
        acts.append('<a class="ghostbtn" href="https://www.dbpia.co.kr/journal/articleDetail?nodeId=%s" '
                    'target="_blank" rel="noopener">DBpia <span aria-hidden="true">↗</span></a>' % esc(p["dbpia"]))

    # abstract
    if p.get("abs"):
        abstract = '<div class="abs"><span class="lbl">국문 초록</span><p>%s</p></div>' % esc(p["abs"])
    elif p.get("absEn"):
        abstract = '<div class="abs"><span class="lbl">Abstract</span><p>%s</p></div>' % esc(p["absEn"])
    else:
        head = ("이 글의 초록은 국문 원문과 KCI 서지에서 확인할 수 있습니다. " if p.get("kci")
                else "이 글의 초록은 원문 PDF에서 확인할 수 있습니다. ")
        abstract = ('<p class="note">' + head
                    + '필요하시면 <a href="mailto:leeyongseung@daegu.ac.kr">이메일</a>로 문의해 주세요.</p>')
    if p.get("abs") and p.get("absEn"):
        abstract += '<div class="abs" style="margin-top:12px"><span class="lbl">Abstract (EN)</span><p>%s</p></div>' % esc(p["absEn"])

    # facts
    rows = []
    rows.append(("저자", by))
    if p.get("kind") == "book":
        rows.append(("출판사", venue + ((" · " + esc(p["vol"])) if p.get("vol") else "")))
        if p.get("isbn"):
            rows.append(("ISBN", esc(p["isbn"])))
        if p.get("pages"):
            rows.append(("분량", esc(p["pages"])))
    else:
        rows.append(("학술지", venue + ((" " + esc(p["vol"])) if p.get("vol") else "")))
        if p.get("pages"):
            rows.append(("쪽", esc(p["pages"])))
    rows.append(("발행", "%s년%s" % (p["year"], (" %d월" % p["month"]) if p.get("month") else "")))
    if p.get("grade"):
        rows.append(("구분", esc(p["grade"])))
    if p.get("doi"):
        rows.append(("DOI", '<a href="https://doi.org/%s" target="_blank" rel="noopener">%s</a>' % (esc(p["doi"]), esc(p["doi"]))))
    if p.get("kci"):
        rows.append(("KCI", '<a href="https://www.kci.go.kr/kciportal/ci/sereArticleSearch/'
                           'ciSereArtiView.kci?sereArticleSearchBean.artiId=%s" target="_blank" rel="noopener">'
                           '%s</a>' % (esc(p["kci"]), esc(p["kci"]))))
    facts = "<dl class=\"facts\">" + "".join(
        "<div><dt>%s</dt><dd>%s</dd></div>" % (k, v) for k, v in rows) + "</dl>"

    # 함께 읽기
    also = ""
    rel = related_items(p, items)
    if rel:
        lis = "".join(
            '<li><a href="%s.html"><span class="t">%s</span>'
            '<span class="m">%s · %s · %s</span></a></li>'
            % (esc(q["id"]), esc(q["t"]), q["year"], esc(KIND_KO.get(q["kind"], "글")),
               esc(q.get("v") or ""))
            for q in rel)
        also = ('<section class="block" aria-labelledby="also-h">\n'
                '      <h2 id="also-h">함께 읽기</h2>\n'
                '      <ul class="also">%s</ul>\n'
                '    </section>' % lis)

    html = (DETAIL_TPL
            .replace("%%TITLE%%", esc(title))
            .replace("%%DESC%%", esc(desc))
            .replace("%%KEYWORDS%%", esc(keywords_of(p)))
            .replace("%%AUTHOR%%", esc(", ".join(p.get("a") or ["이용승"])))
            .replace("%%URL%%", esc(url))
            .replace("%%OGTYPE%%", "book" if p.get("kind") == "book" else "article")
            .replace("%%LD%%", ld_json(p, url))
            .replace("%%KIND%%", esc(kind))
            .replace("%%YEAR%%", esc(p["year"]))
            .replace("%%GRADEPILL%%", grade_pill)
            .replace("%%H1%%", esc(p["t"]))
            .replace("%%SUBTITLES%%", subtitles)
            .replace("%%BYLINE%%", byline)
            .replace("%%ACTIONS%%", "\n      ".join(acts))
            .replace("%%CITATION%%", esc(cite_of(p)))
            .replace("%%ABSTRACT%%", abstract)
            .replace("%%FACTS%%", facts)
            .replace("%%ALSO%%", also)
            .replace("%%STATS_API%%", STATS_API))
    return html


def quicklinks(ql):
    """data/quicklinks.json → (하단 바로가기 칩 HTML, 이름 i18n JSON 문자열).

    항목 형식: {"id": "slug", "url": "https://…",
                "name": {"ko": "…", "en": "…", "zh": "…"}}
    name은 세 언어(없는 언어는 ko로 대체). 링크가 한 줄 폭을 넘으면
    메인 페이지 스크립트가 자동으로 가로 흐름(marquee)으로 바꾼다.
    """
    items = ql.get("items") or []
    lis = []
    i18n = {k: {} for k in ("ko", "en", "zh")}
    for it in items:
        name = it.get("name") or {}
        if isinstance(name, str):
            name = {"ko": name}
        key = "ql." + it["id"]
        ko = name.get("ko") or next((v for v in name.values() if v), "")
        lis.append(
            '<li><a class="ql-chip" href="%s" target="_blank" rel="noopener noreferrer">'
            '<span data-i18n="%s">%s</span><span class="arw" aria-hidden="true">↗</span></a></li>'
            % (esc(it["url"]), esc(key), esc(ko or it["url"])))
        for lang in ("ko", "en", "zh"):
            v = name.get(lang) or ko
            if v:
                i18n[lang][key] = v
    return ("\n            ".join(lis),
            json.dumps(i18n, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))


def curation_ld(items, url):
    """추천 글 페이지용 JSON-LD — CollectionPage(+ 항목이 있으면 ItemList)."""
    page = {
        "@type": "CollectionPage",
        "@id": url,
        "url": url,
        "name": "추천 글 · 큐레이션 — 이용승 교수",
        "description": "이용승 교수가 직접 고른 추천 글과 Glasp 하이라이트 모음. 출처와 한 줄 평, 원문 링크를 함께 실었다.",
        "inLanguage": "ko",
        "isPartOf": {"@id": SITE + "/#website"},
        "about": {"@id": SITE + "/#person"},
        "mainEntity": {"@id": SITE + "/#person"},
        "breadcrumb": {"@id": url + "#breadcrumb"},
    }
    if items:
        parts = []
        for i, it in enumerate(items, 1):
            title = it.get("title")
            if isinstance(title, dict):
                title = title.get("ko") or title.get("en") or title.get("zh") or ""
            node = {"@type": "ListItem", "position": i, "name": title or ""}
            if it.get("url"):
                node["url"] = it["url"]
            parts.append(node)
        page["hasPart"] = {"@type": "ItemList", "numberOfItems": len(items),
                           "itemListElement": parts}
    graph = [page, {
        "@type": "BreadcrumbList",
        "@id": url + "#breadcrumb",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "이용승 교수 홈페이지", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "추천 글 · 큐레이션", "item": url},
        ],
    }]
    out = {"@context": "https://schema.org", "@graph": graph}
    return json.dumps(out, ensure_ascii=False, indent=2).replace("</", "<\\/")


def sitemap_xml(items):
    urls = [(SITE + "/", "1.0", "weekly"), (SITE + "/curation.html", "0.7", "weekly")]
    for path, pri in APPS:
        urls.append(("%s/%s" % (SITE, path), pri, "monthly"))
    for p in items:
        urls.append(("%s/p/%s.html" % (SITE, p["id"]), "0.6", "yearly"))
    body = "".join(
        "  <url>\n    <loc>%s</loc>\n    <lastmod>%s</lastmod>\n"
        "    <changefreq>%s</changefreq>\n    <priority>%s</priority>\n  </url>\n"
        % (esc(u), TODAY, freq, pri) for u, pri, freq in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "</urlset>\n")


def main():
    data = json.loads((BASE / "data" / "publications.json").read_text(encoding="utf-8"))
    items = data["items"]

    # 1) 메인 페이지
    tpl = (BASE / "index.template.html").read_text(encoding="utf-8")
    ql = json.loads((BASE / "data" / "quicklinks.json").read_text(encoding="utf-8"))
    ql_html, ql_i18n = quicklinks(ql)
    js = json.dumps({"items": items}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    out = (tpl
           .replace("__QUICKLINKS_I18N__", ql_i18n)
           .replace("__QUICKLINKS__", ql_html)
           .replace("__DATA__", js))
    (BASE / "index.html").write_text(out, encoding="utf-8")

    # 2) 개별 페이지
    pdir = BASE / "p"
    pdir.mkdir(exist_ok=True)
    (pdir / "detail.css").write_text(DETAIL_CSS, encoding="utf-8")
    for p in items:
        (pdir / ("%s.html" % p["id"])).write_text(detail_page(p, items), encoding="utf-8")

    # 3) 추천 글 · 큐레이션 페이지
    cur = json.loads((BASE / "data" / "curations.json").read_text(encoding="utf-8"))
    cur_items = cur.get("items") or []
    ctpl = (BASE / "curation.template.html").read_text(encoding="utf-8")
    cjs = json.dumps({"items": cur_items, "updated": cur.get("updated") or TODAY},
                     ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    cur_html = (ctpl
                .replace("__CURATIONS__", cjs)
                .replace("__CURATION_LD__", curation_ld(cur_items, SITE + "/curation.html")))
    (BASE / "curation.html").write_text(cur_html, encoding="utf-8")

    # 4) sitemap
    (BASE / "sitemap.xml").write_text(sitemap_xml(items), encoding="utf-8")

    arts = [p for p in items if p["kind"] == "article"]
    books = [p for p in items if p["kind"] == "book"]
    briefs = [p for p in items if p["kind"] == "brief"]
    print("built index.html (%d bytes) — %d articles, %d books, %d briefs, %d quick links"
          % (len(out.encode()), len(arts), len(books), len(briefs), len(ql.get("items") or [])))
    print("built p/ — %d individual pages + detail.css" % len(items))
    print("built curation.html (%d bytes) — %d curated items"
          % (len(cur_html.encode()), len(cur_items)))
    print("built sitemap.xml — %d urls" % (2 + len(APPS) + len(items)))


if __name__ == "__main__":
    main()
