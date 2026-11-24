#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《권력·의무·자유》 딜레마 나침반의 '독립 주소' 판본을 만든다.

sites/leeyongseung/apps/power-duty-freedom.html (홈페이지 안 앱) 을 원본으로,
상단의 '← 연구실 홈으로' 링크를 앱 이름 안내로 바꾸고, 하단 링크를 절대 주소로
고친 뒤 canonical·og 메타를 붙여 sites/power-duty-freedom/index.html 로 쓴다.

    python3 sites/leeyongseung/apps/build-standalone-pdf.py
"""
import pathlib

BASE = pathlib.Path(__file__).resolve().parents[3]  # /workspace
SRC = BASE / 'sites/leeyongseung/apps/power-duty-freedom.html'
OUT_DIR = BASE / 'sites/power-duty-freedom'
SITE = 'https://power-duty-freedom.surge.sh/'

html = SRC.read_text(encoding='utf-8')


def sub1(old, new):
    global html
    assert html.count(old) == 1, (html.count(old), old[:70])
    html = html.replace(old, new, 1)


# 1) 상단 바: 홈 링크 → 수업 안내 (독립 앱 느낌)
sub1('''    <a class="back" href="../index.html#apps"><span class="a">←</span> 이용승 교수 연구실 홈으로</a>''',
     '''    <span class="back" style="cursor:default"><span class="a">✦</span> 《권력·의무·자유》 수업 · 이용승 교수</span>''')

# 2) 하단 링크: 상대 경로 → 절대 주소
sub1('''<span><a href="../index.html#apps">연구 App</a> · <a href="../index.html#contact">연락처</a></span>''',
     '''<span><a href="https://yslee.pe.kr/#apps">연구 App</a> · <a href="https://yslee.pe.kr/#contact">연락처</a></span>''')

# 3) 공유 미리보기 + canonical
sub1('''<meta name="robots" content="index,follow">''',
     '''<meta name="robots" content="index,follow">
<link rel="canonical" href="{site}">
<meta property="og:type" content="website">
<meta property="og:url" content="{site}">
<meta property="og:title" content="권력·의무·자유 딜레마 나침반 — 이용승 교수">
<meta property="og:description" content="권력·의무·자유 세 단원에서 실제로 다룬 열두 장면에 A / B / 제3의 길로 답하고, 나의 균형 삼각형과 단원별 자리, 반대편의 질문을 얻습니다. 어떤 수업에서나 질문을 직접 만들어 투표에 올릴 수 있습니다.">
<meta property="og:image" content="https://yslee.pe.kr/assets/profile-hero.jpg">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="권력·의무·자유 딜레마 나침반 — 이용승 교수">
<meta name="twitter:description" content="열두 개의 수업 장면 → 권력·의무·자유 균형 삼각형 → 내가 던져볼 질문 셋. 수업 진행 모드에서 단원별 거수 집계와 새 질문 만들기까지.">'''.format(site=SITE))

assert '../index.html' not in html, 'relative homepage link left behind'

OUT_DIR.mkdir(parents=True, exist_ok=True)
out = OUT_DIR / 'index.html'
out.write_text(html, encoding='utf-8')
print('written', out, len(html.encode()), 'bytes')
