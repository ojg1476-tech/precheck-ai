"""웹 화면용 JS 엔진(web/js/engine.js)이 Python 엔진과 같은 결과를 내는지 확인. python tests/test_web_parity.py (node 필요)"""
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from precheck import Checker, check_products, read_table  # noqa: E402

JS = r"""
const M=require(process.argv[1]);const fs=require('fs');
const ck=new M.Checker(JSON.parse(fs.readFileSync(process.argv[2],'utf8')));
const inp=JSON.parse(fs.readFileSync(0,'utf8'));
const single=inp.cases.map(([t,ty])=>ck.check(t,ty).map(f=>[f.start,f.end,f.grade,f.ruleId,f.penaltyKey,f.category]));
const rows=M.readRows(M.parseCSV(inp.csv));
const batch=M.checkProducts(rows,ck).map(r=>[r.name,r.tier,r.maxPenalty,r.error]);
const ov=M.overview(M.checkProducts(rows,ck),ck);
console.log(JSON.stringify({single,batch,ov}));
"""


def test_web_engine_matches_python():
    ck = Checker()
    cases = []
    for fn in ["data/eval_set.csv", "data/test2.csv", "data/test3.csv"]:
        for r in csv.DictReader(open(ROOT / fn, encoding="utf-8")):
            cases.append([r["text"], r["product_type"]])
    sample = (ROOT / "examples/sample_products.csv").read_text(encoding="utf-8-sig")
    out = subprocess.run(["node", "-e", JS, str(ROOT / "web/js/engine.js"), str(ROOT / "rules/rules.json")],
                         input=json.dumps({"cases": cases, "csv": sample}), capture_output=True, text=True, check=True)
    js = json.loads(out.stdout)
    py_single = [[[f.start, f.end, f.grade, f.rule_id, f.penalty_key, f.category] for f in ck.check(t, ty)] for t, ty in cases]
    assert js["single"] == py_single
    res = check_products(read_table(sample.encode(), "s.csv"), ck)
    assert js["batch"] == [[r.name, r.tier, list(r.max_penalty) if r.max_penalty else None, r.error] for r in res]
    from precheck import overview
    ov = overview(res, ck)
    assert js["ov"]["tiers"] == ov["tiers"] and [tuple(x) for x in js["ov"]["common"]] == ov["common"]
    print(f"{len(cases)}개 문구 + 예시 목록 일괄 점검 결과 같음")


if __name__ == "__main__":
    test_web_engine_matches_python()
