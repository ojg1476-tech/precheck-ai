// 실제 적발 데이터 → web/enforced.json
// - 연도별 적발 건수(국정감사 자료 인용 보도), 유형별 건수
// - 보도에 인용된 실제 적발 문구와, 그 문구가 걸리는 규칙(같은 유형 사례로 보여 주기 위함)
//     node tools/build_enforced.js
const fs = require("fs"), path = require("path");
const ROOT = path.join(__dirname, "..");
const M = require(path.join(ROOT, "web/js/engine.js"));
const ck = new M.Checker(JSON.parse(fs.readFileSync(path.join(ROOT, "web/rules.json"), "utf8")));
const csv = f => M.parseCSV(fs.readFileSync(path.join(ROOT, "data/enforcement", f), "utf8"));
const rows = f => { const [h, ...rs] = csv(f); return rs.filter(r => r.length > 1).map(r => Object.fromEntries(h.map((k, i) => [k, r[i] ?? ""]))); };
const host = u => { try { return new URL(u).hostname.replace(/^www\.|^m\./, ""); } catch (e) { return ""; } };
const DOM = { "식품": "food", "화장품": "cos", "건강기능식품": "hfood" };

const yearly = rows("yearly.csv").map(r => ({ domain: DOM[r.domain], year: +r.year, months: +r.months, n: +r.violations, src: r.source_url }));
const types = rows("yearly_types.csv").map(r => ({ domain: DOM[r.domain], period: r.period, type: r.type, n: +r.violations, src: r.source_url }));
const phrases = [], byRule = {};
for (const r of rows("phrases.csv")) {
  const rules = [...new Set(ck.check(r.text, r.product_type).filter(f => f.grade !== "blue").map(f => f.ruleId))];
  const i = phrases.push({ t: r.text, type: r.product_type, cat: r.category, year: r.year ? +r.year : null, src: r.source_url, site: host(r.source_url) }) - 1;
  for (const id of rules) (byRule[id] = byRule[id] || []).push(i);
}
const out = { note: "적발 건수는 국정감사 자료를 인용한 보도, 문구는 식약처 발표를 인용한 보도에서 모은 것.", yearly, types, phrases, byRule };
fs.writeFileSync(path.join(ROOT, "web/enforced.json"), JSON.stringify(out) + "\n");
console.log(`web/enforced.json: 연도 ${yearly.length}, 유형 ${types.length}, 문구 ${phrases.length} (규칙에 걸린 문구 ${new Set(Object.values(byRule).flat()).size})`);
