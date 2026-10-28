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
const RV = require('./web/js/relevance.js'), news = require('./web/news.json');
const prods = [
  { name: '수험생 집중 젤리', text: '고3 영양제', productType: 'food' },
  { name: '탈모 케어 샴푸', text: '두피 건강과 탈모 예방', productType: 'cos' },
  { name: '데일리 로션', text: '촉촉한 보습', productType: 'cos' },
];
const P = RV.personalize(prods, { season: sea.events, news }, new Date(2026, 9, 29));
out.newsFor = Object.fromEntries(P.news.filter(n => n.level === '상품').map(n => [n.item.id, n.products.map(p => p.name)]));
out.seasonIds = P.season.map(s => s.e.id);
out.words = RV.titleWords('식약처, 감미료 사용 저당 식품의 혈당 관련 기능성 표시 제한');
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
    assert r["newsFor"].get("N261028") == ["수험생 집중 젤리"], r["newsFor"]
    assert "N260724" not in r["newsFor"], "‘예방’ 같은 일반 단어로 엉뚱한 소식이 붙으면 안 됨"
    assert "N261028" not in r["seasonIds"] and "I08" in r["seasonIds"], r["seasonIds"]
    assert r["words"] == ["감미료", "저당", "혈당"], r["words"]
    print("손실 계산·시즌 예보·맞춤 소식: 통과")


if __name__ == "__main__":
    main()
