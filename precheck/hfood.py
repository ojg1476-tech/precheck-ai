"""건강기능식품: 원고 속 원료가 '그 기능성'을 식약처에서 인정받았는지 대조한다.

데이터는 rules.json 의 "hfood" (tools/build_hfood.py 가 식품안전나라 원문으로 만듦).
web/js/engine.js 의 checkHfood 와 같은 순서·같은 결과를 낸다 (tests/test_web_parity.py).

판정
- 원고에서 원료 이름을 하나도 못 찾으면 아무것도 더하지 않는다 (기존 '인정받은 문구인지 확인'이 그대로 남음).
- 기능 표현마다:
  · 찾은 원료 중 하나가 그 기능을 인정받음 → 자료 챙기기(인정 문구 그대로 쓰기) / 문구가 '도움' 없이 세면 확인 필요
  · 같은 이름의 원료 일부만 인정받음(예: 콜라겐 제품마다 다름) → 확인 필요
  · 아무 원료도 인정받지 않음 → 효과를 말하면 꼭 고치기, 떠올리게만 하면 확인 필요
- 신고번호(원고 속 12~15자리 번호) 또는 제품명으로 '신고된 제품'을 찾으면 원료 대신 그 제품이 신고한 기능성으로 판정한다.
  · 신고한 기능 → H1/H2 (신고 문구 원문을 대신 쓸 말로) · 신고하지 않은 기능 → H6 꼭 고치기 / H7 확인 필요
"""
from __future__ import annotations

import re

SKIP = re.compile(r"[\s·․ㆍ・\-_,./®ⓡⓇ™()\[\]{}'\"“”‘’:;]")
CLAUSE_END = re.compile(r"[.!?\n,]")   # 가운뎃점(·)은 기능 나열이라 끊지 않음
CLAIM = re.compile(r"도움|도와|돕|끝|걱정\s?없|해방|싹|쏙|개선|강화|감소|증진|향상|완화|해소|해결|예방|치료|효과|효능|낮춰|낮추|낮아|빠지|빠져|빠졌|줄었|나아|빼|좋아|좋은|튼튼|지켜|책임|확실|보장|회복|잡아|불태|태워|쑥쑥")
SENT_END = re.compile(r"[.!?\n]")
SOFT = re.compile(r"도움|도와|돕|필요")
EXCIPIENT = ("스테아린산", "셀룰로스", "셀룰로오스", "글리세린", "카복시메틸")
LAW_P = "식품표시광고법 제8조 제1항 제4호 (신고하지 않은 기능성), 건강기능식품 품목제조 신고 내용"
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


# 카드 제목 아래 한 줄 (찾은 표현을 넣어 풀어 쓴 설명) — web/js/engine.js HF_EXPLAIN 과 같음
HF_EXPLAIN = {
 "제품이 신고한 기능성": "‘{p}’ 같은 표현은 이 제품이 식약처에 신고한 기능이라 쓸 수 있어요. 다만 신고 문구를 바꾸지 말고 그대로 써야 해요.",
 "원료가 인정받은 기능성": "‘{p}’ 같은 표현은 이 원료가 식약처에서 인정받은 기능이라 쓸 수 있어요. 다만 인정 문구를 바꾸지 말고 그대로 써야 해요.",
 "신고 문구보다 세게 말함": "‘{p}’ 같은 표현처럼 단정하면 신고한 것보다 효과가 크다고 오해할 수 있어요. 쓸 수 있는 말은 ‘~에 도움을 줄 수 있음’까지예요.",
 "인정 문구보다 세게 말함": "‘{p}’ 같은 표현처럼 단정하면 인정받은 것보다 효과가 크다고 오해할 수 있어요. 쓸 수 있는 말은 ‘~에 도움을 줄 수 있음’까지예요.",
 "원료 종류에 따라 다른 기능성": "‘{p}’ 같은 기능은 같은 이름의 원료라도 제품마다 인정받은 내용이 달라서, 이 제품에 든 원료가 그 기능을 인정받았는지 확인해야 해요.",
 "제품이 신고하지 않은 기능성": "‘{p}’ 같은 표현을 쓰면 이 제품에 신고하지 않은 효과까지 있다고 오해할 수 있어요.",
 "원료가 인정받지 않은 기능성": "‘{p}’ 같은 표현을 쓰면 이 제품에 식약처가 인정하지 않은 효과까지 있다고 오해할 수 있어요.",
 "신고하지 않은 기능을 떠올리게 함": "‘{p}’ 같은 표현은 효과를 직접 말하지 않아도, 신고하지 않은 효과를 기대하게 만들 수 있어요.",
 "인정받지 않은 기능을 떠올리게 함": "‘{p}’ 같은 표현은 효과를 직접 말하지 않아도, 인정받지 않은 효과를 기대하게 만들 수 있어요."
}


# 원료가 인정받은 기능과 겹치면 지우는 기본 규칙 분류 (병 이름·건강기능식품 오인·효능 표현·인정 문구 확인)
OVERRIDE = {"F1", "F3", "F4", "HF"}


