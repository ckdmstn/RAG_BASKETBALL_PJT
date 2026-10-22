"""RAG 파이프라인 영역: 프롬프트 1 — 질문에서 위키백과 검색어를 뽑는다 (F2003)."""
import json
import re

from langchain_openai import ChatOpenAI

import config
from src.data_prep.players import build_text

# [실습 17] 프롬프트 1을 직접 써 보세요.
QUERY_PROMPT = """
당신은 KBL(한국프로농구) 전문 사서입니다. 아래 [선택한 선수] 정보와 [질문]을 보고, 한국어 위키백과에서 찾을 '검색어'를 뽑아 주세요.

[선택한 선수]
{player_text}

[질문]
{question}

[규칙]
- 검색어는 2~4개만 뽑습니다.
- 검색어는 위키백과에 문서가 있을 법한 대상의 이름만 뽑습니다. (선수, 팀, 대학, 리그, 제도, 기록, 용어)
- 날짜, 경기 결과, 문장은 검색어로 쓰지 않습니다.
- 질문의 "이 선수"는 선택한 선수의 이름으로 풀어서 생각합니다.

[예시]
- 좋은 검색어: "KBL 최연소 기록", "안양 정관장 레드부스터스", "KBL 신인선수 드래프트"
- 나쁜 검색어: "2024년 12월 4일 DB전 데뷔", "2024-25 시즌", "이 선수가 최연소 기록을 세운 이유"

[출력] 
- JSON 문자열 배열만 출력합니다. 설명 문장은 쓰지 않습니다.
- 예: ["연세대학교 농구부", "고양 소노 스카이거너스"]
"""


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(model=config.CHAT_MODEL, api_key=config.GMS_KEY, base_url=config.GMS_BASE_URL)


def parse_json_list(text: str) -> list[str]:
    """LLM 답에서 JSON 배열을 꺼낸다. ```json 코드블록이 붙어 와도, 깨져도 안전하게 처리한다."""
    text = re.sub(r"```(?:json)?", "", text).strip()
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    return [str(x).strip() for x in data if str(x).strip()]


def extract_queries(player: dict, question: str) -> list[str]:
    # [실습 18] LLM 에게 묻는다.
    queries = []

    user = f"[선택한 선수]\n{build_text(player)}\n\n[질문]\n{question}"
    response = get_llm().invoke([
        {"role": "system", "content": QUERY_PROMPT},
        {"role": "user", "content": user}
    ])
    queries = parse_json_list(response.content)

    # [실습 19] 선택한 선수의 이름을 코드가 '항상' 맨 앞에 넣고, 중복을 빼고, 최대 5개만 돌려준다.
    #   (LLM 이 선수 이름을 빼먹어도 선수 본인 문서는 반드시 검색 대상이 되게 하려는 것, F2003)
    result = [player["name"]]
    for q in queries:
        if q not in result:
            result.append(q)
    return result[:5]