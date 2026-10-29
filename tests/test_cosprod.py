"""기능성화장품 보고 품목 대조. python tests/test_cosprod.py (node 있으면 웹 엔진과도 비교)"""
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from precheck import Checker  # noqa: E402

JS = r"""
const M=require(process.argv[1]);const fs=require('fs');
const ck=new M.Checker(JSON.parse(fs.readFileSync(process.argv[2],'utf8')));
ck.setCosProducts(JSON.parse(fs.readFileSync(process.argv[3],'utf8')));
const inp=JSON.parse(fs.readFileSync(0,'utf8'));
console.log(JSON.stringify(inp.map(([ty,n,t])=>[ck.check(t,ty,{name:n}).map(f=>[f.start,f.end,f.grade,f.ruleId,f.phrase,f.why,f.alt,f.law,f.penalty,f.category]),ck.lastCos])));
"""


def run():
    ck = Checker()
    rows = list(csv.DictReader(open(ROOT / "data/cos_prod_test.csv", encoding="utf-8")))
    bad = []
    for r in rows:
        fs = ck.check(r["text"], r["product_type"], name=r["name"])
        ids = {f.rule_id for f in fs}
        assert ck.last_cos, ("보고 품목을 못 찾음", r["name"])
        if r["expect"] == "ok" and ids & {"K1", "K2"}: bad.append((r, ids))
        if r["expect"] == "K1" and "K1" not in ids: bad.append((r, ids))
        if r["expect"] == "K2" and ("K2" not in ids or any(f.category == "C2" and f.grade == "red" and f.rule_id != "K2" for f in fs if any(g.rule_id == "K2" and g.start < f.end and f.start < g.end for g in fs))): bad.append((r, ids))
    assert not bad, bad[:5]
    # 상품명이 없거나, 지어낸 상품명(예시 목록)이면 대조하지 않음
    ex = json.loads((ROOT / "examples/examples.json").read_text(encoding="utf-8"))["items"]
    for it in ex:
        if it["type"] in ("cos", "fcos"):
            ck.check(it["text"], it["type"], name=it["name"])
            assert ck.last_cos is None, ("예시 상품이 실제 보고 품목과 이어짐", it["name"], ck.last_cos)
    t = "피부 미백과 주름 개선에 도움을 줘요."
    assert [f.rule_id for f in ck.check(t, "fcos")] == [f.rule_id for f in ck.check(t, "fcos", name="")]
    # 웹 엔진과 같은 결과
    if shutil.which("node"):
        cases = [[r["product_type"], r["name"], r["text"]] for r in rows] + [[it["type"], it["name"], it["text"]] for it in ex if it["type"] in ("cos", "fcos")]
        out = subprocess.run(["node", "-e", JS, str(ROOT / "web/js/engine.js"), str(ROOT / "web/rules.json"), str(ROOT / "web/cos_products.json")],
                             input=json.dumps(cases), capture_output=True, text=True, check=True)
        js = json.loads(out.stdout)
        for c, j in zip(cases, js):
            fs = ck.check(c[2], c[0], name=c[1])
            py = [[[f.start, f.end, f.grade, f.rule_id, f.phrase, f.why, f.alt, f.law, f.penalty, f.category] for f in fs], ck.last_cos]
            assert j == py, (c, j, py)
    print(f"보고 품목 대조 {len(rows)}개 맞음 · 예시 상품은 대조 안 됨 · 웹 엔진과 같음")


if __name__ == "__main__":
    run()
