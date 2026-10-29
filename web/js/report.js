/* 일괄 점검 결과 → 엑셀 리포트 (precheck/report.py 와 같은 4개 시트). */
(function (root) {
  "use strict";
  const M = root.Moongu || (typeof require !== "undefined" ? require("./engine.js") : null);
  const X = root.MiniXLSX || (typeof require !== "undefined" ? require("./xlsx.js") : null);
  const L = root.MoonguLoss || (typeof require !== "undefined" ? require("./loss.js") : null);
  const RV = root.MoonguRelevance || (typeof require !== "undefined" ? require("./relevance.js") : null);
  const SE = root.MoonguSeason || (typeof require !== "undefined" ? require("./season.js") : null);
  const DOM = { cos: "화장품", food: "식품", hfood: "건강기능식품" };
  const TYPE_NAME = { cos: "일반 화장품", fcos: "기능성 화장품", food: "일반 식품", hfood: "건강기능식품", "": "-" };
  const NOTICE = "이 리포트는 공개된 법령·식약처 기준·실제 단속 사례에 비춰 문제가 될 수 있는 표현을 알려 주는 점검 자료예요. "
    + "법적으로 위반인지 확정하는 판단은 아니며, 최종 확인은 관계 기관이나 전문가에게 받으세요.";
  const STYLES = {
    head: { bold: true, color: "FFFFFF", fill: "0F5B48" }, title: { bold: true, size: 15, wrap: false },
    muted: { color: "5F6B67", wrap: false }, bold: { bold: true, wrap: false }, cell: {},
    "높음": { fill: "FCE8EA", bold: true, color: "B4232F" }, "중간": { fill: "FBF1DF", bold: true, color: "8A5A00" },
    "확인": { fill: "E6EEF8", bold: true, color: "2D64B0" }, "양호": { fill: "E4F2E9", bold: true, color: "2F855A" },
    "오류": { fill: "EEF1EF", bold: true, color: "5F6B67" },
    red: { fill: "FCE8EA", bold: true, color: "B4232F" }, amber: { fill: "FBF1DF", bold: true, color: "8A5A00" }, blue: { fill: "E6EEF8", bold: true, color: "2D64B0" },
  };
  const ORDER = { red: 0, amber: 1, blue: 2 };

  function table(header, rows) { return [header.map(h => ({ v: h, s: "head" })), ...rows.map(r => r.map(v => (v && typeof v === "object") ? v : { v, s: "cell" }))]; }

  /* 맞춤 소식 시트: 다가오는 단속 시즌 + 상품에 해당하는 최신 소식 */
  function personalRows(results, ctx, now) {
    const P = RV.personalize(results, ctx, now), rows = [];
    const names = ps => ps.length > 6 ? ps.slice(0, 6).map(p => p.name).join(", ") + ` 외 ${ps.length - 6}개` : ps.map(p => p.name).join(", ");
    const hits = ps => [...new Set(ps.map(p => p.hit).filter(Boolean))].join(", ");
    for (const { e, products } of P.season) {
      rows.push([{ v: "다가오는 단속 시즌", s: "amber" }, `${SE.soon(e)} (${e.date.slice(0, 4) === String(now.getFullYear()) && e.until < 0 ? "" : "과거 "}${e.date} 발표)`, DOM[e.domain], e.theme, names(products), hits(products),
        e.tip + (e.total ? ` · 당시 ${e.total.toLocaleString("ko-KR")}건 적발` : ""), e.source]);
    }
    for (const { item: n, level, products } of P.news) {
      rows.push([{ v: n.kind === "제도" ? "기준 변경 소식" : "최신 단속 소식", s: n.kind === "제도" ? "blue" : "red" }, n.date,
        n.cats.map(c => DOM[c]).join("·"), n.title, level === "분야" ? `같은 분야 상품 전체 (${products.length}개)` : names(products), hits(products),
        n.summary || "제목만 모은 소식이에요. 출처에서 내용을 확인하세요.", n.url]);
    }
    return { rows, nSeason: P.season.length, nNews: P.news.length };
  }

  function buildReport(results, checker, today = new Date().toLocaleDateString("sv-SE"), ctx = null) {
    const ov = M.overview(results, checker);
    const per = ctx && RV ? personalRows(results, ctx, new Date(today + "T09:00:00")) : null;
    const sum = [[{ v: "상세페이지 광고 일괄 점검 리포트", s: "title" }], [{ v: `점검일 ${today} · 기준 버전 ${checker.version} · 규칙 ${checker.rules.length}개`, s: "muted" }], []];
    sum.push([{ v: "점검한 상품", s: "bold" }, ov.total]);
    for (const [k, v] of Object.entries(ov.tiers)) sum.push([{ v: "위험도 " + k, s: k }, v]);
    sum.push([], [{ v: "여러 상품에서 반복된 문제", s: "bold" }]);
    for (const [name, n] of ov.common) sum.push([name, `${n}개 상품`]);
    if (!ov.common.length) sum.push(["-"]);
    if (per) {
      sum.push([], [{ v: "내 상품에 필요한 소식", s: "bold" }]);
      sum.push([per.rows.length ? `다가오는 단속 시즌 ${per.nSeason}건, 상품에 해당하는 최신 소식 ${per.nNews}건 → ‘맞춤 소식’ 시트에 정리했어요.`
        : "지금은 상품에 해당하는 단속 시즌이나 소식이 없어요."]);
    }
    sum.push([], [{ v: "위험도 뜻", s: "bold" }]);
    for (const t of ["높음: 꼭 고쳐야 할 표현이 하나 이상 있어요.", "중간: 문제가 될 수 있어 확인이 필요한 표현이 있어요.",
      "확인: 쓸 수는 있지만 증명 자료나 인정 여부를 확인해야 하는 표현만 있어요.", "양호: 기본 검사에서 걸린 표현이 없어요.",
      "같은 위험도 안에서는 형사처벌이 무거운 상품이 먼저 와요."]) sum.push([t]);
    sum.push([], [NOTICE]);
    const noticeRow = sum.length;

    const rank = results.map((p, i) => {
      const c = p.counts;
      const st = L ? L.worstStop(p.findings, p.productType) : null;
      return [i + 1, p.name, TYPE_NAME[p.productType] ?? p.productType, { v: p.tier, s: p.tier }, M.penaltyText(p.maxPenalty),
        st ? st.label + (st.scope === "store" ? " (가게 전체)" : "") : "-", c.red, c.amber, c.blue, p.score, p.error || ""];
    });
    const detail = [], E = ctx && ctx.enforced;
    // 같은 규칙에 걸리는 실제 적발 문구 (같은 분야 먼저, 최대 3개)
    const realOf = (f, type) => {
      const ids = E.byRule[f.ruleId]; if (!ids) return "";
      const cos = type === "cos" || type === "fcos", isCos = p => p.type === "cos" || p.type === "fcos";
      return ids.map(i => E.phrases[i]).filter(p => p.t !== f.phrase).sort((a, b) => (isCos(b) === cos) - (isCos(a) === cos) || (b.year || 0) - (a.year || 0))
        .slice(0, 3).map(p => `‘${p.t}’${p.year ? ` (${p.year})` : ""}`).join(", ");
    };
    for (const p of results) {
      for (const f of p.findings.slice().sort((a, b) => ORDER[a.grade] - ORDER[b.grade] || a.start - b.start)) {
        detail.push([p.name, { v: f.gradeName, s: f.grade }, f.phrase, f.label, (f.easy && f.easy !== f.label ? f.easy + "\n" : "") + f.why, f.alt, f.checks.map(c => "□ " + c).join("\n"), f.penalty,
          ...(E ? [realOf(f, p.productType)] : []), f.law, f.source]);
      }
    }
    const basis = [
      "화장품: 화장품법 제13조·제14조·제37조, 시행규칙 별표5(표시·광고 준수사항)·별표7(행정처분 기준), 대한화장품협회 「화장품 광고자문 기준 및 해설서」(2025)",
      "식품: 식품 등의 표시·광고에 관한 법률 제8조·제26조·제27조, 시행령 별표1(부당한 표시·광고의 내용), 시행규칙 별표7(행정처분 기준)",
      "형사처벌은 법에 정해진 최대치예요. 실제 처벌은 사안마다 달라요.",
      "행정처분 기간은 처음 위반했을 때 기준이고, 1년 안에 반복하면 늘어나요. 식품은 판매업 기준이에요.",
      "‘꼭 고치기’는 기준에 금지로 적힌 표현, ‘확인 필요’는 맥락에 따라 위반이 될 수 있는 표현, ‘자료 챙기기’는 증명 자료가 있어야 쓰는 표현이에요.",
      NOTICE,
    ];
    return X.writeWorkbook([
      { name: "요약", rows: sum, widths: [48, 14, 10, 10], merges: [`A${noticeRow}:D${noticeRow}`], heights: { [noticeRow]: 48 } },
      { name: "위험 순위", rows: table(["순위", "상품명", "제품 종류", "위험도", "가장 무거운 형사처벌(최대)", "1차 위반 행정처분", "꼭 고치기", "확인 필요", "자료 챙기기", "점수", "메모"], rank),
        widths: [6, 26, 14, 9, 30, 26, 9, 9, 10, 7, 28], freeze: 1 },
      { name: "상세", rows: table(["상품명", "등급", "찾은 표현", "쉬운 이름", "왜 문제인가", "대신 이렇게", "쓰기 전에 확인할 것", "이대로 두면",
          ...(E ? ["같은 유형 실제 적발 문구"] : []), "관련 기준", "출처"], detail),
        widths: [20, 10, 18, 20, 36, 26, 44, 44, ...(E ? [34] : []), 30, 28], freeze: 1 },
      ...(per ? [{ name: "맞춤 소식", rows: [[{ v: "내 상품에 필요한 소식", s: "title" }],
        [{ v: `${today} 기준 · 다가오는 단속 시즌은 과거 같은 시기의 단속 기록이며 예측이 아니에요.`, s: "muted" }], [],
        ...table(["구분", "날짜·시기", "분야", "제목·주제", "해당 상품", "겹친 표현", "내용", "출처"],
          per.rows.length ? per.rows : [["-", "", "", "지금은 상품에 해당하는 단속 시즌이나 소식이 없어요.", "", "", "", ""]])],
        widths: [16, 22, 12, 40, 30, 16, 52, 40], freeze: 4 }] : []),
      ...(ctx && ctx.ai ? [{ name: "AI 의심 표현", rows: [[{ v: "AI가 한 번 더 찾은 표현", s: "title" }],
        [{ v: "규칙에는 걸리지 않았지만 실제 적발 문구와 뜻이 가까운 구절이에요. 효능을 말하는 표현인지 직접 확인하세요. 건강기능식품은 확인 대상에서 뺐어요.", s: "muted" }], [],
        ...table(["상품명", "의심 구절", "비슷한 실제 적발 문구", "뜻 유사도(0~1)"],
          ctx.ai.length ? ctx.ai.map(h => [h.name, h.text, h.near.t, Math.round((h.sim ?? h.score) * 100) / 100]) : [["-", "더 찾은 표현이 없어요", "", ""]])],
        widths: [24, 30, 34, 10], freeze: 4 }] : []),
      { name: "기준 안내", rows: [[{ v: "이 점검의 기준과 출처", s: "title" }], [], ...basis.map(t => [t])], widths: [110],
        heights: Object.fromEntries(basis.map((_, i) => [i + 3, 36])) },
    ], STYLES);
  }

  const api = { buildReport, TYPE_NAME };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.MoonguReport = api;
})(typeof window !== "undefined" ? window : globalThis);
