"""선수 찾기 (F2011): 자연어 조건 -> JSON 조건 -> 코드로 정확히 거르고 정렬한다."""
import json
import re

from src.data_prep.teams import load_teams
from src.rag.query_extraction import get_llm

CONDITION_PROMPT = """당신은 KBL 선수 검색 도우미입니다. 아래 [조건]을 JSON 객체 하나로 바꿔 주세요.

[선수 데이터에 있는 항목]
team(팀 이름), position(가드·포워드·센터), is_foreign(외국인 선수 여부), school(출신 학교),
height_cm(키), weight_kg(몸무게), birth_year(출생 연도), draft(드래프트), career_summary(경력 요약)

[팀 이름 목록] team 은 반드시 이 중 하나를 그대로 쓴다.
{team_names}

[규칙]
1. 조건에 없는 항목은 null 로 둔다. keywords 는 없으면 빈 배열이다.
2. 숫자는 숫자로 쓴다. "190cm 이상" → height_min 190, "1995년 이후 출생" → birth_year_min 1995.
   "20대"처럼 나이는 올해를 2026년으로 계산해 birth_year 범위로 바꾼다.
3. "가장 ~한", "~순서", "N명"은 sort_by(height_cm / weight_kg / birth_year), sort_order(desc / asc), limit 으로 바꾼다.
   기준 숫자 없이 "키가 큰", "어린"만 있으면 정렬로 바꾸고 limit 은 5로 한다. (어린 = birth_year desc)
4. school 은 학교 이름의 핵심만 쓴다. 예: "고려대학교" → "고려대".
5. 위 항목으로 표현할 수 없는 조건(경력, 기록, 수상 등)은 keywords 에 짧은 명사로 넣는다. 최대 3개.

[출력 형식] 아래 키를 모두 가진 JSON 객체 하나만 출력한다. 설명은 쓰지 않는다.
{"team": null, "position": null, "is_foreign": null, "school": null, "height_min": null, "height_max": null, "weight_min": null, "weight_max": null, "birth_year_min": null, "birth_year_max": null, "sort_by": null, "sort_order": null, "limit": null, "keywords": []}

[예시 1]
조건: 고려대 출신 가드
{"team": null, "position": "가드", "is_foreign": null, "school": "고려대", "height_min": null, "height_max": null, "weight_min": null, "weight_max": null, "birth_year_min": null, "birth_year_max": null, "sort_by": null, "sort_order": null, "limit": null, "keywords": []}

[예시 2]
조건: 서울 SK 나이츠의 외국인 센터 중 키 큰 순서
{"team": "서울 SK 나이츠", "position": "센터", "is_foreign": true, "school": null, "height_min": null, "height_max": null, "weight_min": null, "weight_max": null, "birth_year_min": null, "birth_year_max": null, "sort_by": "height_cm", "sort_order": "desc", "limit": null, "keywords": []}

[예시 3]
조건: 신인왕 출신 국내 선수
{"team": null, "position": null, "is_foreign": false, "school": null, "height_min": null, "height_max": null, "weight_min": null, "weight_max": null, "birth_year_min": null, "birth_year_max": null, "sort_by": null, "sort_order": null, "limit": null, "keywords": ["신인왕"]}

[조건]
{condition}

JSON:"""

POSITIONS = {"가드", "포워드", "센터"}
SORT_FIELDS = {"height_cm", "weight_kg", "birth_year"}
NUMBER_KEYS = ["height_min", "height_max", "weight_min", "weight_max", "birth_year_min", "birth_year_max"]
RANGES = [  # (최소 키, 최대 키, 선수 데이터의 필드)
    ("height_min", "height_max", "height_cm"),
    ("weight_min", "weight_max", "weight_kg"),
    ("birth_year_min", "birth_year_max", "birth_year"),
]


def _num(v):
    """숫자(정수·실수)만 통과시키고, 아니면 None (True/False 도 숫자로 보지 않는다)."""
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def parse_json_object(text: str) -> dict:
    """LLM 응답에서 JSON 객체 하나를 꺼낸다. 못 꺼내면 빈 딕셔너리."""
    # [실습 1] parse_json_list 와 같은 방식이에요.
    #   ``` 코드블록 표시 제거 -> 정규식으로 { ... } 부분만 찾기(re.DOTALL) -> json.loads
    #   실패하거나 딕셔너리가 아니면 {} 를 돌려주세요
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            obj = json.loads(match.group())
            if isinstance(obj, dict):
                return obj
    except Exception:
        pass
    return {}


