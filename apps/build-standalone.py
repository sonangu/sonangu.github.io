#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《빅컨셉》 나침반의 '독립 주소' 판본을 만든다.

sites/leeyongseung/apps/big-concept-compass.html (홈페이지 안 앱) 을 원본으로,
상단의 '← 연구실 홈으로' 링크를 앱 이름 안내로 바꾸고, 하단 링크를 절대 주소로
고친 뒤 og/canonical 메타를 붙여 sites/big-concept/index.html 로 쓴다.

    python3 sites/leeyongseung/apps/build-standalone.py
"""
import pathlib

BASE = pathlib.Path(__file__).resolve().parents[3]  # /workspace
SRC = BASE / 'sites/leeyongseung/apps/big-concept-compass.html'
OUT_DIR = BASE / 'sites/big-concept'
SITE = 'https://big-concept.surge.sh/'

html = SRC.read_text(encoding='utf-8')


def sub1(old, new):
    global html
    assert html.count(old) == 1, (html.count(old), old[:60])
    html = html.replace(old, new, 1)


# 1) 상단 바: 홈 링크 → 수업 안내 (독립 앱 느낌)
sub1('''    <a class="back" href="../index.html#apps"><span class="a">←</span> 이용승 교수 연구실 홈으로</a>''',
     '''    <span class="back" style="cursor:default"><span class="a">✦</span> 《빅컨셉》 수업 · 이용승 교수</span>''')

# 2) 하단 링크: 상대 경로 → 절대 주소
sub1('''<span><a href="../index.html#apps">연구 App</a> · <a href="../index.html#contact">연락처</a></span>''',
     '''<span><a href="https://yslee.pe.kr/#apps">연구 App</a> · <a href="https://yslee.pe.kr/#contact">연락처</a></span>''')

# 3) 공유 미리보기 + canonical
sub1('''<meta name="robots" content="index,follow">''',
     '''<meta name="robots" content="index,follow">
<link rel="canonical" href="{site}">
<meta property="og:type" content="website">
<meta property="og:url" content="{site}">
<meta property="og:title" content="AI 시대 직업 나침반 — 《빅컨셉》 · 이용승 교수">
<meta property="og:description" content="내 안의 빅컨셉 10개와 짧은 글쓰기 → AI 시대의 빅컨셉 6문항 → 나만의 빅컨셉. 전공 대신 AI 시대에 새로 생기거나 커지는 중범위 직업 영역 36개 가운데 나와 가까운 3곳을 이유와 함께 보여 줍니다.">
<meta property="og:image" content="https://yslee.pe.kr/assets/profile-hero.jpg">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="AI 시대 직업 나침반 — 《빅컨셉》 · 이용승 교수">
<meta name="twitter:description" content="내 안의 빅컨셉 10개 → AI 시대의 빅컨셉 6문항 → 나만의 빅컨셉. 36개 중범위 직업 영역 가운데 나와 가까운 3곳.">'''.format(site=SITE))

assert '../index.html' not in html, 'relative homepage link left behind'

OUT_DIR.mkdir(parents=True, exist_ok=True)
out = OUT_DIR / 'index.html'
out.write_text(html, encoding='utf-8')
print('written', out, len(html.encode()), 'bytes')
