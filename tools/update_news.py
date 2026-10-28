"""식약처 보도자료에서 화장품·식품 광고 관련 소식을 모아 web/news.json에 더한다.

GitHub Actions(.github/workflows/news.yml)가 매일 실행한다. 직접 고른 항목(origin=manual)은 건드리지 않고,
새 항목만 origin=auto로 붙인다. 제목만 보고 고르므로 요약은 비워 둔다.

    python tools/update_news.py            # 실제 갱신
    python tools/update_news.py --dry-run  # 무엇이 붙을지만 출력
"""
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEWS = ROOT / "web/news.json"
KST = timezone(timedelta(hours=9))

# 정책브리핑(korea.kr)의 식약처 보도자료 RSS. 첫 번째로 읽히는 것을 쓴다.
FEEDS = [
    ("식약처 보도자료", "https://www.korea.kr/rss/dept_mfds.xml"),
    ("식약처 보도자료", "https://www.korea.kr/rss/pressrelease.xml"),
]
TOPIC = re.compile(r"광고|부당|과대|허위|표시")
FIELD = {
    "cos": re.compile(r"화장품"),
    "hfood": re.compile(r"건강기능식품|영양제"),
    "food": re.compile(r"식품|음료|차\b|다이어트"),
}
MFDS = re.compile(r"식약처|식품의약품안전처")
MAX_ITEMS = 40


import os


def log(msg):
    """Actions에서는 주석(annotation)으로도 남겨 API로 결과를 볼 수 있게 한다."""
    print(msg)
    if os.environ.get("GITHUB_ACTIONS"):
        print("::notice::" + msg.replace("\n", " ")[:900])


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (moonguradar news bot)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def parse(raw):
    root = ET.fromstring(raw)
    for it in root.iter("item"):
        title = html.unescape((it.findtext("title") or "").strip())
        link = (it.findtext("link") or "").strip()
        desc = re.sub(r"<[^>]+>", " ", html.unescape(it.findtext("description") or ""))
        pub = it.findtext("pubDate") or it.findtext("{http://purl.org/dc/elements/1.1/}date") or ""
        try:
            d = parsedate_to_datetime(pub).astimezone(KST).date()
        except Exception:
            try:
                d = datetime.fromisoformat(pub[:10]).date()
            except Exception:
                continue
        yield title, link, desc, d


def pick(title, desc, require_mfds):
    if not TOPIC.search(title):
        return None
    if require_mfds and not MFDS.search(title + " " + desc[:300]):
        return None
    cats = [c for c, rx in FIELD.items() if rx.search(title)]
    if "hfood" in cats and "food" not in cats:
        cats.append("food")
    return sorted(cats, key=["cos", "food", "hfood"].index) or None


def main(dry=False):
    data = json.loads(NEWS.read_text(encoding="utf-8"))
    known = {i["url"] for i in data["items"]} | {re.sub(r"\W", "", i["title"]) for i in data["items"]}
    added, used = [], None
    for name, url in FEEDS:
        try:
            items = list(parse(fetch(url)))
        except Exception as e:  # 피드가 바뀌거나 막히면 다음 후보로
            log(f"[skip] {url}: {e}")
            continue
        used = url
        log(f"[ok] {url}: {len(items)}건")
        for title, link, desc, d in items:
            cats = pick(title, desc, require_mfds=url.endswith("pressrelease.xml"))
            if not cats or link in known or re.sub(r"\W", "", title) in known:
                continue
            kind = "단속" if re.search(r"적발|점검|단속|조치", title) else "제도"
            added.append({"id": f"A{d:%y%m%d}{len(added):02d}", "date": f"{d:%Y-%m-%d}", "cats": cats, "kind": kind,
                          "origin": "auto", "title": title, "summary": "", "url": link, "source": name})
            known |= {link, re.sub(r"\W", "", title)}
        break
    if used is None:
        log("읽을 수 있는 피드가 없어요. news.json은 그대로 둡니다.")
        return 0
    for a in added:
        log(f"[new] {a['date']} {a['cats']} {a['title']}")
    if dry or not added:
        log(f"새 항목 {len(added)}건 (저장 안 함)" if dry else "새 항목 없음")
        return 0
    data["items"] = sorted(data["items"] + added, key=lambda i: i["date"], reverse=True)
    manual = [i for i in data["items"] if i.get("origin") != "auto"]
    auto = [i for i in data["items"] if i.get("origin") == "auto"][: max(0, MAX_ITEMS - len(manual))]
    data["items"] = sorted(manual + auto, key=lambda i: i["date"], reverse=True)
    data["updated"] = datetime.now(KST).strftime("%Y-%m-%d")
    NEWS.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log(f"새 항목 {len(added)}건 저장")
    return 0


if __name__ == "__main__":
    sys.exit(main(dry="--dry-run" in sys.argv))
