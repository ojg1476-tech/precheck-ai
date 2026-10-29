"""상세페이지 광고 문구 규칙 검사 엔진.

rules/rules.json 하나를 웹 검사기와 같이 쓴다. 검사 결과는 웹 버전(precheck.html)의
runRules + dedupe 와 같은 순서·같은 규칙으로 나온다 (tests/test_parity.py 로 확인).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict, field
from pathlib import Path

from .hfood import OVERRIDE, Products, check_hfood

RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "rules.json"
ORDER = {"red": 0, "amber": 1, "blue": 2}
COS_TYPES = {"cos", "fcos"}


@dataclass
class Finding:
    start: int
    end: int
    phrase: str
    grade: str          # red / amber / blue
    grade_name: str     # 꼭 고치기 / 확인 필요 / 자료 챙기기
    rule_id: str
    label: str          # 쉬운 이름
    why: str
    alt: str
    term: str           # 정확한 용어
    law: str            # 관련 기준
    penalty: str        # 이대로 두면
    source: str
    category: str = ""   # 분류 코드 (C1, F3, HF 등)
    checks: list = field(default_factory=list)  # 쓰기 전에 확인할 것
    penalty_key: str = ""  # 처분 키 (cA, f1 등) — 일괄 점검의 위험도 계산용
    easy: str = ""         # 정식 유형명(label) 아래 보여 줄 쉬운 이름

    def to_dict(self) -> dict:
        return asdict(self)


class Checker:
    def __init__(self, rules_path: str | Path = RULES_PATH):
        data = json.loads(Path(rules_path).read_text(encoding="utf-8"))
        self.version = data["version"]
        self.product_types = data["product_types"]
        self.grades = data["grades"]
        self.penalties = data["penalties"]
        self.rules = data["rules"]
        self.categories = data.get("categories", {})
        hf = Path(rules_path).with_name("hfood.json")
        self.hfood = data.get("hfood") or (json.loads(hf.read_text(encoding="utf-8")) if hf.exists() else None)
        self.last_ingredients: list = []
        self.last_product: dict | None = None
        self._products_path = Path(rules_path).with_name("hfood_products.json")
        self._products: Products | None = None
        for r in self.rules:
            r["_re"] = re.compile(r["pattern"], re.IGNORECASE if r["ignore_case"] else 0)

    @property
    def products(self) -> "Products | None":
        """신고 제품 표는 건강기능식품을 처음 검사할 때 읽는다 (4만여 개라 무거움)."""
        if self._products is None and self.hfood and self._products_path.exists():
            self._products = Products(json.loads(self._products_path.read_text(encoding="utf-8")), self.hfood)
        return self._products

    def check(self, text: str, product_type: str = "cos", name: str = "", report_no: str = "") -> list[Finding]:
        """name·report_no: 건강기능식품일 때 상품명·품목제조신고번호 (있으면 그 제품이 신고한 기능성으로 대조)"""
        if product_type not in self.product_types:
            raise ValueError(f"product_type은 {list(self.product_types)} 중 하나여야 해요")
        is_cos = product_type in COS_TYPES
        found: list[Finding] = []
        for r in self.rules:
            if product_type not in r["applies_to"]:
                continue
            for m in r["_re"].finditer(text):
                raw = m.group(0)
                if not raw.strip():
                    continue
                lead = len(raw) - len(raw.lstrip())
                pen_key = r["penalty_cos"] if is_cos else r["penalty_food"]
                found.append(Finding(
                    start=m.start() + lead, end=m.end(), phrase=raw.strip(),
                    grade=r["grade"], grade_name=self.grades[r["grade"]], rule_id=r["id"],
                    label=r["label"], easy=r.get("easy", ""), why=r["why"], alt=r["alt"], term=r["term"],
                    law=(r["law_cos"] if is_cos else r["law_food"]) or "-",
                    penalty=self.penalties.get(pen_key, "") if pen_key else "",
                    source=r["source"],
                    category=(cat := (r.get("category_cos") if is_cos else r.get("category_food")) or ""),
                    checks=list(self.categories.get(cat, {}).get("checks", [])),
                    penalty_key=pen_key or "",
                ))
        self.last_ingredients, self.last_product = [], None
        if product_type == "hfood" and self.hfood:
            extra, self.last_ingredients, self.last_product = check_hfood(
                text, self.hfood, self.penalties, self.categories.get("HF", {}).get("checks", []), self.products, name, report_no)
            if extra:
                ok = [e for e in extra if e["rule_id"] in ("H1", "H2")]   # 인정·신고된 기능
                found = [f for f in found if not (
                    (f.category == "HF" and any(f.start < e["end"] and e["start"] < f.end for e in extra))
                    or (f.category in OVERRIDE and any(e["_core"][0] < f.end and f.start < e["_core"][1] for e in ok)))]
                found += [Finding(grade_name=self.grades[e["grade"]], **{k: v for k, v in e.items() if k != "_core"}) for e in extra]
        return dedupe(found)


def dedupe(items: list[Finding]) -> list[Finding]:
    """겹치는 표현은 더 위험한 등급 하나만 남긴다 (웹 버전과 같은 규칙)."""
    items = sorted(items, key=lambda f: (f.start, ORDER[f.grade], -(f.end - f.start)))
    out: list[Finding] = []
    for f in items:
        if out and f.start < out[-1].end:
            if ORDER[f.grade] < ORDER[out[-1].grade]:
                out[-1] = f
            continue
        out.append(f)
    return out


def summarize(findings: list[Finding]) -> dict:
    c = {"red": 0, "amber": 0, "blue": 0}
    for f in findings:
        c[f.grade] += 1
    return c
