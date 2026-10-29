"""건강기능식품 원료별 '인정받은 기능성' 표 만들기.

입력: data/hfood/raw/*.json (식품안전나라 OpenAPI 원본 — .github/workflows/fetch_hfood.yml 이 받음)
  - I2710  건강기능식품 품목분류정보 (원료명 PRDCT_NM, 주된 기능성 PRIMARY_FNCLTY)
  - I-0050 개별인정형 정보 (RAWMTRL_NM, PRIMARY_FNCLTY, 인정번호)
  - I-0040 기능성 원료인정현황 (APLC_RAWMTRL_NM, FNCLTY_CN, 인정번호)
출력: rules/hfood.json — tools/export_rules.js 가 rules.json 의 "hfood" 로 넣는다.

기능성은 원문 문구를 그대로 두고, 비교용으로 '기능 분류'(체지방, 간 건강 …)를 붙인다.
분류 정규식은 원고 쪽에도 똑같이 쓰인다 (web/js/engine.js · precheck/engine.py).
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "hfood" / "raw"
OUT = ROOT / "rules" / "hfood.json"

# 기능 분류: [코드, 쉬운 이름, 정규식, 상위 분류]
#  - 위에 있는 것이 먼저 잡힌다(같은 자리에서 겹치면 위의 것만). 구체적인 것을 위에 둔다.
#  - 상위 분류가 있는 것(eye_macula 등): 원고에 '눈 건강'처럼 상위만 쓰면 하위 중 하나만 인정받아도 통과.
FUNCS = [
    ["eye_fatigue", "눈의 피로", r"눈\s?의?\s?피로", "eye"],
    ["eye_dry", "건조한 눈", r"건조한\s?눈|안구\s?건조|눈\s?건조", "eye"],
    ["eye_macula", "황반색소밀도", r"황반", "eye"],
    ["eye", "눈 건강", r"눈\s?(건강|영양|보호)|시력|시각|눈이\s?(편|밝|맑)", ""],
    ["skin_uv", "자외선에 의한 피부 손상", r"자외선|햇볕", "skin"],
    ["skin_immune", "면역과민반응에 의한 피부 상태", r"과민\s?반응에\s?의한\s?피부|피부\s?과민|가려운\s?피부", "skin,allergy"],
    ["skin_moist", "피부 보습", r"피부\s?(의\s?)?(보습|수분|건조)|보습", "skin"],
    ["skin_wrinkle", "피부 주름·탄력", r"피부\s?(의\s?)?(주름|탄력)|주름|탄력", "skin"],
    ["skin", "피부 건강", r"피부\s?(건강|상태|개선|노화|미용)|피부와\s?점막|피부가\s?(좋아|맑아|촉촉)", ""],
    ["nose", "면역과민반응에 의한 코 상태", r"코\s?상태|코\s?가려움|재채기|콧물|코\s?막힘", "allergy"],
    ["allergy", "면역 과민반응", r"면역\s?과민|과민\s?반응|알레르기|알러지", ""],
    ["immune", "면역", r"면역\s?(력|기능|증진|강화|세포|체계|건강)?(?!\s?과민)", ""],
    ["bodyfat", "체지방 감소", r"체지방|내장\s?지방|복부\s?지방|뱃살|지방\s?(합성|축적|연소|분해)|체중\s?(감량|감소|조절|관리)|다이어트|살\s?(이\s?)?빠", ""],
    ["tg", "혈중 중성지방", r"중성\s?지(방|질)", ""],
    ["cholesterol", "혈중 콜레스테롤", r"콜레스테롤", ""],
    ["bloodsugar", "혈당", r"혈당", ""],
    ["bp", "혈압", r"혈압", ""],
    ["bloodflow", "혈행", r"혈행|혈액\s?(순환|흐름)|혈소판|혈관|피가\s?맑", ""],
    ["liver", "간 건강", r"간\s?(건강|기능|보호|손상|피로|해독|수치)|간을\s?(보호|지켜)|알코올|알콜|숙취", ""],
    ["memory", "기억력·인지기능", r"기억력|인지\s?(기능|능력|력)|두뇌|뇌\s?(건강|기능)|집중력|암기", ""],
    ["tension", "긴장 완화", r"긴장|스트레스", ""],
    ["sleep", "수면", r"수면|숙면|잠(을|이|들|자)", ""],
    ["joint", "관절·연골", r"관절|연골|무릎", ""],
    ["bone", "뼈 건강", r"뼈|골\s?(밀도|건강|다공)|칼슘\s?흡수", ""],
    ["muscle", "근력", r"근력|근육", ""],
    ["endurance", "운동수행능력·지구력", r"운동\s?수행|지구력|체력|신체\s?저항", ""],
    ["fatigue", "피로 개선", r"피로|피곤|활력|기운", ""],
    ["antioxidant", "항산화", r"항산화|유해\s?산소|활성\s?산소|산화\s?스트레스", ""],
    ["gut_flora", "장내 유익균·유해균", r"유익균|유해균|유산균\s?(증식|균형)|장내\s?(환경|세균|균)", "gut"],
    ["bowel", "배변활동", r"배변|변비|쾌변|장\s?운동", "gut"],
    ["gut", "장 건강", r"장\s?(건강|기능)|장이\s?(편|건강)", ""],
    ["stomach", "위 건강", r"위\s?(건강|점막|불편|보호)|헬리코박터|속\s?쓰림|소화", ""],
    ["prostate", "전립선", r"전립선", ""],
    ["urinary", "요로·배뇨", r"요로|배뇨|방광|소변", ""],
    ["meno_f", "갱년기 여성", r"갱년기\s?(여성|여자)|여성\s?(의\s?)?갱년기|폐경", "meno"],
    ["meno_m", "갱년기 남성", r"갱년기\s?(남성|남자)|남성\s?(의\s?)?(갱년기|건강)|남성\s?호르몬", "meno"],
    ["meno", "갱년기 건강", r"갱년기", ""],
    ["pms", "월경 전 불편", r"월경|생리\s?(전|통|불순)", ""],
    ["vaginal", "질 건강", r"질\s?(내|건강|유익균)", ""],
    ["bronchi", "기관지", r"기관지|기침|가래|목\s?(건강|상태)", ""],
    ["hair", "모발", r"모발|머리카락|탈모|머릿결", ""],
    ["oral", "치아·잇몸", r"치아|잇몸|충치|구강", ""],
    ["growth", "어린이 키 성장", r"키\s?(성장|크|가\s?크)|성장\s?(발달|기|판)", ""],
    ["energy", "에너지 대사", r"에너지\s?(생성|대사|이용)", ""],
    ["blood", "혈액 생성", r"혈액\s?생성|적혈구|헤모글로빈|빈혈|호모시스테인", ""],
    ["calm", "정서 안정", r"우울|불안", ""],
    ["cognition_kid", "어린이 집중", r"주의\s?집중|ADHD", ""],
]

# 소비자가 흔히 쓰는 이름 → 원료 이름에 들어 있는 글자 (정규화한 뒤 비교)
ALIASES = {
    "유산균": ["프로바이오틱스"], "프로바이오틱": ["프로바이오틱스"],
    "오메가3": ["epa및dha함유유지"], "오메가-3": ["epa및dha함유유지"], "epa": ["epa및dha함유유지"], "dha": ["epa및dha함유유지"],
    "루테인": ["마리골드꽃추출물", "루테인"], "지아잔틴": ["지아잔틴"],
    "밀크씨슬": ["밀크씨슬"], "밀크시슬": ["밀크씨슬"], "실리마린": ["밀크씨슬"],
    "코큐텐": ["코엔자임q10"], "코엔자임": ["코엔자임q10"],
    "철분": ["철"], "비타민씨": ["비타민c"], "비타민디": ["비타민d"],
    "msm": ["엠에스엠"], "식이섬유": ["식이섬유"], "콜라겐": ["콜라겐"],
    "가르시니아": ["가르시니아캄보지아추출물"],
}
# 너무 흔하거나 다른 뜻이 많아 원료 이름으로 쓰지 않는 글자
STOP = {"가자", "감잎", "상추", "철", "밀", "콩", "쌀", "차", "꿀", "효모", "유지", "분말", "추출물", "복합물", "식물", "열매", "과일", "녹용당귀"}
SUFFIX = r"(등\s?)?(복합)?(추출|주정추출|열수추출|에탄올추출|발효추출|효소분해추출)?(물|분말|오일|복합물|농축액|추출물)$"


def norm(s: str) -> str:
    s = s.lower()
    return re.sub(r"[\s·․ㆍ・\-_,./®ⓡⓇ™()\[\]{}'\"“”‘’:;]", "", s)


def clean_name(s: str) -> str:
    s = re.sub(r"\((New)?제?\s?\d{4}-\d+호?\)|\(기능성원료인정.*?\)|\(제\d{4}-\d+호\)", "", s or "")
    return re.sub(r"\s+", " ", s).strip()


def claims_of(s: str) -> list[str]:
    s = re.sub(r"\(영문\).*?(?=\(국문\)|$)", "", s or "", flags=re.S)
    s = re.sub(r"May help.*|Can help.*", "", s, flags=re.S)
    out = []
    for p in re.split(r"[\n\r]|[①②③④⑤⑥⑦⑧⑨]|\(\d+\)|(?:^|\s)\d\)\s|[“”\"]", s):
        p = re.sub(r"\(국문\)|기능성\s?내용\s?:|\((기타|생리활성)\s?(기능)?\s?[IⅠⅡ]+\s?(등급)?\)|\(생리활성기능\s?\d등급\)|\(기타\s?[IⅠⅡ]+등급\)", "", p)
        p = p.strip(" .,-·/")
        if len(p) >= 6 and re.search("[가-힣]", p) and re.search(r"도움|필요|감소|개선|유지|억제|보호|증진", p) \
                and not re.search(r"형식으로|따름|확인이\s?필요|인체시험을\s?대상", p):
            out.append(p)
    return out


def tag(text: str) -> list[str]:
    taken, found = [], []
    for code, _, pat, _ in FUNCS:
        for m in re.finditer(pat, text):
            if any(m.start() < b and a < m.end() for a, b in taken):
                continue
            taken.append((m.start(), m.end()))
            if code not in found:
                found.append(code)
    return found


def keys_for(name: str) -> list[str]:
    base = clean_name(name)
    keys = set()
    complex_ = bool(re.search(r"등|복합|혼합|,|및(?!dha)", base)) and "epa" not in base.lower()
    no_paren = re.sub(r"\(.*?\)", "", base).strip()
    alts = re.findall(r"\(([^()]*)\)", base)
    for part in ([no_paren] if complex_ else re.split(r"/", no_paren)):
        k = norm(part)
        if len(k) >= 2:
            keys.add(k)
        if not complex_:
            stem = k
            for _ in range(3):
                stem = re.sub(SUFFIX, "", stem)
            if len(stem) >= 2 and stem not in STOP and re.search("[가-힣a-z]", stem):
                keys.add(stem)
                part2 = re.sub(r"(열매|잎|뿌리|종자|씨|껍질|꽃|줄기|자실체|균사체|초임계|건조|가수분해)+$", "", stem)
                if len(part2) >= 3 and part2 not in STOP:
                    keys.add(part2)
    for code in re.findall(r"[A-Za-z]{2,}[- ]?\d{2,}[A-Za-z]?\b|\b\d{2,}[A-Za-z]{2,}\d*\b", base):   # 균주·제품 코드 (BNR17, HY7017 …)
        k = norm(code)
        if len(k) >= 4:
            keys.add(k)
    for a in alts:   # 괄호 속 다른 이름: 한글 3자 이상이거나 영문 원료명(MSM 등)일 때만
        for part in re.split(r",", a):
            k = norm(part)
            if (re.fullmatch(r"[가-힣]{3,}", k) and not re.search(r"추출|함량|분말", k)) or k in ("msm",):
                keys.add(k)
    return sorted(k for k in keys if k not in STOP)


def main():
    rows = []
    for r in json.loads((RAW / "I2710.json").read_text(encoding="utf-8")):
        rows.append(("품목분류", r["PRDCT_NM"], r["PRIMARY_FNCLTY"], ""))
    for r in json.loads((RAW / "I-0050.json").read_text(encoding="utf-8")):
        rows.append(("개별인정", r["RAWMTRL_NM"], r["PRIMARY_FNCLTY"], r.get("HF_FNCLTY_MTRAL_RCOGN_NO", "")))
    for r in json.loads((RAW / "I-0040.json").read_text(encoding="utf-8")):
        rows.append(("인정현황", r["APLC_RAWMTRL_NM"], r["FNCLTY_CN"], r.get("HF_FNCLTY_MTRAL_RCOGN_NO", "")))

    by = defaultdict(lambda: {"names": [], "claims": [], "no": set()})
    for src, name, fn, no in rows:
        cs = claims_of(fn)
        nm = clean_name(name)
        if not cs or not nm:
            continue
        key = norm(re.sub(r"\(.*?\)", "", nm)) or norm(nm)
        e = by[key]
        if nm not in e["names"]:
            e["names"].append(nm)
        for c in cs:
            if c not in e["claims"]:
                e["claims"].append(c)
        m = re.search(r"\d{4}-\d+", no or name)
        if m:
            e["no"].add(m.group(0))

    items, key_map, simple, by_names = [], defaultdict(set), set(), []
    for key, e in sorted(by.items()):
        fs = []
        for c in e["claims"]:
            for t in tag(c):
                if t not in fs:
                    fs.append(t)
        if not fs:
            continue
        i = len(items)
        by_names.append(e["names"])
        name = min(e["names"], key=len)
        cs = list(e["claims"])
        for c in e["claims"]:   # '면역력 증진･피로개선･…에 도움을 줄 수 있음' → 기능 하나씩 나눈 문구도 둔다
            parts = re.split(r"\s?[･·ㆍ]\s?", c)
            if len(parts) > 1:
                tail = re.search(r"(에|을|를)?\s?도움을?\s?줄\s?수\s?있(음|습니다)$", parts[-1])
                ending = "에 도움을 줄 수 있음" if tail else ""
                for p in parts:
                    q = p if re.search("도움|필요", p) else (p + ending if ending else "")
                    if q and len(tag(q)) == 1 and q not in cs:
                        cs.append(q)
        items.append({"n": name, "f": fs, "c": cs[:12], "no": sorted(e["no"])[:5]})
        for nm in e["names"]:
            ks = keys_for(nm)
            for k in ks:
                key_map[k].add(i)
            if not re.search(r"등|복합|혼합|,", nm):
                simple.update(ks)
    exact = defaultdict(set)   # 원료 이름 그대로(괄호 뺀 것) → 원료
    for i, it in enumerate(items):
        for nm in by_names[i]:
            exact[norm(re.sub(r"\(.*?\)", "", nm))].add(i)
    for k in list(key_map):    # 같은 이름이 여러 원료에 걸리면, 이름이 정확히 같은 원료만 남긴다 (홍삼 ≠ 홍삼오일)
        if len(key_map[k]) > 1 and exact.get(k):
            key_map[k] = set(exact[k])
    for alias, targets in ALIASES.items():
        a = norm(alias)
        for t in targets:
            if exact.get(t):
                key_map[a] |= exact[t]
            else:
                for k in list(key_map):
                    if k in simple and t in k:
                        key_map[a] |= key_map[k]
    keys = sorted(([k, sorted(v)] for k, v in key_map.items() if v), key=lambda kv: (-len(kv[0]), kv[0]))
    data = {
        "source": "식품안전나라 OpenAPI I2710·I-0050·I-0040",
        "funcs": [{"id": c, "name": n, "re": p, "parent": par} for c, n, p, par in FUNCS],
        "items": items,
        "keys": keys,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    untagged = [k for k, e in by.items() if not any(tag(c) for c in e["claims"])]
    print(f"원료 {len(items)}개 · 이름 {len(keys)}개 · 분류 못 한 원료 {len(untagged)}개 · {OUT.stat().st_size // 1024}KB")
    return untagged, by


if __name__ == "__main__":
    un, by = main()
    import sys
    if "-v" not in sys.argv:
        sys.exit()
    for k in un[:60]:
        print("  분류 못 함:", by[k]["names"][0], "|", " / ".join(by[k]["claims"])[:150])