def clean_conditions(raw: dict, team_names: set[str]) -> dict:
    """LLM 이 만든 조건을 검증해서 안전한 값만 남긴다. 키는 항상 모두 있다."""
    # [실습 2] 아래 규칙으로 cond 딕셔너리를 만들어 돌려주세요
    #   team       : team_names 에 있는 값만, 아니면 None
    #   position   : POSITIONS 에 있는 값만, 아니면 None
    #   is_foreign : True / False 일 때만, 아니면 None
    #   school     : 문자열이면 공백을 뺀 값 (빈 문자열이면 None)
    #   NUMBER_KEYS 의 여섯 개: _num(...) 으로 숫자만
    #   sort_by    : SORT_FIELDS 에 있는 값만, 아니면 None
    #   sort_order : "asc" 또는 "desc" 만. sort_by 가 있는데 sort_order 가 없으면 "desc"
    #   limit      : 1~50 의 정수만, 아니면 None
    #   keywords   : 문자열 목록만, 앞에서 3개까지
    cond = {}
    team = raw.get("team")
    cond["team"] = team if isinstance(team, str) and team in team_names else None
    position = raw.get("position")
    cond["position"] = position if isinstance(position, str) and position in POSITIONS else None
    cond["is_foreign"] = raw.get("is_foreign") if isinstance(raw.get("is_foreign"), bool) else None
    school = raw.get("school")
    cond["school"] = school.strip() if isinstance(school, str) and school.strip() else None
    for key in NUMBER_KEYS:
        cond[key] = _num(raw.get(key))

    sort_by = raw.get("sort_by")
    cond["sort_by"] = sort_by if isinstance(sort_by, str) and sort_by in SORT_FIELDS else None
    sort_order = raw.get("sort_order")
    if sort_order not in ("asc", "desc"):
        sort_order = "desc" if cond["sort_by"] else None
    cond["sort_order"] = sort_order

    limit = raw.get("limit")
    is_int = isinstance(limit, int) and not isinstance(limit, bool)
    cond["limit"] = limit if is_int and 1 <= limit <= 50 else None

    keywords = raw.get("keywords")
    if isinstance(keywords, list):
        cond["keywords"] = [k.strip() for k in keywords if isinstance(k, str) and k.strip()][:3]
    else:
        cond["keywords"] = []
    return cond



def parse_conditions(text: str) -> dict:
    """자연어 조건 -> 검증된 조건 딕셔너리."""
    team_names = [t["team_name"] for t in load_teams()]
    prompt = CONDITION_PROMPT.replace("{team_names}", "\n".join(team_names)).replace("{condition}", text)
    raw = parse_json_object(get_llm().invoke(prompt).content)
    return clean_conditions(raw, set(team_names))


def apply_conditions(players: list[dict], cond: dict) -> list[dict]:
    """조건에 맞는 선수를 코드로 정확히 거르고 정렬한다. (LLM 을 쓰지 않는다)"""
    result = []
    for p in players:
        # [실습 3-1] 아래 조건 중 하나라도 어긋나면 이 선수는 건너뛰세요 (continue)
        #   team / position 이 지정됐는데 다름
        #   is_foreign 이 지정됐는데 다름  (p.get("is_foreign") 와 비교)
        #   school 이 지정됐는데 p.get("school", "") 에 그 글자가 들어 있지 않음 (부분 일치)
        #   RANGES 의 각 줄: 최소가 지정됐는데 값이 없거나 더 작음 / 최대가 지정됐는데 값이 없거나 더 큼
        if cond["team"] is not None and p.get("team") != cond["team"]:
            continue
        if cond["position"] is not None and p.get("position") != cond["position"]:
            continue
        if cond["is_foreign"] is not None and p.get("is_foreign") != cond["is_foreign"]:
            continue
        if cond["school"] is not None and cond["school"] not in (p.get("school") or ""):
            continue
        range_violation = False
        for min_key, max_key, field in RANGES:
            if cond[min_key] is not None and (p.get(field) is None or p.get(field) < cond[min_key]):
                range_violation = True
                break
            if cond[max_key] is not None and (p.get(field) is None or p.get(field) > cond[max_key]):
                range_violation = True
                break
        if range_violation:
            continue
        result.append(p)

    # [실습 3-2] cond["sort_by"] 가 있으면 정렬하세요. sort_order 가 "desc" 면 큰 값이 먼저.
    #   값이 없는 선수(None)는 항상 맨 뒤로 보내세요.
    if cond["sort_by"] is not None:
        sort_field = cond["sort_by"]
        reverse = cond.get("sort_order") == "desc"
        with_value = [p for p in result if p.get(sort_field) is not None]
        without_value = [p for p in result if p.get(sort_field) is None]
        with_value.sort(key=lambda p: p[sort_field], reverse=reverse)
        result = with_value + without_value        # 값이 없는 선수는 항상 맨 뒤

    # [실습 3-3] cond["limit"] 가 있으면 앞에서 그 수만큼만 남기세요
    if cond["limit"] is not None:
        result = result[:cond["limit"]]
    return result