NO_RE = re.compile(r"(?<!\d)(?:19|20)\d{10,13}(?!\d)")


DECOR_RE = re.compile(r"\[[^\]]*\]|\([^)]*\)|【[^】]*】|무료\s?배송|당일\s?발송|선물\s?세트|기획\s?세트|정품|\d+\s?\+\s?\d+|"
                      r"[x×*]\s?\d+|\d+(\.\d+)?\s?(정|포|캡슐|알|병|개월분?|일분|박스|box|개입?|팩|통|세트|ml|mg|g|kg|l)(?![가-힣a-z])", re.I)


def clean_listing(name: str) -> str:
    """쇼핑몰 상품명에서 꾸밈말(대괄호, 1+1, 60정, 2박스 …)을 뺀다"""
    return DECOR_RE.sub(" ", name)


class Products:
    """신고 제품 표 (rules/hfood_products.json). 기능 분류는 읽을 때 kb 정규식으로 붙인다."""

    def __init__(self, data: dict, kb: dict):
        tags = [[f["id"] for f in find_funcs(c, kb)] for c in data["claims"]]
        self.items = []
        self.by_no = {}
        self.by_name = {}
        for no, name, ids in data["p"]:
            f = []
            for i in ids:
                for t in tags[i]:
                    if t not in f:
                        f.append(t)
            it = {"no": no, "n": name, "c": [data["claims"][i] for i in ids], "f": f}
            self.by_no[no] = len(self.items)
            k = _norm_map(clean_listing(name))[0]
            if len(k) >= 4:
                self.by_name.setdefault(k, []).append(len(self.items))
            self.items.append(it)
        self.names = sorted(self.by_name, key=lambda k: (-len(k), k))

    def find(self, text: str, name: str = "", no: str = "") -> tuple[list[int], str]:
        """신고번호(입력값 → 원고 속 번호) → 제품명 순서로 찾는다. 이름이 같은 제품이 여럿이면 모두. (제품들, 'no'|'name')"""
        for cand in ([re.sub(r"\D", "", no)] if no else []) + NO_RE.findall(text):
            if cand in self.by_no:
                return [self.by_no[cand]], "no"
        k = _norm_map(clean_listing(name or ""))[0]
        if len(k) >= 4:
            if k in self.by_name:
                return list(self.by_name[k]), "name"
            for nk in self.names:   # 등록 이름이 상품명 안에 들어 있으면 (가장 긴 것). 너무 짧은 이름은 쓰지 않음
                if len(nk) >= 9 and len(nk) * 2 >= len(k) and nk in k:
                    return list(self.by_name[nk]), "name"
        return [], ""


