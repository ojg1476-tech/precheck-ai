"""기능성화장품 보고 품목 대조 (web/js/engine.js 의 checkCosProd 와 같은 판정).

상품명으로 보고 품목(rules/cos_products.json)을 찾고, 원고 속 기능 표현(미백·주름·자외선·염모·탈색·제모)이
그 제품이 보고한 기능인지 본다.
- 기능성 화장품으로 검사: 보고하지 않은 기능을 말하면 K1(꼭 고치기)
- 일반 화장품으로 검사했는데 보고된 기능성 제품이면: 그 기능 표현을 K2(확인 필요, 제품 종류 바꾸기 안내)로 바꾼다
보고 내용에 기능이 안 적힌 품목(비트 0)은 판정하지 않는다.
"""
from __future__ import annotations

import re

from .hfood import _norm_map, clean_listing


class CosProducts:
    def __init__(self, data: dict):
        self.by_name: dict[str, tuple[str, int]] = {}
        for name, m in data["p"]:
            k = _norm_map(clean_listing(name))[0]
            if len(k) >= 4:
                self.by_name[k] = (name, m)
        self.names = sorted((k for k in self.by_name if len(k) >= 9), key=lambda k: (-len(k), k))

    def find(self, name: str) -> tuple[str, int] | None:
        """정확히 같은 이름 → 등록 이름이 상품명 안에 들어 있으면(9자 이상, 상품명의 절반 이상, 가장 긴 것)"""
        k = _norm_map(clean_listing(name or ""))[0]
        if len(k) < 8:   # ‘데일리선크림’처럼 짧고 흔한 이름은 다른 회사 제품과 겹칠 수 있어 대조하지 않음
            return None
        if k in self.by_name:
            return self.by_name[k]
        for nk in self.names:
            if len(nk) * 2 >= len(k) and nk in k:
                return self.by_name[nk]
        return None


def _have(cfg: dict, m: int) -> str:
    return "·".join(v for b, v in sorted(((int(b), v) for b, v in cfg["bits"].items())) if m & b)


def check_cosprod(text: str, product_type: str, cfg: dict, penalties: dict, categories: dict,
                  products: CosProducts | None, name: str) -> tuple[list[dict], dict | None]:
    """(새 결과들, 찾은 보고 품목). 결과는 engine.Finding 필드와 같은 키의 dict."""
    if not products or not name:
        return [], None
    hit = products.find(name)
    if not hit:
        return [], None
    pname, m = hit
    prod = {"n": pname, "m": m, "have": _have(cfg, m)}
    if not m:
        return [], prod
    out = []
    for c in cfg["claims"]:
        bit = c["bit"]
        for mt in re.finditer(c["pattern"], text):
            p = mt.group(0).strip()
            if not p:
                continue
            want = cfg["bits"][str(bit)]
            if product_type == "fcos" and not m & bit:
                k = cfg["k1"]; grade = "red"; rid = "K1"
            elif product_type == "cos" and m & bit:
                k = cfg["k2"]; grade = "amber"; rid = "K2"
            else:
                continue
            fill = lambda s: s.replace("{prod}", pname).replace("{have}", prod["have"]).replace("{want}", want)
            cat = k["category"]
            out.append({"start": mt.start(), "end": mt.end(), "phrase": p, "grade": grade, "rule_id": rid,
                        "label": k["label"], "easy": k["explain"].replace("{p}", p), "why": fill(k["why"]), "alt": fill(k["alt"]),
                        "term": k["term"], "law": k["law"], "penalty": penalties.get(k["pen"], "") if k["pen"] else "",
                        "source": k["source"], "category": cat, "checks": list(categories.get(cat, {}).get("checks", [])),
                        "penalty_key": k["pen"] or ""})
    return out, prod
