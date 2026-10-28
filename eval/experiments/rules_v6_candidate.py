"""규칙 v6 후보: 단어를 하나씩 쫓지 않고 '사전'으로 넓게 깔기.

- 병·증상 사전(약 130개, 몸 부위별) × 효능 동사  → 식품·화장품에서 병을 고친다는 말
- 식약처가 건강기능식품에만 허용한 기능 표현(면역·혈행·기억력·관절 건강 등)  → 일반식품에 쓰면 건강기능식품 오인
- '○○약' 형태와 약·한약 이름  → 의약품 오인
- 염모제 사용 범위 밖(눈썹·속눈썹 등), Before & After, 흉터가 '없어졌다' 같은 후기형 어미
- 앞 실험에서 오탐이 없던 후보(X01, X04, Y02, Y03, Y04)와 범위를 좁힌 키 성장(Y01)

    python eval/experiments/rules_v6_candidate.py
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval/experiments"))
BASE = json.loads((ROOT / "rules/rules.json").read_text(encoding="utf-8"))
by_id = {r["id"]: r for r in BASE["rules"]}
import rules_v5_candidate as v5  # noqa: E402
import rules_v5b_candidate as v5b  # noqa: E402

def like(src, **kw):
    r = copy.deepcopy(by_id[src]); r.update(kw); return r

def alt(words):
    return "|".join(sorted({w.replace(" ", r"\s?") for w in words}, key=len, reverse=True))

DISEASE = """당뇨 고혈압 저혈압 고지혈 고지혈증 이상지질혈증 동맥경화 대사증후군 성인병 통풍 갑상선
심장병 협심증 심근경색 부정맥 뇌졸중 중풍 혈전 하지정맥류 혈관질환 심혈관질환
감기 독감 비염 축농증 천식 기관지염 폐렴 기침 가래 코막힘 인후염 편도염 호흡기질환
위염 위궤양 역류성 식도염 식도염 장염 과민성 대장 변비 설사 치질 치핵 소화불량 지방간 간염 간경화 간질환
관절염 류머티즘 류마티스 골다공증 오십견 디스크 근육통 요통 신경통 관절통 퇴행성
치매 알츠하이머 파킨슨 우울증 불면증 공황장애 ADHD 편두통 어지럼증 이명 건망증 자폐 틱장애
아토피 습진 건선 무좀 대상포진 두드러기 피부염 사마귀 백반증 지루성 원형탈모 탈모 모낭염 습진성
전립선 전립선비대 요실금 방광염 질염 생리통 생리불순 갱년기 난임 불임 발기부전 조루 성조숙증 냉대하
암 항암 종양 빈혈 수족냉증 안구건조증 백내장 녹내장 황반변성 소아비만 비만 알레르기 자가면역 코로나 바이러스 감염""".split()
CLAIM = r"(예방|치료|치유|완치|개선|완화|극복|탈출|방지|해소|퇴치|없애|없어|사라|좋은|좋아|좋습|좋다|효과|효능|도움|관리|케어|잡아|잡는|낫|나아|완쾌|이겨|막아|막는|억제)"
D_NAME = alt(DISEASE).replace(r"(?<![가-힣])", "")
DIS = rf"(?<![가-힣])({D_NAME})(?:증|증상|질환)?(?:이|가|을|를|에|의|도|엔|에는|과|와|으로|로)?(?![가-힣])\s?(\S+\s?){{0,2}}?{CLAIM}"
FUNC = r"(면역|혈행|혈류|혈당|혈압|콜레스테롤|중성지방|체지방|기억력|인지\s?(능력|기능)|집중력|두뇌|간|눈|관절|연골|뼈|치아|잇몸|피부|모발|두피|전립선|요로|질|갱년기|수면|숙면|긴장|스트레스|피로|운동\s?수행|근력|근육|지구력|항산화|정자|배변|장|위|혈관|심장|폐|기관지)" \
       r"\s?(의\s?)?(건강|기능)\s?(개선|강화|증진|향상|유지|보호|회복|에\s?(도움|좋|효과))|" \
       r"(면역|혈행|혈류|기억력|인지\s?력|집중력|지구력|항산화)\s?(력\s?)?(이|을|를)?\s?(개선|강화|증진|향상|높|올려|도와)"
DRUG = r"(다이어트|비만|간장|위장|당뇨|혈압|탈모|발모|수면|정력|두통|변비|감기|기침|관절|치매|공부\s?잘하는|머리카락\s?나는|키\s?크는)\s?(약|치료제|유도제|억제제)(?![가-힣])|수면\s?유도|천연\s?(수면제|진통제|항생제|소화제)"

CANDIDATES = [
    like("R28", id="Z01", label="병을 고친다는 표현(병명 사전)", applies_to=["food", "hfood", "cos"], pattern=DIS),
    like("R04", id="Z02", label="병을 고친다는 표현(병명 사전)", applies_to=["fcos"],
         pattern=DIS.replace("원형탈모|", "").replace("|탈모", "").replace("탈모|", "")),
    like("R31", id="Z03", label="건강기능식품에만 쓸 수 있는 기능 표현", applies_to=["food"], pattern=FUNC),
    like("R30", id="Z04", label="약처럼 부름", pattern=DRUG),
    like("R24", id="Z05", label="염모제를 허가 범위 밖에 쓰는 표현", applies_to=["cos", "fcos"],
         pattern=r"(눈썹|속눈썹|인중|수염|체모|겨드랑이)\s?(을|를|의)?\s?(\S+\s?)?(염색|탈색|브리치|컬러링)|(눈썹|속눈썹)\s?(염색약|탈색제|염모제)"),
    like("R33", id="Z06", grade="amber", label="사용 전후 비교", applies_to=["food", "hfood", "cos", "fcos"],
         pattern=r"before\s?(&|and|/)?\s?after|비포\s?(&|앤)?\s?애프터|(사용|섭취|복용)\s?전\s?(과\s?)?후|전후\s?(비교|사진)", ignore_case=True),
    like("R06", id="Z07", label="흉터·자국이 없어졌다는 표현",
         pattern=r"(흉터|흉|자국|상처|점|기미|잡티)\s?(가|이|도)?\s?(싹\s?|다\s?|완전히\s?)?(없어졌|사라졌|옅어졌|흐려졌|아물었|지워졌)"),
    like("R08", id="Z08", grade="amber", label="시술처럼 채워진다는 표현",
         pattern=r"(꺼진|패인|움푹한)?\s?(이마|볼|팔자|눈밑|애교살|입술)\s?(이|가)?\s?(\S+\s?)?(봉긋|채워져|채워지|차올라|볼륨\s?(이|업))"),
    like("R31", id="Z09", label="머리카락이 난다는 표현", applies_to=["food", "hfood"],
         pattern=r"탈모\s?(를|에|가)?\s?(\S+\s?)?(예방|개선|방지|좋|효과|도움)|발모|모발\s?(성장|생성)|머리카락\s?(이|가)?\s?(나게|나는|난다|새로\s?나|자라|굵어)"),
    like("R31", id="Z10", label="키가 큰다는 표현", applies_to=["food", "hfood"],
         pattern=r"키\s?(가\s?|를\s?)?(성장|크는|쑥쑥|늘어|늘려|촉진|키우|키워)|아이\s?키|키\s?성장|성장\s?호르몬"),
] + [c for c in v5.CANDIDATES if c["id"] in ("X01", "X04")] + [c for c in v5b.CANDIDATES if c["id"] in ("Y02", "Y03", "Y04")]

if __name__ == "__main__":
    cand = copy.deepcopy(BASE)
    cand["rules"] = BASE["rules"] + CANDIDATES
    (ROOT / "eval/experiments/rules_v6_candidate.json").write_text(json.dumps(cand, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"후보 {len(CANDIDATES)}개, 병명 {len(DISEASE)}개")
