"""건강기능식품: 원고 속 원료가 '그 기능성'을 식약처에서 인정받았는지 대조한다.

데이터는 rules.json 의 "hfood" (tools/build_hfood.py 가 식품안전나라 원문으로 만듦).
web/js/engine.js 의 checkHfood 와 같은 순서·같은 결과를 낸다 (tests/test_web_parity.py).

판정
- 원고에서 원료 이름을 하나도 못 찾으면 아무것도 더하지 않는다 (기존 '인정받은 문구인지 확인'이 그대로 남음).
- 기능 표현마다:
  · 찾은 원료 중 하나가 그 기능을 인정받음 → 자료 챙기기(인정 문구 그대로 쓰기) / 문구가 '도움' 없이 세면 확인 필요
  · 같은 이름의 원료 일부만 인정받음(예: 콜라겐 제품마다 다름) → 확인 필요
  · 아무 원료도 인정받지 않음 → 효과를 말하면 꼭 고치기, 떠올리게만 하면 확인 필요
"""
from __future__ import annotations

import re

SKIP = re.compile(r"[\s·․ㆍ・\-_,./®ⓡⓇ™()\[\]{}'\"“”‘’:;]")
CLAUSE_END = re.compile(r"[.!?\n,·]")
CLAIM = re.compile(r"도움|도와|돕|끝|걱정\s?없|해방|싹|쏙|개선|강화|감소|증진|향상|완화|해소|해결|예방|치료|효과|효능|낮춰|낮추|낮아|빠지|빠져|빠졌|줄었|나아|빼|좋아|좋은|튼튼|지켜|책임|확실|보장|회복|잡아|불태|태워|쑥쑥")
SOFT = re.compile(r"도움|도와|돕|필요")
EXCIPIENT = ("스테아린산", "셀룰로스", "셀룰로오스", "글리세린", "카복시메틸")
LAW = "식품표시광고법 제8조 제1항 제4호 (인정받지 않은 기능성), 건강기능식품 기능성 원료 인정 내용"


def _norm_map(text: str):
    chars, idx = [], []
    for i, ch in enumerate(text):
        if SKIP.match(ch):
            continue
        chars.append(ch.lower() if ch.isascii() else ch)
        idx.append(i)
    return "".join(chars), idx


def find_ingredients(text: str, kb: dict) -> list[dict]:
    s, idx = _norm_map(text)
    taken, out = [], []
    for key, items in kb["keys"]:
        start = 0
        while True:
            j = s.find(key, start)
            if j < 0:
                break
            start = j + 1
            e = j + len(key)
            if s[max(0, j - 6):j].endswith(EXCIPIENT):   # 스테아린산마그네슘·카복시메틸셀룰로스칼슘 같은 첨가물
                continue
            a, b = idx[j], idx[e - 1] + 1   # 영문 원료명은 원문에서 앞뒤가 영문·숫자로 이어지면 다른 낱말
            if key.isascii() and ((a > 0 and text[a - 1].isascii() and text[a - 1].isalnum()) or (b < len(text) and text[b].isascii() and text[b].isalnum())):
                continue
            if any(j < b and a < e for a, b in taken):
                continue
            taken.append((j, e))
            out.append({"start": idx[j], "end": idx[e - 1] + 1, "key": key, "items": list(items)})
    out.sort(key=lambda m: m["start"])
    return out


def find_funcs(text: str, kb: dict) -> list[dict]:
    taken, out = [], []
    for f in kb["funcs"]:
        for m in re.finditer(f["re"], text):
            if m.end() == m.start() or any(m.start() < b and a < m.end() for a, b in taken):
                continue
            taken.append((m.start(), m.end()))
            out.append({"start": m.start(), "end": m.end(), "id": f["id"]})
    out.sort(key=lambda m: m["start"])
    return out


def _satisfies(item: dict, fid: str, parents: dict) -> bool:
    for t in item["f"]:
        if t == fid or fid in parents.get(t, ()):
            return True
    return False


def _join(names: list[str], n: int = 3) -> str:
    names = list(dict.fromkeys(names))
    return ", ".join(names[:n]) + (f" 외 {len(names) - n}개" if len(names) > n else "")


# 원료가 인정받은 기능과 겹치면 지우는 기본 규칙 분류 (병 이름·건강기능식품 오인·효능 표현·인정 문구 확인)
OVERRIDE = {"F1", "F3", "F4", "HF"}


