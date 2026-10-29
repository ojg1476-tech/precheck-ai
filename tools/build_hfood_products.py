"""신고된 건강기능식품 제품별 '신고한 기능성' 표 만들기 (신고번호·제품명으로 대조할 때 씀).

입력: data/hfood/raw/C003_func.json.gz — 식품안전나라 C003(건강기능식품 품목제조 신고사항) 전체에서
      [신고번호, 제품명, 신고일, 주된 기능성]만 뽑은 것 (.github/workflows/fetch_hfood.yml)
출력: rules/hfood_products.json, web/hfood_products.json
  {"claims": [기능성 문구…], "p": [[신고번호, 제품명, [문구 번호…]], …]}
문구의 기능 분류는 엔진이 읽을 때 rules/hfood.json 의 분류 정규식으로 붙인다 (웹·Python 같은 결과).
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from build_hfood import claims_of, tag  # noqa: E402

RAW = ROOT / "data" / "hfood" / "raw"


def split_claims(text: str) -> list[str]:
    cs = []
    for c in claims_of(text):
        c = re.sub(r"^\s*(\d+[.)]\s*|[가-힣A-Za-z0-9 ]{1,12}\s?:\s*|\[[^\]]{1,12}\]\s*)", "", c).strip()   # '3) 비타민B2 : …', '[나이아신] …' 머리말 빼기
        if c and c not in cs:
            cs.append(c)
        parts = re.split(r"\s?[･·ㆍ]\s?", c)
        if len(parts) > 1:
            tail = re.search(r"(에|을|를)?\s?도움을?\s?줄\s?수\s?있(음|습니다)$", parts[-1])
            for p in parts:
                q = p if re.search("도움|필요", p) else (p + "에 도움을 줄 수 있음" if tail else "")
                if q and len(tag(q)) == 1 and q not in cs:
                    cs.append(q)
    cs = [c for c in cs if tag(c) and not re.search(r"[·･ㆍ]\s?에\s", c)]   # '…항산화·에 도움' 같은 깨진 문구 빼기
    return sorted(cs, key=lambda c: len(tag(c)) > 1)   # 기능 하나짜리 문구를 앞에 (보여 줄 때·대신 쓸 말)


def main():
    f = RAW / "C003_func.json.gz"
    if f.exists():
        rows = json.loads(gzip.open(f, "rt", encoding="utf-8").read())
    else:   # 전체를 아직 못 받았으면 표본으로
        rows = [[r["PRDLST_REPORT_NO"], r["PRDLST_NM"], r["PRMS_DT"], r["PRIMARY_FNCLTY"]]
                for r in json.loads((RAW / "C003_sample.json").read_text(encoding="utf-8"))]
    claims, cidx, prods, seen = [], {}, [], set()
    for no, name, _dt, fn in sorted(rows, key=lambda r: r[0]):
        no = re.sub(r"\D", "", no or "")
        if not no or no in seen:
            continue
        cs = split_claims(fn)
        if not cs:
            continue
        seen.add(no)
        ids = []
        for c in cs:
            if c not in cidx:
                cidx[c] = len(claims)
                claims.append(c)
            ids.append(cidx[c])
        prods.append([no, (name or "").strip(), ids])
    data = {"source": "식품안전나라 OpenAPI C003 건강기능식품 품목제조 신고사항", "claims": claims, "p": prods}
    txt = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    for out in (ROOT / "rules" / "hfood_products.json", ROOT / "web" / "hfood_products.json"):
        out.write_text(txt, encoding="utf-8")
    print(f"제품 {len(prods):,}개 · 기능성 문구 {len(claims):,}개 · {len(txt.encode()) // 1024:,}KB")


if __name__ == "__main__":
    main()
