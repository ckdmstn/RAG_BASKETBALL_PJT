"""F2015: RAG 사용 전후 답변 비교. 결과를 docs/rag_comparison.md 로 저장한다.
사용: python -m scripts.compare_rag   (질문 6개 x (RAG 없이 1회 + RAG 파이프라인 1회) 실행)"""
import re
from datetime import date
from pathlib import Path

from src.data_prep.players import load_players
from src.rag.pipeline import answer_question
from src.rag.query_extraction import get_llm

OUT = Path("docs/rag_comparison.md")

# RAG 없이 묻는 프롬프트: 근거 없이 LLM 이 아는 대로 답하게 한다 (모르면 모른다고 하라는 기본 안내만 둔다)
NO_RAG_PROMPT = """당신은 한국프로농구(KBL) 안내 도우미입니다. 아래 질문에 한국어 존댓말로 2~3문장으로 답하세요.
확실하지 않으면 모른다고 답하세요.

질문: {question}
답변:"""

# 모른다는 뜻으로 볼 표현들 (자동 판정용)
UNKNOWN_MARKERS = ["확인되지", "알 수 없", "알려지지", "모릅니다", "모르", "공개되지", "정보가 없", "확인할 수 없", "어렵습니다", "부족해서"]

# 대표 질문 (RAG 없이는 틀리기 쉬운 것들). 정답은 우리가 색인한 데이터(kbl_players.json, kbl_teams.json) 기준이다.
#  must   : 정답으로 인정하려면 답변에 들어 있어야 하는 표현들 (각 묶음에서 하나 이상 포함)
#  unknown: True 이면 '근거에 없는 질문'이라 모른다고 답해야 정답
CASES = [
    {"player": "박정웅", "team": "안양 정관장 레드부스터스",
     "question": "박정웅 선수는 몇 년도 드래프트에서 몇 순위로 어느 팀에 지명됐어?",
     "expected": "2024 KBL 신인선수 드래프트 1라운드 1순위, 안양 정관장",
     "must": [["2024"], ["1순위"], ["정관장"]], "unknown": False},
    {"player": "이민서", "team": "서울 SK 나이츠",
     "question": "서울 SK 나이츠는 챔피언결정전에서 몇 번 우승했어?",
     "expected": "3회 (1999-2000, 2017-18, 2021-22)",
     "must": [["3회", "3번", "세 번", "세번"]], "unknown": False},
    {"player": "자니 오브라이언트", "team": "고양 소노 스카이거너스",
     "question": "자니 오브라이언트 선수의 현재 소속팀은 어디야?",
     "expected": "고양 소노 스카이거너스 (2026년 합류)",
     "must": [["소노"]], "unknown": False},
    {"player": "이민서", "team": "서울 SK 나이츠",
     "question": "서울 SK 나이츠의 이민서 선수는 어느 대학 출신이야?",
     "expected": "연세대학교",
     "must": [["연세대"]], "unknown": False},
    {"player": "박정웅", "team": "안양 정관장 레드부스터스",
     "question": "안양 정관장 레드부스터스의 홈구장은 어디야?",
     "expected": "안양 정관장 아레나",
     "must": [["정관장 아레나"]], "unknown": False},
    {"player": "박정웅", "team": "안양 정관장 레드부스터스",
     "question": "박정웅 선수의 혈액형은 뭐야?",
     "expected": "자료에 없음 -> 모른다고 답해야 함",
     "must": [], "unknown": True},
]


def judge(case: dict, answer: str) -> dict:
    """세 기준으로 판정한다 (키워드 기준 자동 판정)."""
    said_unknown = any(m in answer for m in UNKNOWN_MARKERS)
    cited = bool(re.search(r"\[근거\s*\d", answer))
    if case["unknown"]:
        accurate = said_unknown                 # 근거에 없는 질문: 지어내지 않고 모른다고 하면 정답
        verdict = "정답(모른다고 답함)" if said_unknown else "오답(지어냄)"
    else:
        accurate = all(any(w in answer for w in group) for group in case["must"])
        verdict = "정답" if accurate else ("모른다고 답함" if said_unknown else "오답")
    return {"accurate": accurate, "cited": cited, "said_unknown": said_unknown, "verdict": verdict}


