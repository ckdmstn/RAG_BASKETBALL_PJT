"""RAG 파이프라인 영역: 프롬프트 2 — 검색 후보 중 색인할 문서를 고른다 (F2004)."""
import re
import config

from src.data_prep.players import build_text
from src.rag.query_extraction import get_llm, parse_json_list
from src.data_prep.teams import load_teams

# [실습 22] 프롬프트 2를 직접 써 보세요. 프롬프트 1과 같은 방식으로 빈칸 세 개를 넣어요.
#   빈칸: {player_text} 선택한 선수 정보 / {question} 사용자 질문 / {candidates} 후보 목록
#   - 역할:   검색 후보 중 색인할 문서를 고르는 선별자
#   - 판단 기준: ① 선택한 선수·그 팀·리그(KBL)와 직접 관련이 있고
#               ② 질문의 주제를 다루고 있을 것 같은 문서만 고른다
#               (관련 없는 인물, 해·날짜 문서, 다른 종목 문서는 제외)
#   - 규칙:   최대 3개 / 확실히 관련 있는 것만 / 하나도 없으면 빈 배열
#   - 출력:   고른 후보의 '번호'만 담은 JSON 배열. 예) [1, 3]   없으면 []
SELECT_PROMPT = """
당신은 KBL(한국프로농구) 전문 사서입니다. 아래 [선택한 선수] 정보와 [질문], [후보 목록]을 보고, 한국어 위키백과에서 색인할 문서를 고르세요.

[선택한 선수]
{player_text}

[질문]
{question}

[후보 목록]
{candidates}

[규칙]
- 후보 중 최대 3개만 고릅니다.
- 선택한 선수, 그 선수의 팀·대학·감독, KBL과 직접 관련된 문서만 고릅니다.
- 다른 리그(NBA 등)나 다른 종목의 선수·팀 문서는 제외합니다.
- 해·날짜 문서나 질문과 무관한 인물 문서는 제외합니다.
- 확실하지 않으면 고르지 않습니다. 하나도 없으면 빈 배열 []이 정상 답입니다.

[예시]
- 질문 "이 선수가 속한 팀은 어떤 팀이야?" / 후보 "1. 안양 정관장 레드부스터스 - 경기도 안양시를 연고로 하는 프로 농구단 2. 2005년 - 4월 6일 천주교 대전교구 3. 코비 브라이언트 - NBA 로스앤젤레스 레이커스" → [1]
- 질문 "이 선수는 왜 최연소 기록 얘기가 나와?" / 후보 "1. 2026년 - 마라톤에서 2. 코비 브라이언트 - NBA 최연소" → []
- 질문 "이 선수는 누구야?" / 후보 "1. 3월 11일 - 변준형(농구 선수) 출생 2. 변준형 (농구 선수) - KBL 가드" → [2]

[출력]
- 고른 후보의 '번호'만 담은 JSON 배열을 출력합니다. 예) [1, 3]   없으면 []
"""

def is_date_page(title: str) -> bool:
    """'3월 11일', '1996년' 처럼 날짜·연도만 제목인 문서인가?"""
    # [실습 26] 제목 전체가 '숫자+년' 이거나 '숫자+월 숫자+일' 형식이면 True
    #   힌트: return re.fullmatch(r"\d+년|\d+월 \d+일", title) is not None
    #   (fullmatch 는 제목 '전체'가 이 모양일 때만 맞다. "2026년 아시안 게임" 은 일부만 맞으니 False)
    return re.fullmatch(r"\d+년|\d+월 \d+일", title) is not None

def format_candidates(candidates: list[dict]) -> str:
    """후보를 '1. 제목 - 요약' 줄 목록으로 만든다. 본문은 보내지 않는다 (토큰 절약)."""
    return "\n".join(
        f"{i}. {c['title']} - {c['snippet']}" for i, c in enumerate(candidates, start=1)
    )

def is_own_doc(player: dict, c: dict) -> bool:
    """후보 문서 c 가 선택한 선수 '본인'의 문서인지 판정한다."""
    name = player["name"]
    # [실습 24] 위 조건 세 개를 차례로 검사한다. 하나라도 어긋나면 return False
    #   ① 제목 검사:  c["title"] 이 name 과 같거나, name + " (" 로 시작하는가
    #   ② 요약에 "농구" 가 들어 있는가
    #   ③ 출생 연도:  birth = player.get("birth_year")
    #                 birth 가 있으면(None 이 아니면) str(birth) 가 c["snippet"] 에 들어 있어야 한다
    if c["title"] != name and not c["title"].startswith(name + " ("):
        return False
    if "농구" not in c["snippet"]:
        return False
    birth = player.get("birth_year")
    return birth is None or str(birth) in c["snippet"]

def select_candidates(question: str, player: dict, candidates: list[dict]) -> list[dict]:
    """본인 문서는 항상 포함하고, 나머지는 LLM 이 골라 최대 MAX_SELECTED 개."""

    team_names = {t["team_name"] for t in load_teams()}
    my_team_docs = [c for c in candidates if c["title"] == player["team"]]

    # [실습 25] 후보를 두 묶음으로 나눈다.
    #   own    = 본인 문서인 후보들      (힌트: [c for c in candidates if is_own_doc(player, c)])
    #   others = 나머지 후보들           (힌트: [c for c in candidates if c not in own])
    #   others 가 비어 있으면 own 만 돌려주고 끝낸다.
    #   그 뒤 기존 LLM 선별 코드는 candidates 대신 others 로 돌리고,
    #   마지막 반환은  own + chosen[: config.MAX_SELECTED]  로 바꾼다.
    #   (본인 문서는 MAX_SELECTED 개수 제한에도 걸리지 않고 앞에 붙는다)
    own = [c for c in candidates if is_own_doc(player, c)]
    others = [c for c in candidates if c not in own and not is_date_page(c["title"]) and c["title"] not in team_names]
                 # 팀 문서는 LLM에게 묻지 않는다 (코드가 처리)
    if not others:
        return own

    # [실습 23] ① 빈칸을 채워 프롬프트를 만들고 ② LLM 에게 보내고 ③ 번호 목록을 꺼낸다.
    #   ④ 번호를 후보로 바꾼다. LLM 이 엉뚱한 번호(예: 후보가 5개인데 7)를 줘도 안전하게:
    #      1 이상 후보 수 이하인 번호만 / 같은 번호 중복 없이 / 최대 config.MAX_SELECTED 개
    #      ※ 번호는 1부터 시작하지만 리스트 칸은 0부터라서 candidates[n - 1] 로 꺼낸다
    prompt = SELECT_PROMPT.format(
        player_text=build_text(player),
        question=question,
        candidates=format_candidates(others)
    )
    response = get_llm().invoke(prompt)
    numbers = [int(s) for s in parse_json_list(response.content) if s.isdigit()]
    chosen = []
    for n in numbers:
        if 1 <= n <= len(others) and others[n - 1] not in chosen:
            chosen.append(others[n - 1])
    return own + my_team_docs + chosen[:config.MAX_SELECTED]