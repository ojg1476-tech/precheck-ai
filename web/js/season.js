/* 단속 시즌 예보: 과거 식약처 점검 발표의 시기·주제로 '다가오는 시기에 걸리기 쉬운 표현'을 알려 준다.
   예측이 아니라 '과거 이맘때 이런 단속이 있었다'는 기록이다. */
(function (root) {
  "use strict";
  const DOMAIN_NAME = { cos: "화장품", food: "식품", hfood: "건강기능식품" };
  const DAY = 864e5;

  function domainsFor(type) {
    if (type === "cos" || type === "fcos") return ["cos"];
    if (type === "hfood") return ["food", "hfood"];
    if (type === "food") return ["food"];
    return ["cos", "food", "hfood"];
  }

  /* 단어가 상품명·문구에 있는지. '[가-힣]+차$' 같은 정규식은 상품명에만 쓴다. */
  function kwHit(ev, name, text) {
    const all = `${name} ${text}`;
    for (const k of ev.kw || []) {
      if (/[\[\]$^+]/.test(k)) { if (new RegExp(k).test(name.trim())) return name.trim().split(/\s+/).pop(); }
      else if (all.includes(k)) return k;
    }
    return "";
  }

  /* today 기준으로 그 발표의 '다음 같은 날'까지 남은 날 (지난 back일 이내면 음수) */
  function daysUntil(ev, today, back = 14) {
    const [, m, d] = ev.date.split("-").map(Number);
    let t = new Date(today.getFullYear(), m - 1, d);
    let diff = Math.round((t - today) / DAY);
    if (diff < -back) { t = new Date(today.getFullYear() + 1, m - 1, d); diff = Math.round((t - today) / DAY); }
    return diff;
  }

  function upcoming(events, today = new Date(), ahead = 61, back = 14) {
    const t0 = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    return events.map(e => ({ ...e, until: daysUntil(e, t0, back) }))
      .filter(e => e.until >= -back && e.until <= ahead)
      .sort((a, b) => a.until - b.until || b.date.localeCompare(a.date));
  }

  /* 상품 하나에 해당하는 다가오는 단속: 분야가 맞고, 주제 단어가 상품에 있는 것만 */
  function forProduct(events, p, today) {
    const ds = domainsFor(p.productType || p.type);
    return upcoming(events, today).filter(e => ds.includes(e.domain))
      .map(e => ({ ...e, hit: kwHit(e, p.name || "", p.text || "") })).filter(e => e.hit);
  }

  function when(e) {
    const [y, m, d] = e.date.split("-").map(Number);
    return `${y}년 ${m}월 ${d}일 발표`;
  }
  function soon(e) {
    if (e.until < 0) return new Date() - new Date(e.date) < 30 * DAY ? "최근 발표" : "지금 시기";
    if (e.until <= 7) return "이번 주";
    return `${Math.round(e.until / 7)}주 뒤`;
  }

  const api = { DOMAIN_NAME, domainsFor, kwHit, upcoming, forProduct, when, soon };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.MoonguSeason = api;
})(typeof window !== "undefined" ? window : globalThis);
