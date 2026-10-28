/* 맡긴 상품에 맞춘 소식 고르기.
   - 소식: 소식의 핵심 단어(직접 고른 소식은 지정 단어, 자동 소식은 제목에서 뽑은 단어)가 상품명·문구에 있으면 그 상품에 해당.
     단어가 겹치지 않아도 '제도' 소식(표시 기준 변경 등)은 같은 분야 상품 전체에 해당.
   - 단속 시즌: 앞으로 두 달 안에 과거 같은 주제의 단속이 있었고, 그 주제 단어가 상품에 있으면 해당. */
(function (root) {
  "use strict";
  const SE = root.MoonguSeason || (typeof require !== "undefined" ? require("./season.js") : null);
  const DAY = 864e5;
  // 제목에서 뽑을 때 버리는 일반 단어
  const STOP = new Set(("식약처 식품의약품안전처 광고 부당광고 허위 과대 허위과대 적발 점검 안내 표시 방법 제한 관련 사용 세부 기능성 " +
    "온라인 보도참고 보도자료 식품 일반식품 화장품 건강기능식품 업체 판매 제품 조치 회수 기준 강화 실시 추진 발표 결과 대상 " +
    "개정 시행 의약품 의약외품 의료기기 소비자 주의 당부 집중 합동 특별 위반 추가 이상 이하 대한 위한 통해 예방 치료 효과 효능 건강 개선 도움 협회 업체 판매처 알고 보니").split(" "));
  const JOSA = /(으로|에서|에게|까지|부터|이나|이다|하는|하고|의|을|를|이|가|은|는|에|로|과|와|도|등)$/;

  function titleWords(title) {
    return [...new Set(title.replace(/\[[^\]]*\]/g, " ").split(/[^가-힣A-Za-z0-9]+/)
      .map(w => (w.length > 2 ? w.replace(JOSA, "") : w)).filter(w => w.length >= 2 && !STOP.has(w) && !/^\d+$/.test(w)))];
  }
  function wordsOf(item) { return item.kw || (item.season && item.season.kw) || titleWords(item.title); }

  function forNews(results, items, today = new Date(), days = 365) {
    const out = [];
    for (const n of items) {
      if (today - new Date(n.date) > days * DAY) continue;
      const kw = wordsOf(n), hits = [];
      for (const r of results) {
        if (r.error) continue;
        const ds = SE.domainsFor(r.productType);
        if (!n.cats.some(c => ds.includes(c))) continue;
        const text = `${r.name} ${r.text}`, w = kw.find(k => text.includes(k));
        if (w) hits.push({ name: r.name, hit: w });
      }
      if (hits.length) { out.push({ item: n, level: "상품", products: hits }); continue; }
      if (n.kind === "제도") {   // 기준이 바뀐 소식은 분야 전체에 해당
        const all = results.filter(r => !r.error && n.cats.some(c => SE.domainsFor(r.productType).includes(c)));
        if (all.length) out.push({ item: n, level: "분야", products: all.map(r => ({ name: r.name, hit: "" })) });
      }
    }
    return out.sort((a, b) => (a.level === b.level ? 0 : a.level === "상품" ? -1 : 1) || b.item.date.localeCompare(a.item.date));
  }

  function forSeason(results, events, today = new Date()) {
    const map = new Map();
    for (const r of results) {
      if (r.error) continue;
      for (const e of SE.forProduct(events, r, today)) {
        const k = e.id; if (!map.has(k)) map.set(k, { e, products: [] });
        map.get(k).products.push({ name: r.name, hit: e.hit });
      }
    }
    return [...map.values()].sort((a, b) => a.e.until - b.e.until);
  }

  function personalize(results, ctx = {}, today = new Date()) {
    const news = ctx.news ? forNews(results, ctx.news.items, today) : [];
    const shown = new Set(news.map(n => n.item.id));   // 소식으로 이미 나온 단속은 시즌에서 빼기
    return { news, season: ctx.season ? forSeason(results, ctx.season, today).filter(s => !shown.has(s.e.id)) : [] };
  }

  const api = { titleWords, forNews, forSeason, personalize };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.MoonguRelevance = api;
})(typeof window !== "undefined" ? window : globalThis);
