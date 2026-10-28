"""규칙 v5b 후보: 놓친 '주제'를 넓히기.

개발용으로 쓴 것: 고정 후 모았던 묶음 17개(data/test5_batches.csv)에서 놓친 주제와 법령의 금지 유형.
시험 세트 6은 이 파일을 고정(커밋)한 **뒤에** 새로 모은다.

    python eval/experiments/rules_v5b_candidate.py   # 후보 규칙 파일 만들기
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = json.loads((ROOT / "rules/rules.json").read_text(encoding="utf-8"))
by_id = {r["id"]: r for r in BASE["rules"]}


def like(src, **kw):
    r = copy.deepcopy(by_id[src]); r.update(kw); return r


CANDIDATES = [
    # 키 성장 (식품·건강기능식품 모두 인정된 기능성이 없음)
    like("R31", id="Y01", label="키가 큰다는 표현", applies_to=["food", "hfood"],
         pattern=r"키\s?(가\s?|를\s?)?(성장|크[는고게기]|커[요서지졌]|자라|쑥쑥|늘어|늘려|촉진|키[우워])|아이\s?키|키\s?성장|성장\s?호르몬"),
    # 아이·여성·남성 질환 이름
    like("R28", id="Y02",
         pattern=r"성조숙증|소아\s?비만|비만\s?(을\s?)?(예방|치료|개선|탈출)|난임|불임|발기\s?부전|생리\s?불순|수족\s?냉증|요실금|방광염|야뇨증|성장\s?장애"),
    # 몸 치수가 바뀌었다는 후기 (식품·화장품)
    like("R33", id="Y03", label="몸 치수가 바뀌었다는 후기", applies_to=["food", "hfood", "cos", "fcos"],
         pattern=r"\d+(\.\d+)?\s?(센치|센티|cm|㎝|kg|키로|킬로|인치)\s?(에서|→|->|에서\s?지금)\s?(\S+\s?){0,3}\d+(\.\d+)?\s?(센치|센티|cm|㎝|kg|키로|킬로|인치)?|"
                 r"\d+(\.\d+)?\s?(kg|키로|킬로|센치|cm)\s?(이나\s?|나\s?|가\s?)?(빠졌|빠짐|감량|뺐|줄었|컸|자랐|늘었)"),
    # 화장품: 노폐물 배출·부종 (피부·모공 노폐물 ‘제거’는 세정 표현이라 허용 — 개발용 허용 예시에서 확인)
    like("R08", id="Y04", label="몸속 작용처럼 보이는 표현",
         pattern=r"노폐물\s?(을|를|이|가)?\s?(배출|빼|빠져|녹여)|부종|붓기\s?(를|가)?\s?(빼|빠|제거|완화|개선|감소|관리|케어|도움)"),
    # 식품: 소화·속 편함 (거짓·과장 가능, 확인 필요)
    like("R37", id="Y05", grade="amber", label="소화·속이 편해진다는 표현", applies_to=["food"],
         pattern=r"소화\s?(가|를|도)?\s?(잘\s?(되|돼)|돕|도와|촉진|개선)|속\s?(이|을|도)?\s?(편한|편안|편하게|편해)|더부룩"),
]

if __name__ == "__main__":
    cand = copy.deepcopy(BASE)
    cand["rules"] = BASE["rules"] + CANDIDATES
    (ROOT / "eval/experiments/rules_v5b_candidate.json").write_text(json.dumps(cand, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"후보 {len(CANDIDATES)}개 → eval/experiments/rules_v5b_candidate.json")
