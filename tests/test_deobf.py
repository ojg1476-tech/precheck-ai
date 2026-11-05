"""우회 표기(다.이.어.트, 면♡역력, ㄷㅣ톡스)와 협찬 표시(R49)를 찾는지, 웹·Python이 같은지 확인. python tests/test_deobf.py"""
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from precheck import Checker  # noqa: E402

JS = r"""
const M=require(process.argv[1]);const fs=require('fs');
const ck=new M.Checker(JSON.parse(fs.readFileSync(process.argv[2],'utf8')));
const inp=JSON.parse(fs.readFileSync(0,'utf8'));
console.log(JSON.stringify(inp.map(([t,ty])=>ck.check(t,ty).map(f=>[f.start,f.end,f.grade,f.ruleId,f.phrase,f.why,f.easy]))));
"""


def test_deobf():
    ck = Checker()
    rows = list(csv.DictReader(open(ROOT / "data/deobf_test.csv", encoding="utf-8")))
    py = []
    for r in rows:
        fs = ck.check(r["text"], r["product_type"])
        ids = {f.rule_id for f in fs if f.grade in ("red", "amber")}
        if r["expect"]:
            assert r["expect"] in ids, (r["text"], ids)
        else:
            assert not ids, (r["text"], ids)
        py.append([[f.start, f.end, f.grade, f.rule_id, f.phrase, f.why, f.easy] for f in fs])
    out = subprocess.run(["node", "-e", JS, str(ROOT / "web/js/engine.js"), str(ROOT / "web/rules.json")],
                         input=json.dumps([[r["text"], r["product_type"]] for r in rows]), capture_output=True, text=True, check=True)
    assert json.loads(out.stdout) == py
    print(f"우회 표기·협찬 표시 {len(rows)}개 확인, 웹·Python 결과 같음")


if __name__ == "__main__":
    test_deobf()