def check_hfood(text: str, kb: dict, penalties: dict, checks: list, products: "Products | None" = None,
                name: str = "", no: str = "") -> tuple[list[dict], list[dict], dict | None]:
    """(새 결과들, 찾은 원료들, 찾은 신고 제품). 결과는 engine.Finding 필드와 같은 키의 dict."""
    ings = find_ingredients(text, kb)
    pids, how = products.find(text, name, no) if products else ([], "")
    prod = None
    if pids:
        ps = [products.items[i] for i in pids]
        f, c = [], []
        for p in ps:
            f += [t for t in p["f"] if t not in f]
            c += [x for x in p["c"] if x not in c]
        prod = {"no": ps[0]["no"], "n": ps[0]["n"], "c": c, "f": f, "count": len(ps), "by": how}
    if not ings and not prod:
        return [], [], None
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
        ms = SENT_END.search(text, fm["end"])
        soft = bool(SOFT.search(text[cstart:ms.start() if ms else len(text)]))   # 'A 개선, B 개선에 도움'처럼 쉼표로 나열한 것도 부드러운 말로 봄
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
        if prod:
            base = {"start": fm["start"], "end": end, "phrase": text[fm["start"]:end].strip(), "source": "식품안전나라 건강기능식품 품목제조 신고사항",
                    "category": "HF", "checks": list(checks), "_core": (fm["start"], fm["end"]), "term": "", "law": LAW_P, "penalty_key": "f4", "penalty": penalties.get("f4", "")}
            label = f"‘{prod['n']}’(신고번호 {prod['no']})" + (f" 등 같은 이름 제품 {prod['count']}개" if prod["count"] > 1 else "")
            if _satisfies(prod, fid, parents):
                exact = _exact(prod, fid, parents, kb)
                if claim and not soft:
                    out.append({**base, "grade": "amber", "rule_id": "H2", "label": "신고 범위 초과 표현", "easy": "신고 문구보다 세게 말함",
                                "why": f"{label}은(는) ‘{fname[fid]}’ 기능성을 신고했지만, 신고 문구는 ‘{exact}’예요. ‘개선’, ‘효과’처럼 단정하면 신고 범위를 넘는 광고가 돼요.",
                                "alt": exact, "term": "신고한 기능성 범위를 넘는 표시·광고"})
                else:
                    out.append({**base, "grade": "blue", "rule_id": "H1", "label": "신고 기능성 표시", "easy": "제품이 신고한 기능성",
                                "why": f"{label}은(는) ‘{exact}’로 신고된 제품이에요. 이 문구 그대로 쓰고, 협회 심의를 받은 내용인지 확인하세요.",
                                "alt": exact, "term": "신고한 기능성 표시 (신고 문구 그대로)", "penalty_key": "", "penalty": ""})
            else:
                have = []
                for t in prod["f"]:
                    if fname[t] not in have:
                        have.append(fname[t])
                strong = claim or soft
                by_name = prod["by"] == "name"   # 상품명으로 찾은 제품은 다른 회사 같은 이름일 수 있어 한 단계 낮춤
                out.append({**base, "grade": "red" if strong and not by_name else "amber", "rule_id": "H6" if strong else "H7",
                            "label": "미신고 기능성 표시" if strong else "미신고 기능성 암시",
                            "easy": "제품이 신고하지 않은 기능성" if strong else "신고하지 않은 기능을 떠올리게 함",
                            "why": f"{label}이(가) 신고한 기능성은 ‘{_join(have, 4)}’예요. ‘{fname[fid]}’ 기능성은 신고하지 않았어요. 원료에 그 기능이 있어도 제품으로 신고하지 않았으면 광고할 수 없어요."
                                   + (" 상품명으로 찾은 제품이라, 다른 제품이면 신고번호를 넣어 다시 확인하세요." if by_name else ""),
                            "alt": f"(신고한 기능성만: {prod['c'][0]})", "term": "신고하지 않은 기능성 표시·광고"})
            continue
        base = {"start": fm["start"], "end": end, "phrase": text[fm["start"]:end].strip(), "source": "식품안전나라 건강기능식품 기능성 원료 인정 내용",
                "category": "HF", "checks": list(checks), "_core": (fm["start"], fm["end"]), "term": "", "law": LAW, "penalty_key": "f4", "penalty": penalties.get("f4", "")}
        if full:
            it = items[full[0]["items"][0]]
            exact = _exact(it, fid, parents, kb)
            nm = text[full[0]["start"]:full[0]["end"]]
            if claim and not soft:
                out.append({**base, "grade": "amber", "rule_id": "H2", "label": "인정 범위 초과 표현", "easy": "인정 문구보다 세게 말함",
                            "why": f"‘{nm}’은(는) ‘{fname[fid]}’ 기능성을 인정받았지만, 인정 문구는 ‘{exact}’예요. ‘개선’, ‘효과’처럼 단정하면 인정 범위를 넘는 광고가 돼요.",
                            "alt": exact, "term": "인정받은 기능성 범위를 넘는 표시·광고"})
            else:
                out.append({**base, "grade": "blue", "rule_id": "H1", "label": "인정 기능성 표시", "easy": "원료가 인정받은 기능성",
                            "why": f"‘{nm}’은(는) 식약처에서 ‘{exact}’로 인정받은 원료예요. 이 문구 그대로 쓰고, 협회 심의를 받은 내용인지 확인하세요.",
                            "alt": exact, "term": "인정받은 기능성 표시 (인정 문구 그대로)", "penalty_key": "", "penalty": ""})
        elif part:
            g = part[0]
            nm = text[g["start"]:g["end"]]
            ok_names = _join([items[i]["n"] for i in part_ok])
            out.append({**base, "grade": "amber", "rule_id": "H3", "label": "원료별 인정 기능성 상이", "easy": "원료 종류에 따라 다른 기능성",
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
                        "label": "미인정 기능성 표시" if claim else "미인정 기능성 암시",
                        "easy": "원료가 인정받지 않은 기능성" if claim else "인정받지 않은 기능을 떠올리게 함",
                        "why": f"원고에서 찾은 원료({_join(names)})가 인정받은 기능성은 ‘{_join(have, 4)}’예요. ‘{fname[fid]}’ 기능성은 인정받지 않았어요. 다른 기능성 원료가 들어 있다면 그 원료의 인정 내용을 확인하세요.",
                        "alt": f"(인정받은 기능성만: {it0['c'][0]})", "term": "인정받지 않은 기능성 표시·광고"})
    found = [{"name": text[g["start"]:g["end"]], "items": [items[i]["n"] for i in g["items"]][:5]} for g in ings]
    for o in out:
        o["easy"] = HF_EXPLAIN.get(o["easy"], o["easy"]).replace("{p}", o["phrase"])
    pinfo = {"no": prod["no"], "name": prod["n"], "count": prod["count"], "by": prod["by"], "claims": prod["c"][:12]} if prod else None
    return out, found, pinfo


def _exact(item: dict, fid: str, parents: dict, kb: dict) -> str:
    """그 기능에 해당하는 인정 문구 중 가장 짧은 것"""
    hits = [c for c in item["c"] if any(t == fid or fid in parents.get(t, ()) for t in _tags_of(c, kb))]
    return min(hits, key=len) if hits else item["c"][0]


_TAG_CACHE: dict = {}


def _tags_of(claim: str, kb: dict) -> list[str]:
    if claim not in _TAG_CACHE:
        _TAG_CACHE[claim] = [f["id"] for f in find_funcs(claim, kb)]
    return _TAG_CACHE[claim]
