#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《정의란 무엇인가》 딜레마 수업 앱의 '독립 주소' 판본을 만든다.

sites/leeyongseung/apps/what-is-justice.html (홈페이지 안 앱) 을 원본으로,
상대 경로 홈 링크를 절대 주소로 바꾸고 canonical·og 메타를 붙여
sites/what-is-justice/index.html 로 쓴다.

    python3 sites/leeyongseung/apps/build-standalone-justice.py
"""
import pathlib

BASE = pathlib.Path(__file__).resolve().parents[3]  # /workspace
SRC = BASE / 'sites/leeyongseung/apps/what-is-justice.html'
OUT_DIR = BASE / 'sites/what-is-justice'
SITE = 'https://what-is-justice.surge.sh/'

html = SRC.read_text(encoding='utf-8')


def sub1(old, new):
    global html
    assert html.count(old) == 1, (html.count(old), old[:70])
    html = html.replace(old, new, 1)


# 1) 상단 바: 상대 경로 → 절대 주소 (독립 주소에서도 홈으로 갈 수 있게)
sub1('<a class="back" href="../#apps"><span class="a">←</span> yslee.pe.kr</a>',
     '<a class="back" href="https://yslee.pe.kr/#apps"><span class="a">←</span> yslee.pe.kr</a>')

# 2) 하단 링크: 상대 경로 → 절대 주소
sub1('<span><a href="../#apps">연구 App</a> · <a href="https://yslee.pe.kr/#contact">연락처</a></span>',
     '<span><a href="https://yslee.pe.kr/#apps">연구 App</a> · <a href="https://yslee.pe.kr/#contact">연락처</a></span>')

# 3) 공유 미리보기 + canonical
sub1('<meta name="robots" content="index,follow">',
     '''<meta name="robots" content="index,follow">
<link rel="canonical" href="{site}">
<meta property="og:type" content="website">
<meta property="og:url" content="{site}">
<meta property="og:title" content="정의란 무엇인가 · 딜레마 수업 앱 — 이용승 교수">
<meta property="og:description" content="수단·자격·한계·주체 네 축으로 배치한 열여섯 장면에 A / B / 제3의 길로 답하면, 공리적 조화·인간의 존엄·시스템적 공정 세 준거 위에 내가 선 자리와 수업의 정의관 6유형을 보여 줍니다. 강의실에서는 거수 숫자를 바로 집계하는 수업 진행 모드까지.">
<meta property="og:image" content="https://yslee.pe.kr/assets/profile-hero.jpg">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="정의란 무엇인가 · 딜레마 수업 앱 — 이용승 교수">
<meta name="twitter:description" content="열여섯 장면 → 세 준거 삼각형 → 정의관 6유형 → 기록지 4번. 수업 진행 모드에서 A/B/제3의 길 실시간 집계.">'''.format(site=SITE))

assert '"../#apps"' not in html, 'relative homepage link left behind'

OUT_DIR.mkdir(parents=True, exist_ok=True)
out = OUT_DIR / 'index.html'
out.write_text(html, encoding='utf-8')
print('written', out, len(html.encode()), 'bytes')
