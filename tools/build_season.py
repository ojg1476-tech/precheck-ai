"""단속 시즌 예보용 데이터 만들기.

data/enforcement/inspections.csv(식약처 점검 발표 25건)와 news.json의 최근 단속 소식을 합쳐
web/season.json을 만든다. 주제마다 '어떤 상품이 해당되는지' 판단할 단어를 붙인다.

    python tools/build_season.py
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 주제별 해당 상품 단어. general=True면 단어와 상관없이 그 분야 전체가 대상(채널·상습 위반 점검 등).
SUMMER_FOOD = ["다이어트", "체지방", "붓기", "슬리밍", "디톡스", "갈증", "지방"]
SUMMER_COS = ["선크림", "선 크림", "자외선", "쿨링", "슬리밍", "셀룰라이트", "제모", "데오"]
THEMES = {
    "I01": dict(kw=[], general=True, tip="체험기·후기를 이용한 광고"),
    "I02": dict(kw=[], general=True, tip="인플루언서 SNS 광고(시술 관련 표현)"),
    "I03": dict(kw=[], general=True, tip="인플루언서 SNS 광고"),
    "I04": dict(kw=["침출차", "티백", "허브티", "[가-힣]+차$"], general=False, tip="침출차 등 차 제품의 효능 표현"),
    "I05": dict(kw=SUMMER_FOOD, general=False, tip="다이어트·체지방 등 여름철 효능 표현"),
    "I06": dict(kw=SUMMER_COS, general=False, tip="자외선·슬리밍 등 여름철 화장품 표현"),
    "I07": dict(kw=["키 성장", "키성장", "성장기", "어린이", "키 크"], general=False, tip="키 성장 효능 표현"),
    "I08": dict(kw=["수험생", "수능", "집중력", "기억력", "두뇌", "총명", "고3", "공부"], general=False, tip="수험생 대상 집중력·기억력 표현"),
    "I09": dict(kw=[], general=True, tip="인정되지 않은 기능성 표방"),
    "I10": dict(kw=[], general=True, tip="온라인 쇼핑몰 식품 광고 전반"),
    "I11": dict(kw=["지방 분해", "셀룰라이트", "스테로이드"], general=True, tip="지방 분해·셀룰라이트·'스테로이드 없음' 등"),
    "I12": dict(kw=[], general=True, tip="숏폼(쇼츠·릴스) 광고"),
    "I13": dict(kw=[], general=True, tip="인정되지 않은 기능성 표방"),
    "I14": dict(kw=["의사", "병원", "피부과", "약사", "클리닉", "더마"], general=False, tip="병원·의사 추천처럼 보이는 표현"),
    "I15": dict(kw=[], general=True, tip="상습 위반 업체 집중 점검"),
    "I16": dict(kw=["염색", "염모", "탈색", "눈썹", "헤어컬러", "브리치"], general=False, tip="염모제·탈색제를 심사 내용과 다르게(눈썹 등) 광고"),
    "I17": dict(kw=SUMMER_FOOD, general=False, tip="휴가철 다이어트·붓기 등 효능 표현"),
    "I18": dict(kw=SUMMER_COS + ["피부과"], general=False, tip="휴가철 화장품, '피부과 전용' 같은 전문가 추천 표현"),
    "I19": dict(kw=["미백", "주름"], general=False, tip="미백·주름 기능성 화장품 광고"),
    "I20": dict(kw=[], general=True, tip="소비자 참여 온라인 광고 점검"),
    "I21": dict(kw=["탈모", "발모", "두피", "모발", "샴푸", "육모"], general=False, tip="탈모 예방·발모 등 의약품 효능 표방"),
    "I22": dict(kw=["선물", "세트", "기프트", "명절"], general=False, tip="명절 선물용 화장품의 의약품 효능 표현"),
    "I23": dict(kw=["면역", "감기", "기관지", "호흡기", "목 건강", "비염"], general=False, tip="환절기 면역·호흡기 효능 표현"),
    "I24": dict(kw=[], general=True, tip="상습 위반 업체 집중 점검"),
    "I25": dict(kw=["질염", "여드름", "여성청결"], general=True, tip="질염 예방·여드름 치료 등 의약품 효능 표현"),
}
DOMAIN = {"화장품": "cos", "식품": "food", "건강기능식품": "hfood"}


def main():
    events = []
    with open(ROOT / "data/enforcement/inspections.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t = THEMES[r["id"]]
            events.append({
                "id": r["id"], "date": r["date"], "domain": DOMAIN[r["domain"]], "theme": r["theme"],
                "total": int(r["total"]) if r["total"] else None, "kw": t["kw"], "general": t["general"],
                "tip": t["tip"], "source": r["source_url"],
            })
    # 데이터셋 이후의 단속 발표(news.json에서 season이 붙은 것)
    news = json.loads((ROOT / "web/news.json").read_text(encoding="utf-8"))
    for n in news["items"]:
        s = n.get("season")
        if not s:
            continue
        events.append({
            "id": n["id"], "date": n["date"], "domain": s["domain"], "theme": s["theme"], "total": s.get("total"),
            "kw": s.get("kw", []), "general": s.get("general", False), "tip": s["tip"], "source": n["url"],
        })
    events.sort(key=lambda e: e["date"])
    out = {"note": "식약처 점검 발표의 시기·주제. 과거에 이 시기에 이런 단속이 있었다는 기록이며 예측이 아니다.",
           "events": events}
    (ROOT / "web/season.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"web/season.json: {len(events)}건")


if __name__ == "__main__":
    main()
