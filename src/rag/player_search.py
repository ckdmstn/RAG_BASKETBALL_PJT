"""선수 찾기 (F2011): 코드 필터 + (경력 키워드가 있으면) 의미 검색과 LLM 선별."""
import config
from src.data_prep.players import load_players
from src.rag.query_extraction import get_llm, parse_json_list
from src.rag.search_conditions import apply_conditions, parse_conditions
from src.vectorstore.store import get_store

# 후보 중 조건에 맞는 선수를 LLM 이 고르게 하는 프롬프트 (프롬프트 6).
# 규칙: 후보 글에 적힌 내용만 보고 판단 / 확실하지 않으면 고르지 않음 / 번호 JSON 배열만 출력
PICK_PROMPT = """당신은 KBL 선수 검색 도우미입니다. [조건]에 맞는 선수를 [후보]에서 고르세요.

[규칙]
1. 후보의 글에 적힌 내용만 보고 판단한다. 글에 없으면 조건에 맞지 않는 것으로 본다.
2. 확실하지 않으면 고르지 않는다. 맞는 선수가 없으면 빈 배열 []을 출력한다.
3. 고른 후보 번호의 JSON 배열만 출력한다. 설명은 쓰지 않는다.

[예시 1]
조건: NBA에서 뛴 적이 있는 선수
후보:
[1] 선수: 가상선수A / 경력: NBA 가상 팀을 거쳐 KBL에 왔다.
[2] 선수: 가상선수B / 경력: 대학 졸업 후 KBL 신인 드래프트로 입단했다.
출력: [1]

[예시 2]
조건: 올림픽에 출전한 선수
후보:
[1] 선수: 가상선수C / 경력: 대학 리그 득점왕 출신이다.
[2] 선수: 가상선수D / 경력: 2024시즌 베스트5에 선정됐다.
출력: []

이제 실제 조건입니다.

[조건]
{condition}

[후보]
{candidates}

출력:"""


def search_by_keywords(base: list[dict], keywords: list[str], k: int = 10) -> list[dict]:
    """base(코드 필터를 통과한 선수들) 안에서 키워드로 의미 검색한다.
    -> [{"player": 선수 딕셔너리, "text": 그 선수의 정보 글}, ...] (가까운 순)"""
    store = get_store(config.COL_PLAYERS)
    by_id = {p["player_id"]: p for p in base}
    # filter 의 $in: player_id 가 이 목록에 있는 선수만 검색 대상으로 삼는다 (범위는 코드가 정한다)
    docs = store.similarity_search(
        " ".join(keywords), k=k, filter={"player_id": {"$in": list(by_id)}}
    )
    cands = []
    for d in docs:
        player = by_id.get(d.metadata.get("player_id"))
        if player is not None:
            cands.append({"player": player, "text": d.page_content})
    return cands


def pick_matching(condition: str, cands: list[dict]) -> list[dict]:
    """후보 중 조건에 맞는 선수만 LLM 이 골라 돌려준다. 못 고르면 빈 목록."""
    if not cands:
        return []
    # 후보를 "[1] 글" 줄들로 만든다 (줄바꿈은 " / " 로, 앞 300자까지만 -> 토큰 절약)
    lines = [f"[{i}] " + c["text"].replace("\n", " / ")[:300] for i, c in enumerate(cands, start=1)]
    prompt = PICK_PROMPT.format(condition=condition, candidates="\n".join(lines))
    raw = parse_json_list(get_llm().invoke(prompt).content)

    # LLM 출력은 코드가 검증한다: 정수가 아니거나 범위를 벗어난 번호는 버리고 중복은 한 번만
    chosen = []
    for x in raw:
        try:
            n = int(x)
        except (TypeError, ValueError):
            continue
        if 1 <= n <= len(cands) and n not in chosen:
            chosen.append(n)
    return [cands[n - 1]["player"] for n in chosen]


def find_players(text: str, on_progress=None) -> dict:
    """자연어 조건 -> {"conditions": 조건, "players": 선수 목록, "note": 안내 문구}"""
    say = on_progress or (lambda message: None)
    players = load_players()

    say("조건을 해석하는 중...")
    cond = parse_conditions(text)
    keywords = cond["keywords"]

    # 아무 조건도 해석하지 못했으면 전체 선수를 보여 주지 않고 다시 적도록 안내한다
    if all(v in (None, []) for v in cond.values()):
        return {"conditions": cond, "players": [],
                "note": "조건을 이해하지 못했습니다. 팀, 포지션, 학교, 키, 출생 연도, 경력 키워드 등으로 다시 적어 주세요."}

    # 키워드가 있으면 정렬·개수 제한은 선별 뒤에 적용해야 하므로 지금은 뺀다
    base_cond = {**cond, "sort_by": None, "sort_order": None, "limit": None} if keywords else cond
    base = apply_conditions(players, base_cond)
    say(f"코드 필터 결과: {len(base)}명")

    if not keywords:
        return {"conditions": cond, "players": base, "note": ""}
    if not base:
        return {"conditions": cond, "players": [], "note": ""}

    say(f"경력 키워드로 후보를 찾는 중: {keywords}")
    cands = search_by_keywords(base, keywords)
    say(f"후보 {len(cands)}명 중 조건에 맞는 선수를 고르는 중...")
    picked = pick_matching(text, cands)
    found = apply_conditions(picked, cond)          # 정렬·개수 제한은 마지막에 코드로
    note = f"경력 키워드는 코드 필터를 통과한 선수 중 가장 가까운 {len(cands)}명만 살펴봅니다."
    return {"conditions": cond, "players": found, "note": note}