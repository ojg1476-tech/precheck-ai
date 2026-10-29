"""기능성화장품 보고 품목 표 만들기 (제품명으로 대조할 때 씀).

입력: data/cos/raw/reports.json.gz — 공공데이터포털 '식품의약품안전처_기능성화장품 보고품목정보'
      (FtnltCosmRptPrdlstInfoService01/getRptPrdlstInq01) 전체 (.github/workflows/fetch_cos.yml)
출력: rules/cos_products.json, web/cos_products.json
  {"bits": {...}, "p": [[제품명, 기능 비트], …]}  — 이름이 같은 품목은 하나로 합치고 기능은 합친다
기능 비트: 1 미백 · 2 주름 · 4 자외선 · 8 염모 · 16 탈색 · 32 제모. 0 = 보고 내용에 기능이 안 적힘(판정 안 함)
  - EE_NAME(효능·효과) 글자로 미백·주름·염모·탈색·제모를,
  - EFFECT_YN1·2·3(미백·주름·자외선 여부)와 SPF 값으로 미백·주름·자외선을 읽는다.
  (YN1·2·3 뜻은 제품명으로 확인: YN1만 Y → '화이트·브라이트닝', YN2만 Y → '링클' 제품이 대부분)
보고 품목만 있는 자료라 탈모·여드름·튼살·피부장벽(심사 품목)은 이 표에 없다.
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from precheck.hfood import _norm_map, clean_listing  # noqa: E402

BITS = {"미백": 1, "주름": 2, "자외선": 4, "염모": 8, "탈색": 16, "제모": 32}


def mask_of(r: dict) -> int:
    m = 0
    ee = r.get("EE_NAME") or ""
    if "미백" in ee: m |= 1
    if "주름" in ee: m |= 2
    if "자외선" in ee: m |= 4
    if "염모" in ee and "산화" not in ee: m |= 8
    if "탈색" in ee or "탈염" in ee: m |= 16
    if "산화" in ee: m |= 8 | 16          # 염모제·탈색제의 산화제(보조제)
    if "제모" in ee or "체모" in ee: m |= 32
    if r.get("EFFECT_YN1") == "Y": m |= 1
    if r.get("EFFECT_YN2") == "Y": m |= 2
    if r.get("EFFECT_YN3") == "Y" or (r.get("SPF") or "").strip(): m |= 4
    return m


def main():
    rows = json.loads(gzip.open(ROOT / "data/cos/raw/reports.json.gz", "rt", encoding="utf-8").read())
    by = {}
    for r in rows:
        if r.get("CANCEL_APPROVAL_YN") == "Y":
            continue
        name = (r.get("ITEM_NAME") or "").strip()
        k = _norm_map(clean_listing(name))[0]
        if len(k) < 4 or not re.search(r"[가-힣]{2}|[a-z]{4}", k):   # 숫자뿐인 이름 등은 빼기
            continue
        cur = by.get(k)
        m = mask_of(r)
        by[k] = [cur[0] if cur else name, (cur[1] if cur else 0) | m]
    p = sorted(by.values(), key=lambda x: x[0])
    data = {"source": "공공데이터포털 식품의약품안전처_기능성화장품 보고품목정보 (FtnltCosmRptPrdlstInfoService01)",
            "bits": BITS, "p": p}
    txt = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    for out in (ROOT / "rules" / "cos_products.json", ROOT / "web" / "cos_products.json"):
        out.write_text(txt, encoding="utf-8")
    known = sum(1 for _, m in p if m)
    print(f"보고 품목 {len(rows):,}건 → 이름 {len(p):,}개 (기능이 적힌 것 {known:,}개) · {len(txt.encode()) // 1024:,}KB")


if __name__ == "__main__":
    main()