def short(text: str) -> str:
    """표에 넣을 한 줄 답변."""
    return text.replace("\n", " ").replace("|", "/").strip()


def main():
    players = load_players()
    rows = []
    for i, case in enumerate(CASES, start=1):
        print(f"[{i}/{len(CASES)}] {case['question']}")
        player = next(p for p in players if p["name"] == case["player"] and p["team"] == case["team"])
        try:
            plain = get_llm().invoke(NO_RAG_PROMPT.format(question=case["question"])).content.strip()
        except Exception as e:
            plain = f"(오류: {type(e).__name__})"
        try:
            rag = answer_question(player, case["question"])["answer"].strip()
        except Exception as e:
            rag = f"(오류: {type(e).__name__})"
        rows.append({"case": case, "plain": plain, "rag": rag,
                     "j_plain": judge(case, plain), "j_rag": judge(case, rag)})

    # 기준별 집계 (정답이 정해진 질문 5개 기준, 모른다고 답하는지는 근거에 없는 질문 기준)
    fact = [r for r in rows if not r["case"]["unknown"]]
    unk = [r for r in rows if r["case"]["unknown"]]
    n = len(fact)

    lines = [
        "# RAG 사용 전후 답변 비교 (F2015)",
        "",
        f"- 작성일: {date.today()}",
        "- 방법: 같은 질문을 (가) RAG 없이 LLM에게 그대로 묻고, (나) RAG 파이프라인(수집 → 색인 → 검색 → 근거를 붙인 답변)으로 답하게 해 비교했다.",
        "- 정답 기준: 이 프로젝트가 색인한 데이터(선수 JSON, 팀 정보 JSON, 위키백과). 실제 사실과 다를 수 있는 값도 이 기준으로 판정했다.",
        "- 판정 방식: 답변에 정답 표현이 들어 있는지(키워드)로 자동 판정했다. 근거 제시는 답변의 [근거 n] 표기 여부, 모르는 것을 모른다고 답하는지는 '확인되지 않는다' 등의 표현 여부로 판정했다.",
        "",
        "## 요약",
        "",
        "| 평가 기준 | RAG 없이 | RAG 사용 |",
        "|---|---|---|",
        f"| 사실 정확성 (정답이 있는 질문 {n}개) | {sum(r['j_plain']['accurate'] for r in fact)}/{n} | {sum(r['j_rag']['accurate'] for r in fact)}/{n} |",
        f"| 근거 제시 (정답이 있는 질문 {n}개 중 [근거 n] 표기) | {sum(r['j_plain']['cited'] for r in fact)}/{n} | {sum(r['j_rag']['cited'] for r in fact)}/{n} |",
        f"| 모르는 것을 모른다고 답함 (근거에 없는 질문 {len(unk)}개) | {sum(r['j_plain']['accurate'] for r in unk)}/{len(unk)} | {sum(r['j_rag']['accurate'] for r in unk)}/{len(unk)} |",
        "",
        "## 질문별 비교",
        "",
        "| # | 질문 | 정답(데이터 기준) | RAG 없이 | 판정 | RAG 사용 | 판정 |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(rows, start=1):
        lines.append(
            f"| {i} | {r['case']['question']} | {r['case']['expected']} | {short(r['plain'])} | {r['j_plain']['verdict']} "
            f"| {short(r['rag'])} | {r['j_rag']['verdict']} |"
        )
    lines += ["", "## 질문별 답변 전문", ""]
    for i, r in enumerate(rows, start=1):
        lines += [
            f"### {i}. {r['case']['question']}",
            f"- 정답(데이터 기준): {r['case']['expected']}",
            f"- **RAG 없이** ({r['j_plain']['verdict']}, 근거 표기 {'있음' if r['j_plain']['cited'] else '없음'}):",
            "", r["plain"], "",
            f"- **RAG 사용** ({r['j_rag']['verdict']}, 근거 표기 {'있음' if r['j_rag']['cited'] else '없음'}):",
            "", r["rag"], "",
        ]
    lines += ["## 정리", "", "(결과를 보고 직접 작성하거나, 이 파일을 보여 주면 정리를 만들어 드립니다.)", ""]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("저장:", OUT)


if __name__ == "__main__":
    main()