def check_hfood(text: str, kb: dict, penalties: dict, checks: list) -> tuple[list[dict], list[dict]]:
    """(새 결과들, 찾은 원료들). 결과는 engine.Finding 필드와 같은 키의 dict."""
    ings = find_ingredients(text, kb)
    if not ings:
        return [], []
    items = kb["items"]
    fname = {f["id"]: f["name"] for f in kb["funcs"]}
    parents = {f["id"]: [p for p in f["parent"].split(",") if p] for f in kb["funcs"]}
    out = []
    for fm in find_funcs(text, kb):
        fid = fm["id"]
        m = CLAUSE_END.search(text, fm["end"])
        cend = m.start() if m else len(text)
        cstart = max([mm.end() for mm in CLAUSE_END.finditer(text, 0, fm["start"])] or [0])
        clause = text[cstart:cend]
        end = min(cend, fm["end"] + 20)
        full, part, part_ok = [], [], []
        for g in ings:
            ok = [i for i in g["items"] if _satisfies(items[i], fid, parents)]
            if ok and len(ok) == len(g["items"]):
                full.append(g)
            elif ok:
                part.append(g)
                part_ok += ok
        claim = bool(CLAIM.search(clause))
        base = {"start": fm["start"], "end": end, "phrase": text[fm["start"]:end].strip(), "source": "식품안전나라 건강기능식품 기능성 원료 인정 내용",
                "category": "HF", "checks": list(checks), "_core": (fm["start"], fm["end"]), "term": "", "law": LAW, "penalty_key": "f4", "penalty": penalties.get("f4", "")}
        if full:
            it = items[full[0]["items"][0]]
            exact = _exact(it, fid, parents, kb)
            nm = text[full[0]["start"]:full[0]["end"]]
            if claim and not SOFT.search(clause):
                out.append({**base, "grade": "amber", "rule_id": "H2", "label": "인정 문구보다 세게 말함",
                            "why": f"‘{nm}’은(는) ‘{fname[fid]}’ 기능성을 인정받았지만, 인정 문구는 ‘{exact}’예요. ‘개선’, ‘효과’처럼 단정하면 인정 범위를 넘는 광고가 돼요.",
                            "alt": exact, "term": "인정받은 기능성 범위를 넘는 표시·광고"})
            else:
                out.append({**base, "grade": "blue", "rule_id": "H1", "label": "원료가 인정받은 기능성",
                            "why": f"‘{nm}’은(는) 식약처에서 ‘{exact}’로 인정받은 원료예요. 이 문구 그대로 쓰고, 협회 심의를 받은 내용인지 확인하세요.",
                            "alt": exact, "term": "인정받은 기능성 표시 (인정 문구 그대로)", "penalty_key": "", "penalty": ""})
        elif part:
            g = part[0]
            nm = text[g["start"]:g["end"]]
            ok_names = _join([items[i]["n"] for i in part_ok])
            out.append({**base, "grade": "amber", "rule_id": "H3", "label": "원료 종류에 따라 다른 기능성",
                        "why": f"‘{nm}’ 원료 중 일부({ok_names})만 ‘{fname[fid]}’ 기능성을 인정받았어요. 제품에 든 원료가 정확히 그 원료인지 원료명(균주·제품 코드까지)으로 확인하세요.",
                        "alt": _exact(items[part_ok[0]], fid, parents, kb), "term": "원료별로 다른 인정 기능성"})
        else:
            names = [text[g["start"]:g["end"]] for g in ings]
            have = []
            for g in ings:
                for i in g["items"]:
                    for t in items[i]["f"]:
                        if fname[t] not in have:
                            have.append(fname[t])
            it0 = items[ings[0]["items"][0]]
            out.append({**base, "grade": "red" if claim else "amber", "rule_id": "H4" if claim else "H5",
                        "label": "원료가 인정받지 않은 기능성" if claim else "인정받지 않은 기능을 떠올리게 함",
                        "why": f"원고에서 찾은 원료({_join(names)})가 인정받은 기능성은 ‘{_join(have, 4)}’예요. ‘{fname[fid]}’ 기능성은 인정받지 않았어요. 다른 기능성 원료가 들어 있다면 그 원료의 인정 내용을 확인하세요.",
                        "alt": f"(인정받은 기능성만: {it0['c'][0]})", "term": "인정받지 않은 기능성 표시·광고"})
    found = [{"name": text[g["start"]:g["end"]], "items": [items[i]["n"] for i in g["items"]][:5]} for g in ings]
    return out, found


def _exact(item: dict, fid: str, parents: dict, kb: dict) -> str:
    """그 기능에 해당하는 인정 문구 중 가장 짧은 것"""
    hits = [c for c in item["c"] if any(t == fid or fid in parents.get(t, ()) for t in _tags_of(c, kb))]
    return min(hits, key=len) if hits else item["c"][0]


_TAG_CACHE: dict = {}


def _tags_of(claim: str, kb: dict) -> list[str]:
    if claim not in _TAG_CACHE:
        _TAG_CACHE[claim] = [f["id"] for f in find_funcs(claim, kb)]
    return _TAG_CACHE[claim]
