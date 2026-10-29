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
    f1: [10, 1e8], f2: [10, 1e8], f3: [10, 1e8], f34: [10, 1e8], f4: [5, 5e7], f5: [5, 5e7], f6: [5, 5e7], fP: [5, 5e7],
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
      this.hfood = data.hfood || null;
      if (this.hfood) this.hfood.funcs.forEach(f => (f._re = new RegExp(f.re, "g")));
      this.lastIngredients = []; this.lastProduct = null; this.products = null;
    }
    /* 신고 제품 표(hfood_products.json): 건강기능식품을 검사할 때만 받아서 넣는다 */
    setProducts(data) { this.products = data && this.hfood ? new HfProducts(data, this.hfood) : null; }
    /* ctx: { name: 상품명, no: 품목제조신고번호 } — 건강기능식품일 때 그 제품이 신고한 기능성으로 대조 */
    check(text, type = "cos", ctx = {}) {
      if (!(type in this.productTypes)) throw new Error("알 수 없는 제품 종류: " + type);
      const isCos = COS.has(type); let found = [];
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
      this.lastIngredients = []; this.lastProduct = null;
      if (type === "hfood" && this.hfood) {
        const [extra, ings, prod] = checkHfood(text, this.hfood, this.penalties, ((this.categories.HF || {}).checks) || [], this.products, (ctx && ctx.name) || "", (ctx && ctx.no) || "");
        this.lastIngredients = ings; this.lastProduct = prod;
        if (extra.length) {
          const ok = extra.filter(e => e.ruleId === "H1" || e.ruleId === "H2");
          found = found.filter(f => !((f.category === "HF" && extra.some(e => f.start < e.end && e.start < f.end))
            || (HF_OVERRIDE.has(f.category) && ok.some(e => e._core[0] < f.end && f.start < e._core[1]))));
          for (const e of extra) { const { _core, ...rest } = e; found.push({ ...rest, gradeName: this.grades[e.grade] }); }
        }
      }
      return dedupe(found);
    }
  }

  /* ── 건강기능식품: 원고 속 원료가 그 기능성을 인정받았는지 (precheck/hfood.py 와 같은 판정) ── */
  const HF_SKIP = /[\s·․ㆍ・\-_,./®ⓡⓇ™()\[\]{}'"“”‘’:;]/;
  const HF_CLAIM = /도움|도와|돕|끝|걱정\s?없|해방|싹|쏙|개선|강화|감소|증진|향상|완화|해소|해결|예방|치료|효과|효능|낮춰|낮추|낮아|빠지|빠져|빠졌|줄었|나아|빼|좋아|좋은|튼튼|지켜|책임|확실|보장|회복|잡아|불태|태워|쑥쑥/;
  const HF_CLAUSE = /[.!?\n,·]/g;
  const HF_OVERRIDE = new Set(["F1", "F3", "F4", "HF"]);
  const HF_EXCIPIENT = ["스테아린산", "셀룰로스", "셀룰로오스", "글리세린", "카복시메틸"];
  const HF_LAW = "식품표시광고법 제8조 제1항 제4호 (인정받지 않은 기능성), 건강기능식품 기능성 원료 인정 내용";
  const isAlnumAscii = c => /[a-z0-9]/i.test(c);

  function hfIngredients(text, kb) {
    let s = ""; const idx = [];
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (HF_SKIP.test(ch)) continue;
      s += ch.charCodeAt(0) < 128 ? ch.toLowerCase() : ch; idx.push(i);
    }
    const taken = [], out = [];
    for (const [key, items] of kb.keys) {
      const ascii = /^[\x00-\x7f]*$/.test(key);
      let from = 0;
      for (;;) {
        const j = s.indexOf(key, from);
        if (j < 0) break;
        from = j + 1;
        const e = j + key.length;
        const before = s.slice(Math.max(0, j - 6), j);
        if (HF_EXCIPIENT.some(x => before.endsWith(x))) continue;   // 스테아린산마그네슘·카복시메틸셀룰로스칼슘 같은 첨가물
        const a0 = idx[j], b0 = idx[e - 1] + 1;   // 영문 원료명은 원문에서 앞뒤가 영문·숫자로 이어지면 다른 낱말
        if (ascii && ((a0 > 0 && isAlnumAscii(text[a0 - 1])) || (b0 < text.length && isAlnumAscii(text[b0])))) continue;
        if (taken.some(([a, b]) => j < b && a < e)) continue;
        taken.push([j, e]);
        out.push({ start: idx[j], end: idx[e - 1] + 1, key, items: items.slice() });
      }
    }
    return out.sort((a, b) => a.start - b.start);
  }
  function hfFuncs(text, kb) {
    const taken = [], out = [];
    for (const f of kb.funcs) {
      f._re.lastIndex = 0; let m;
      while ((m = f._re.exec(text))) {
        const a = m.index, b = a + m[0].length;
        if (b === a) { f._re.lastIndex++; continue; }
        if (taken.some(([x, y]) => a < y && x < b)) continue;
        taken.push([a, b]); out.push({ start: a, end: b, id: f.id });
      }
    }
    return out.sort((a, b) => a.start - b.start);
  }
  function hfJoin(names, n = 3) {
    names = [...new Set(names)];
    return names.slice(0, n).join(", ") + (names.length > n ? ` 외 ${names.length - n}개` : "");
  }
  const HF_NO = /(?<!\d)(?:19|20)\d{10,13}(?!\d)/g;
  const HF_LAW_P = "식품표시광고법 제8조 제1항 제4호 (신고하지 않은 기능성), 건강기능식품 품목제조 신고 내용";
  const hfNorm = t => { let s = ""; for (const ch of t) { if (HF_SKIP.test(ch)) continue; s += ch.charCodeAt(0) < 128 ? ch.toLowerCase() : ch; } return s; };
  /* 쇼핑몰 상품명에서 꾸밈말(대괄호, 1+1, 60정, 2박스 …)을 뺀다 (precheck/hfood.py clean_listing 과 같음) */
  const HF_DECOR = /\[[^\]]*\]|\([^)]*\)|【[^】]*】|무료\s?배송|당일\s?발송|선물\s?세트|기획\s?세트|정품|\d+\s?\+\s?\d+|[x×*]\s?\d+|\d+(\.\d+)?\s?(정|포|캡슐|알|병|개월분?|일분|박스|box|개입?|팩|통|세트|ml|mg|g|kg|l)(?![가-힣a-z])/gi;
  const hfCleanListing = n => n.replace(HF_DECOR, " ");
  class HfProducts {
    constructor(data, kb) {
      const tags = data.claims.map(c => hfFuncs(c, kb).map(x => x.id));
      this.items = []; this.byNo = new Map(); this.byName = new Map();
      for (const [no, name, ids] of data.p) {
        const f = [];
        for (const i of ids) for (const t of tags[i]) if (!f.includes(t)) f.push(t);
        this.byNo.set(no, this.items.length);
        const k = hfNorm(hfCleanListing(name));
        if (k.length >= 4) { if (!this.byName.has(k)) this.byName.set(k, []); this.byName.get(k).push(this.items.length); }
        this.items.push({ no, n: name, c: ids.map(i => data.claims[i]), f });
      }
      this.names = [...this.byName.keys()].sort((a, b) => b.length - a.length || (a < b ? -1 : a > b ? 1 : 0));
    }
    find(text, name = "", no = "") {
      const cands = (no ? [String(no).replace(/\D/g, "")] : []).concat(text.match(HF_NO) || []);
      for (const c of cands) if (this.byNo.has(c)) return [this.byNo.get(c)];
      const k = hfNorm(hfCleanListing(name || ""));
      if (k.length >= 4) {
        if (this.byName.has(k)) return this.byName.get(k).slice();
        for (const nk of this.names) if (nk.length >= 6 && nk.length * 2 >= k.length && k.includes(nk)) return this.byName.get(nk).slice();
      }
      return [];
    }
  }

  function checkHfood(text, kb, penalties, checks, products = null, name = "", no = "") {
    const ings = hfIngredients(text, kb);
    const pids = products ? products.find(text, name, no) : [];
    let prod = null;
    if (pids.length) {
      const ps = pids.map(i => products.items[i]), f = [], c = [];
      for (const p of ps) { for (const t of p.f) if (!f.includes(t)) f.push(t); for (const x of p.c) if (!c.includes(x)) c.push(x); }
      prod = { no: ps[0].no, n: ps[0].n, c, f, count: ps.length };
    }
    if (!ings.length && !prod) return [[], [], null];
    const items = kb.items, fname = {}, parents = {};
    for (const f of kb.funcs) { fname[f.id] = f.name; parents[f.id] = f.parent.split(",").filter(Boolean); }
    const tagCache = kb._tags || (kb._tags = new Map());
    const tagsOf = c => { if (!tagCache.has(c)) tagCache.set(c, hfFuncs(c, kb).map(x => x.id)); return tagCache.get(c); };
    const sat = (it, fid) => it.f.some(t => t === fid || parents[t].includes(fid));
    const exactOf = (it, fid) => {
      const hits = it.c.filter(c => tagsOf(c).some(t => t === fid || parents[t].includes(fid)));
      return hits.length ? hits.reduce((a, b) => (b.length < a.length ? b : a)) : it.c[0];
    };
    const out = [];
    for (const fm of hfFuncs(text, kb)) {
      const fid = fm.id;
      HF_CLAUSE.lastIndex = fm.end; const m = HF_CLAUSE.exec(text);
      const cend = m ? m.index : text.length;
      let cstart = 0; for (let i = fm.start - 1; i >= 0; i--) if (/[.!?\n,·]/.test(text[i])) { cstart = i + 1; break; }
      const clause = text.slice(cstart, cend), end = Math.min(cend, fm.end + 20);
      const full = [], part = [], partOk = [];
      for (const g of ings) {
        const ok = g.items.filter(i => sat(items[i], fid));
        if (ok.length && ok.length === g.items.length) full.push(g);
        else if (ok.length) { part.push(g); partOk.push(...ok); }
      }
      const claim = HF_CLAIM.test(clause);
      if (prod) {
        const base = { start: fm.start, end, phrase: text.slice(fm.start, end).trim(), source: "식품안전나라 건강기능식품 품목제조 신고사항",
          category: "HF", checks: [...checks], _core: [fm.start, fm.end], term: "", law: HF_LAW_P, penaltyKey: "f4", penalty: penalties.f4 || "" };
        const label = `‘${prod.n}’(신고번호 ${prod.no})` + (prod.count > 1 ? ` 등 같은 이름 제품 ${prod.count}개` : "");
        if (sat(prod, fid)) {
          const exact = exactOf(prod, fid);
          if (claim && !/도움|도와|돕|필요/.test(clause)) out.push({ ...base, grade: "amber", ruleId: "H2", label: "신고 문구보다 세게 말함",
            why: `${label}은(는) ‘${fname[fid]}’ 기능성을 신고했지만, 신고 문구는 ‘${exact}’예요. ‘개선’, ‘효과’처럼 단정하면 신고 범위를 넘는 광고가 돼요.`,
            alt: exact, term: "신고한 기능성 범위를 넘는 표시·광고" });
          else out.push({ ...base, grade: "blue", ruleId: "H1", label: "제품이 신고한 기능성",
            why: `${label}은(는) ‘${exact}’로 신고된 제품이에요. 이 문구 그대로 쓰고, 협회 심의를 받은 내용인지 확인하세요.`,
            alt: exact, term: "신고한 기능성 표시 (신고 문구 그대로)", penaltyKey: "", penalty: "" });
        } else {
          const have = [];
          for (const t of prod.f) if (!have.includes(fname[t])) have.push(fname[t]);
          const strong = claim || /도움|도와|돕|필요/.test(clause);
          out.push({ ...base, grade: strong ? "red" : "amber", ruleId: strong ? "H6" : "H7",
            label: strong ? "제품이 신고하지 않은 기능성" : "신고하지 않은 기능을 떠올리게 함",
            why: `${label}이(가) 신고한 기능성은 ‘${hfJoin(have, 4)}’예요. ‘${fname[fid]}’ 기능성은 신고하지 않았어요. 원료에 그 기능이 있어도 제품으로 신고하지 않았으면 광고할 수 없어요.`,
            alt: `(신고한 기능성만: ${prod.c[0]})`, term: "신고하지 않은 기능성 표시·광고" });
        }
        continue;
      }
      const base = { start: fm.start, end, phrase: text.slice(fm.start, end).trim(), source: "식품안전나라 건강기능식품 기능성 원료 인정 내용",
        category: "HF", checks: [...checks], _core: [fm.start, fm.end], term: "", law: HF_LAW, penaltyKey: "f4", penalty: penalties.f4 || "" };
      if (full.length) {
        const it = items[full[0].items[0]], exact = exactOf(it, fid), nm = text.slice(full[0].start, full[0].end);
        if (claim && !/도움|도와|돕|필요/.test(clause)) out.push({ ...base, grade: "amber", ruleId: "H2", label: "인정 문구보다 세게 말함",
          why: `‘${nm}’은(는) ‘${fname[fid]}’ 기능성을 인정받았지만, 인정 문구는 ‘${exact}’예요. ‘개선’, ‘효과’처럼 단정하면 인정 범위를 넘는 광고가 돼요.`,
          alt: exact, term: "인정받은 기능성 범위를 넘는 표시·광고" });
        else out.push({ ...base, grade: "blue", ruleId: "H1", label: "원료가 인정받은 기능성",
          why: `‘${nm}’은(는) 식약처에서 ‘${exact}’로 인정받은 원료예요. 이 문구 그대로 쓰고, 협회 심의를 받은 내용인지 확인하세요.`,
          alt: exact, term: "인정받은 기능성 표시 (인정 문구 그대로)", penaltyKey: "", penalty: "" });
      } else if (part.length) {
        const g = part[0], nm = text.slice(g.start, g.end);
        out.push({ ...base, grade: "amber", ruleId: "H3", label: "원료 종류에 따라 다른 기능성",
          why: `‘${nm}’ 원료 중 일부(${hfJoin(partOk.map(i => items[i].n))})만 ‘${fname[fid]}’ 기능성을 인정받았어요. 제품에 든 원료가 정확히 그 원료인지 원료명(균주·제품 코드까지)으로 확인하세요.`,
          alt: exactOf(items[partOk[0]], fid), term: "원료별로 다른 인정 기능성" });
      } else {
        const names = ings.map(g => text.slice(g.start, g.end)), have = [];
        for (const g of ings) for (const i of g.items) for (const t of items[i].f) if (!have.includes(fname[t])) have.push(fname[t]);
        const it0 = items[ings[0].items[0]];
        out.push({ ...base, grade: claim ? "red" : "amber", ruleId: claim ? "H4" : "H5",
          label: claim ? "원료가 인정받지 않은 기능성" : "인정받지 않은 기능을 떠올리게 함",
          why: `원고에서 찾은 원료(${hfJoin(names)})가 인정받은 기능성은 ‘${hfJoin(have, 4)}’예요. ‘${fname[fid]}’ 기능성은 인정받지 않았어요. 다른 기능성 원료가 들어 있다면 그 원료의 인정 내용을 확인하세요.`,
          alt: `(인정받은 기능성만: ${it0.c[0]})`, term: "인정받지 않은 기능성 표시·광고" });
      }
    }
    return [out, ings.map(g => ({ name: text.slice(g.start, g.end), items: g.items.map(i => items[i].n).slice(0, 5) })),
      prod ? { no: prod.no, name: prod.n, count: prod.count, claims: prod.c.slice(0, 12) } : null];
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
        pr.findings = pr.text ? checker.check(pr.text, pr.productType, { name: pr.name }) : [];
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

  const api = { Checker, checkHfood, HfProducts, dedupe, summarize, normalizeType, parseCSV, readRows, ProductResult, checkProducts, overview, penaltyText, PEN_MAX };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.Moongu = api;
})(typeof window !== "undefined" ? window : globalThis);
