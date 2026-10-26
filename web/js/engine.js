/* 문구레이더 검사 엔진 (브라우저·Node 공용).
 * precheck/engine.py · precheck/batch.py 와 같은 규칙·같은 순서로 결과를 낸다 (tests/test_web_parity.py 로 확인).
 * 규칙은 rules.json 하나를 Python과 같이 쓴다. */
(function (root) {
  "use strict";
  const ORDER = { red: 0, amber: 1, blue: 2 };
  const COS = new Set(["cos", "fcos"]);
  const TYPE_ALIASES = {
    cos: "cos", "일반화장품": "cos", "화장품": "cos", fcos: "fcos", "기능성화장품": "fcos",
    food: "food", "일반식품": "food", "식품": "food", hfood: "hfood", "건강기능식품": "hfood", "건기식": "hfood",
  };
  const COLUMN_ALIASES = {
    name: ["상품명", "제품명", "name", "product", "상품"],
    type: ["제품종류", "제품 종류", "종류", "type", "product_type", "구분"],
    text: ["상세문구", "상세페이지 문구", "상세페이지", "문구", "text", "본문", "내용"],
  };
  const PEN_MAX = {
    cA: [1, 1e7], cB: [1, 1e7], cAB: [1, 1e7], cP: [1, 1e7], cX: [1, 1e7],
    f1: [10, 1e8], f2: [10, 1e8], f3: [10, 1e8], f34: [10, 1e8], f4: [5, 5e7], f5: [5, 5e7], fP: [5, 5e7],
  };
  const WEIGHT = { red: 10, amber: 4, blue: 1 };
  const TIER_ORDER = { "높음": 0, "중간": 1, "확인": 2, "양호": 3, "오류": 4 };

  class Checker {
    constructor(data) {
      this.version = data.version;
      this.productTypes = data.product_types;
      this.grades = data.grades;
      this.penalties = data.penalties;
      this.categories = data.categories || {};
      this.rules = data.rules.map(r => ({ ...r, re: new RegExp(r.pattern, "g" + (r.ignore_case ? "i" : "")) }));
    }
    check(text, type = "cos") {
      if (!(type in this.productTypes)) throw new Error("알 수 없는 제품 종류: " + type);
      const isCos = COS.has(type), found = [];
      for (const r of this.rules) {
        if (!r.applies_to.includes(type)) continue;
        r.re.lastIndex = 0;
        let m;
        while ((m = r.re.exec(text))) {
          const raw = m[0];
          if (!raw.trim()) { r.re.lastIndex++; continue; }
          const lead = raw.length - raw.trimStart().length;
          const pen = isCos ? r.penalty_cos : r.penalty_food;
          const cat = (isCos ? r.category_cos : r.category_food) || "";
          found.push({
            start: m.index + lead, end: m.index + raw.length, phrase: raw.trim(), grade: r.grade,
            gradeName: this.grades[r.grade], ruleId: r.id, label: r.label, why: r.why, alt: r.alt, term: r.term,
            law: (isCos ? r.law_cos : r.law_food) || "-", penalty: pen ? (this.penalties[pen] || "") : "",
            source: r.source, category: cat, checks: [...((this.categories[cat] || {}).checks || [])], penaltyKey: pen || "",
          });
        }
      }
      return dedupe(found);
    }
  }

  function dedupe(items) {
    items = items.slice().sort((a, b) => a.start - b.start || ORDER[a.grade] - ORDER[b.grade] || (b.end - b.start) - (a.end - a.start));
    const out = [];
    for (const f of items) {
      const last = out[out.length - 1];
      if (last && f.start < last.end) { if (ORDER[f.grade] < ORDER[last.grade]) out[out.length - 1] = f; continue; }
      out.push(f);
    }
    return out;
  }

  function summarize(fs) {
    const c = { red: 0, amber: 0, blue: 0 };
    for (const f of fs) c[f.grade]++;
    return c;
  }

  function normalizeType(v) {
    const k = String(v || "").replace(/\s/g, "").toLowerCase();
    if (!(k in TYPE_ALIASES)) throw new Error(`제품종류 '${v}'를 알 수 없어요. 일반 화장품, 기능성 화장품, 일반 식품, 건강기능식품 중 하나로 적어 주세요.`);
    return TYPE_ALIASES[k];
  }

  function parseCSV(text) {
    const rows = []; let row = [], cell = "", q = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (q) {
        if (ch === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; }
        else cell += ch;
      } else if (ch === '"') q = true;
      else if (ch === ",") { row.push(cell); cell = ""; }
      else if (ch === "\n" || ch === "\r") {
        if (ch === "\r" && text[i + 1] === "\n") i++;
        row.push(cell); rows.push(row); row = []; cell = "";
      } else cell += ch;
    }
    if (cell !== "" || row.length) { row.push(cell); rows.push(row); }
    return rows;
  }

  /* 2차원 표(첫 줄 = 열 이름) → [{row, name, type, text}] */
  function readRows(rows) {
    rows = rows.map(r => r.map(c => (c == null ? "" : String(c)))).filter(r => r.some(c => c.trim()));
    if (!rows.length) throw new Error("파일이 비어 있어요.");
    const norm = rows[0].map(h => h.replace(/\s/g, "").trim().toLowerCase());
    const idx = {};
    for (const k in COLUMN_ALIASES) {
      idx[k] = null;
      for (const a of COLUMN_ALIASES[k]) { const j = norm.indexOf(a.replace(/\s/g, "").toLowerCase()); if (j >= 0) { idx[k] = j; break; } }
    }
    const missing = Object.keys(idx).filter(k => idx[k] === null).map(k => COLUMN_ALIASES[k][0]);
    if (missing.length) throw new Error(`'${missing.join(", ")}' 칸을 찾지 못했어요. 첫 줄에 상품명, 제품종류, 상세문구 칸 이름을 적어 주세요.`);
    return rows.slice(1).map((r, i) => {
      const get = k => (r[idx[k]] || "").trim();
      return { row: i + 1, name: get("name") || `상품 ${i + 1}`, type: get("type"), text: get("text") };
    });
  }

  class ProductResult {
    constructor(row, name, type, text, findings = [], error = "") {
      Object.assign(this, { row, name, productType: type, text, findings, error });
    }
    get counts() { return summarize(this.findings); }
    get score() { return this.findings.reduce((s, f) => s + WEIGHT[f.grade], 0); }
    get tier() {
      if (this.error) return "오류";
      const c = this.counts;
      return c.red ? "높음" : c.amber ? "중간" : c.blue ? "확인" : "양호";
    }
    get maxPenalty() {
      let best = null;
      for (const f of this.findings) {
        if (f.grade === "blue") continue;
        const p = PEN_MAX[f.penaltyKey];
        if (p && (!best || p[0] > best[0] || (p[0] === best[0] && p[1] > best[1]))) best = p;
      }
      return best;
    }
    sortKey() { const p = this.maxPenalty || [0, 0]; return [TIER_ORDER[this.tier], -p[0], -this.score, this.row]; }
  }

  function checkProducts(items, checker) {
    const out = items.map(it => {
      const pr = new ProductResult(it.row, it.name, "", it.text || "");
      try {
        pr.productType = normalizeType(it.type);
        pr.findings = pr.text ? checker.check(pr.text, pr.productType) : [];
        if (it._err) pr.error = "이미지 읽기 실패: " + String(it._err).slice(0, 80);
        else if (!pr.text) pr.error = "상세 문구가 비어 있어요.";
      } catch (e) { pr.error = e.message; }
      return pr;
    });
    out.sort((a, b) => { const x = a.sortKey(), y = b.sortKey(); for (let i = 0; i < x.length; i++) if (x[i] !== y[i]) return x[i] - y[i]; return 0; });
    return out;
  }

  function overview(results, checker) {
    const tiers = { "높음": 0, "중간": 0, "확인": 0, "양호": 0, "오류": 0 };
    const phrases = new Map();
    for (const r of results) {
      tiers[r.tier]++;
      for (const f of r.findings) {
        if (f.grade === "blue") continue;
        const name = (checker.categories[f.category] || {}).name || f.label;
        if (!phrases.has(name)) phrases.set(name, new Set());
        phrases.get(name).add(r.name);
      }
    }
    const common = [...phrases].map(([k, v]) => [k, v.size]).sort((a, b) => b[1] - a[1]).slice(0, 5);
    return { total: results.length, tiers, common };
  }

  function penaltyText(p) {
    if (!p) return "-";
    const money = p[1] >= 1e8 ? `${p[1] / 1e8}억 원` : `${(p[1] / 1e4).toLocaleString("ko-KR")}만 원`;
    return `징역 ${p[0]}년 이하 또는 벌금 ${money} 이하`;
  }

  const api = { Checker, dedupe, summarize, normalizeType, parseCSV, readRows, ProductResult, checkProducts, overview, penaltyText, PEN_MAX };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.Moongu = api;
})(typeof window !== "undefined" ? window : globalThis);
