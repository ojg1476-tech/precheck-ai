"""단속 소식(web/news.json) 본문에서 따옴표로 인용된 광고 문구를 뽑아 '시험 문구 후보'로 쌓는다.

다음 시험 세트를 만들 재료가 모자라서 만든 도구예요(2026-11-05). 뽑은 문구는 바로 시험에 쓰지 않고
data/candidates/phrases.csv에 '검토 전'으로만 쌓아요. 사람이 보고 광고 문구가 맞는지, 어떤 제품 종류인지 정한 뒤
시험 세트로 고정해요. 이미 데이터에 있는 문구와 한 번 읽은 주소는 건너뛰어요.

GitHub Actions(.github/workflows/news.yml)가 소식 갱신 뒤에 실행한다.

    python tools/collect_phrases.py            # 실제 갱신
    python tools/collect_phrases.py --dry-run  # 무엇이 붙을지만 출력
"""
import csv
import glob
import html
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEWS = ROOT / "web/news.json"
OUT = ROOT / "data/candidates/phrases.csv"
SEEN = ROOT / "data/candidates/seen_urls.txt"
FIELDS = ["date", "cats", "phrase", "status", "title", "url"]
ENFORCE = re.compile(r"적발|부당|위반|단속|점검|과대|허위")
QUOTE = re.compile(r"[‘'\"“「]([^‘’'\"“”「」\n]{2,40})[’'\"”」]")
HANGUL = re.compile(r"[가-힣]")
# 광고 문구가 아닌 인용: 기관·제도·법령 이름, 기사 형식 말
NOT_AD = re.compile(r"식약처|식품의약품안전처|처장|보도|붙임|공정위|위원회|협회|법률|법\b|시행령|시행규칙|고시|가이드|지침|"
                    r"캠페인|사업|센터|시스템|누리집|홈페이지|담당|문의|과장|팀장|\d{2,4}[-.]\d{3,4}")


def log(msg):
    print(msg)
    if os.environ.get("GITHUB_ACTIONS"):
        print("::notice::" + msg.replace("\n", " ")[:900])


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (moonguradar news bot)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def page_text(raw_html):
    """본문만 대략 남긴다: script·style·메뉴(nav·header·footer)를 빼고 태그를 없앤다."""
    t = re.sub(r"(?is)<(script|style|nav|header|footer|noscript)[^>]*>.*?</\1>", " ", raw_html)
    t = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</tr>", "\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"[ \t ]+", " ", t)


def quotes(text):
    """따옴표 안의 짧은 한글 문구. 광고 문구가 아닌 것(기관·법령 이름 등)은 뺀다."""
    out = []
    for m in QUOTE.finditer(text):
        q = m.group(1).strip(" ,.·")
        if len(q) < 2 or not HANGUL.search(q) or NOT_AD.search(q):
            continue
        if q not in out:
            out.append(q)
    return out


def norm(s):
    return re.sub(r"[\s·,.\-‘’'\"“”]", "", s)


def known_phrases():
    seen = set()
    for p in glob.glob(str(ROOT / "data/**/*.csv"), recursive=True):
        try:
            for r in csv.DictReader(open(p, encoding="utf-8")):
                for k in ("text", "phrase"):
                    if r.get(k):
                        seen.add(norm(r[k]))
        except (UnicodeDecodeError, csv.Error):
            continue
    enf = ROOT / "web/enforced.json"
    if enf.exists():
        for ph in json.loads(enf.read_text(encoding="utf-8")).get("phrases", []):
            seen.add(norm(ph["t"]))
    return seen


def main(dry=False):
    items = json.loads(NEWS.read_text(encoding="utf-8"))["items"]
    done = set(SEEN.read_text(encoding="utf-8").split()) if SEEN.exists() else set()
    known = known_phrases()
    rows, read = [], []
    for it in items:
        url = it.get("url", "")
        if not url.startswith("http") or url in done or not ENFORCE.search(it.get("title", "")):
            continue
        try:
            text = page_text(fetch(url))
        except Exception as e:  # 막히거나 없어진 페이지는 다음에 다시 시도
            log(f"[skip] {url}: {e}")
            continue
        read.append(url)
        got = [q for q in quotes(text) if norm(q) not in known]
        for q in got:
            known.add(norm(q))
            rows.append({"date": it.get("date", ""), "cats": ",".join(it.get("cats", [])), "phrase": q, "status": "검토 전",
                         "title": it.get("title", ""), "url": url})
        log(f"[read] {it.get('date')} {it.get('title', '')[:40]} → 새 후보 {len(got)}개: {', '.join(got[:8])}")
    log(f"읽은 보도 {len(read)}건, 새 후보 문구 {len(rows)}개")
    if dry:
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    new_file = not OUT.exists()
    with open(OUT, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        w.writerows(rows)
    if read:
        with open(SEEN, "a", encoding="utf-8") as f:
            f.write("".join(u + "\n" for u in read))
    return 0


if __name__ == "__main__":
    sys.exit(main(dry="--dry-run" in sys.argv))
