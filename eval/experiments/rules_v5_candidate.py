"""규칙 v5 후보 실험: 말을 바꿔 쓴 표현(우회 표현)을 잡는 규칙을 '확인 필요' 위주로 더해 본다.

원칙
- 시험 세트 4(data/test4.csv)를 고정한 뒤에 썼다. 놓친 문구 목록은 보지 않았다.
- 시험 세트 4에만 나오는 고유한 단어(제품명, 가린 글자 등)는 넣지 않았다.
- 다만 시험 세트 4를 만든 사람이 같은 사람이라 문구를 이미 본 상태다. 그래서 진짜 확인은
  고정 이후 새로 모이는 단속 소식(시험 세트 5)으로 다시 한다.

    python eval/experiments/rules_v5_candidate.py
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))
from evaluate import run, metrics  # noqa: E402

BASE = json.loads((ROOT / "rules/rules.json").read_text(encoding="utf-8"))
by_id = {r["id"]: r for r in BASE["rules"]}


def like(src, **kw):
    r = copy.deepcopy(by_id[src])
    r.update(kw)
    return r


CANDIDATES = [
    # 식품: 몸의 기능을 '높이고·되살린다'는 말 바꾸기 (건강기능식품처럼 보임)
    like("R31", id="X01", grade="amber", label="몸의 기능을 높인다는 표현",
         pattern=r"(집중\s?력|기억\s?력|인지\s?력|두뇌\s?(활동|회전)?|지구력|체력|면역\s?력?|혈행|혈류|숙면|수면\s?(의\s?)?질|피로|스태미나|정력|근력|몰입\s?력?)"
                 r"\s?(을|를|이|가|도|과|와)?\s?(\S+\s?)?(높여|높이|높아|올려|올리|끌어\s?올|향상|증진|강화|회복|도와|돕|키워|키우|쑥쑥|팍팍|UP|업)",
         applies_to=["food"]),
    # 식품: 병 이름 넓히기 (정신·신경·만성 질환)
    like("R28", id="X02",
         pattern=r"(불안\s?장애|공황|주의력\s?결핍|과잉\s?행동|틱\s?장애|자폐|알츠하이머|파킨슨|뇌졸중|중풍|협심증|부정맥|지방간|간염|위염|장염|과민성\s?대장|"
                 r"갱년기\s?(증상|장애)|생리통|요실금|녹내장|백내장|안구\s?건조|이명|편두통|두통|수면\s?장애|천식|대상포진|헤르페스|동맥\s?경화|혈전|류머티즘|디스크)"
                 r"\s?(을|를|이|가|에|의)?\s?(\S+\s?)?(예방|치료|개선|완화|극복|없애|잡아|해결|도움|효과|좋)"),
    # 식품: 약·한약 처방 이름을 빌려 씀
    like("R30", id="X03", pattern=r"경옥고|우황\s?청심|쌍화탕|십전대보|녹용\s?대보|비아그라|시알리스|타이레놀|아스피린|인슐린|항생제|진통제|수면제|신경\s?안정제|해열제"),
    # 화장품: 손상·흔적을 되돌린다는 말 바꾸기
    like("R06", id="X04",
         pattern=r"(손상된|상한|망가진|다친)\s?(피부|모발|두피|머릿결)\s?(을|를|이|가)?\s?(\S+\s?)?(개선|회복|복구|치유|되살|재건|살려)|"
                 r"(흉터|흉|상처|자국|홍반|붉은\s?반점|멍)\s?(을|를|이|가)?\s?(\S+\s?)?(옅어|옅게|흐려|없어|사라|감소|줄여|완화|개선)"),
    # 화장품: 통증·근육·피로 (몸에 작용하는 효과)
    like("R09", id="X05",
         pattern=r"(통증|결림|뭉침|근육통|관절통|신경통|생리통|두통)\s?(을|를|이|가)?\s?(\S+\s?)?(완화|해소|개선|줄여|없애|풀어)|근육\s?(을|의)?\s?(이완|회복|풀어)|피로\s?(회복|해소)"),
    # 식품: 먹기만 하면 바로 효과
    like("R17", id="X06", grade="amber", label="먹기만 하면 바로 효과가 난다는 표현",
         pattern=r"(먹|마시|섭취)[가-힣]{0,3}\s?(만으로|만\s?해도|즉시|바로|직후)\s?(\S+\s?){0,2}(효과|달라|변화|높|빠|개선)", applies_to=["food", "hfood"]),
]


def main():
    cand = copy.deepcopy(BASE)
    cand["rules"] = BASE["rules"] + CANDIDATES
    out = ROOT / "eval/experiments/rules_v5_candidate.json"
    out.write_text(json.dumps(cand, ensure_ascii=False, indent=1), encoding="utf-8")
    rows = []
    for split in ["test4", "test3", "test2", "all"]:
        m0, m1 = metrics(run(split)[1]), metrics(run(split, rules=str(out))[1])
        f = lambda m, k: f"{m[k][0]}/{m[k][1]} ({m[k][0] / m[k][1] * 100:.1f}%)" if m[k][1] else "-"
        rows.append((split, f(m0, "strong_recall"), f(m1, "strong_recall"), f(m0, "fp_rate"), f(m1, "fp_rate")))
    print("| 세트 | v4 탐지 | v5 후보 탐지 | v4 오탐 | v5 후보 오탐 |")
    print("| --- | --- | --- | --- | --- |")
    for r in rows:
        print("| " + " | ".join(r) + " |")


if __name__ == "__main__":
    main()
