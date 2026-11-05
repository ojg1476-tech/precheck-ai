"""우회 표기 정리 (web/js/engine.js 의 deobf 와 같음).

글자 사이에 기호·띄어쓰기를 넣거나(다.이.어.트, 면♡역력, 면 역 력) 자음·모음을 풀어 쓴(ㄷㅣ톡스) 표현을
붙여 쓴 글로 바꾼다. 결과 글자마다 원래 글의 [시작, 끝) 위치를 같이 돌려줘서 찾은 위치를 원래 글로 되돌린다.
"""
from __future__ import annotations

import re

NOTE = " 글자 사이에 기호나 띄어쓰기를 넣거나 자음·모음을 풀어 써도 같은 표현으로 봐요."
CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
JUNG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
JONG = " ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ"
ZW = re.compile(r"[​-‍⁠﻿]")
SYM = re.compile(r"(?<=[가-힣])[*_~♡♥★☆^♪✿❤]+(?=[가-힣])")
RUN = re.compile(r"(?<![가-힣])[가-힣](?:[ \t.·ㆍ\-/|,]{1,2}[가-힣](?![가-힣])){2,}")
RUN2 = re.compile(r"(?<![가-힣])[가-힣][.\-/|][가-힣](?![가-힣])")
SEP = re.compile(r"[ \t.·ㆍ\-/|,]")


def deobf(text: str) -> tuple[str, list[int], list[int]]:
    t, s, e = [], [], []
    for i, c in enumerate(text):
        if not ZW.match(c):
            t.append(c); s.append(i); e.append(i + 1)
    t2, s2, e2 = [], [], []   # 풀어 쓴 자음·모음 합치기
    i = 0
    while i < len(t):
        c = CHO.find(t[i]); v = JUNG.find(t[i + 1]) if i + 1 < len(t) else -1
        if c >= 0 and v >= 0:
            k = 0
            if i + 2 < len(t):
                jj = JONG.find(t[i + 2])
                if jj > 0 and not (i + 3 < len(t) and t[i + 3] in JUNG):
                    k = jj
            t2.append(chr(0xAC00 + (c * 21 + v) * 28 + k)); s2.append(s[i]); e2.append(e[i + (2 if k else 1)])
            i += 3 if k else 2
        else:
            t2.append(t[i]); s2.append(s[i]); e2.append(e[i]); i += 1
    t, s, e = t2, s2, e2

    def drop(rx, in_run):
        nonlocal t, s, e
        st = "".join(t); keep = [True] * len(t)
        for m in rx.finditer(st):
            for i in range(m.start(), m.end()):
                if not in_run or SEP.match(st[i]):
                    keep[i] = False
        t = [x for x, k in zip(t, keep) if k]; s = [x for x, k in zip(s, keep) if k]; e = [x for x, k in zip(e, keep) if k]

    drop(SYM, False)
    drop(RUN, True)
    drop(RUN2, True)
    return "".join(t), s, e
