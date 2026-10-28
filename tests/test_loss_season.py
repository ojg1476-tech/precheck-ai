"""손실 계산·시즌 예보 점검 (node로 웹 모듈을 직접 실행)."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = r"""
const L = require('./web/js/loss.js'), SE = require('./web/js/season.js');
const rules = require('./web/rules.json'), sea = require('./web/season.json');
const keys = Object.keys(rules.penalties);
const missing = keys.filter(k => !(k in L.STOP) && !L.NO_DAYS.includes(k));
const f = (k, g = 'red') => ({ penaltyKey: k, grade: g });
const out = {
  missing,
  hfood: L.worstStop([f('f2')], 'hfood').max, food: L.worstStop([f('f2')], 'food').max,
  worst: L.worstStop([f('f3'), f('f1')], 'food').label, blue: L.worstStop([f('f1', 'blue')], 'food'),
  money: L.lossText({ min: 15, max: 15 }, 300000), range: L.lossText({ min: 60, max: 90 }, 100000),
  exam: SE.forProduct(sea.events, { name: '수험생 집중력 젤리', text: '', productType: 'food' }, new Date(2026, 10, 1)).map(e => e.id),
  cosNoFood: SE.forProduct(sea.events, { name: '수험생 집중력 크림', text: '', productType: 'cos' }, new Date(2026, 10, 1)).length,
  tea: SE.kwHit({ kw: ['[가-힣]+차$'] }, '레몬 생강차', ''),
};
console.log(JSON.stringify(out));
"""


def main():
    r = json.loads(subprocess.run(["node", "-e", JS], cwd=ROOT, capture_output=True, text=True, check=True).stdout)
    assert r["missing"] == [], f"처분 기간 표에 없는 처분 키: {r['missing']}"
    assert (r["food"], r["hfood"]) == (15, 30), r
    assert r["worst"] == "영업정지 2개월", r
    assert r["blue"] is None, r
    assert r["money"] == "450만 원" and r["range"] == "600만 원~900만 원", r
    assert "I08" in r["exam"], r
    assert r["cosNoFood"] == 0, r
    assert r["tea"] == "생강차", r
    print("손실 계산·시즌 예보: 통과")


if __name__ == "__main__":
    main()
