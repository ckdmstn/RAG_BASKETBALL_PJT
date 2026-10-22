import json

import config


def load_players() -> list[dict]:
    """data/kbl_players.json 을 읽어 선수 목록(리스트)으로 돌려준다."""
    # [실습 1] 파일을 열어서 json.load 로 읽고, 그 결과를 return 한다.
    #   - 경로는 config.PLAYERS_JSON
    #   - 파일은 open(경로, encoding="utf-8") 로 연다
    #   - with 문을 쓰면 파일이 알아서 닫힌다
    with open(config.PLAYERS_JSON, encoding="utf-8") as f:
        return json.load(f)

def build_text(p: dict) -> str:
    """선수 1명을 '글 한 덩어리'로 만든다. 이 글이 임베딩되어 검색에 쓰인다."""
    lines = []   # 줄들을 하나씩 모아 둘 리스트

    # [실습 2] 첫 줄을 lines 에 추가한다.   결과 모양:
    #   선수: 박정웅 (안양 정관장 레드부스터스, 등번호 4번)
    #   힌트: lines.append(f"선수: {p['name']} ({...})") 등번호는 p['jersey_number']
    lines.append(f"선수: {p['name']} ({p['team']}, 등번호 {p['jersey_number']}번)")

    # [실습 3] 둘째 줄을 lines 에 추가한다.  결과 모양:  포지션: 가드 / 국내 선수
    #   - p['is_foreign'] 이 True 면 "외국인 선수", False 면 "국내 선수" 라는 말로 바꾼다
    #     (임베딩은 true/false 같은 값은 못 알아듣고, '외국인'이라는 말이 글에 있어야 검색에 걸린다)
    origin = "외국인 선수" if p['is_foreign'] else "국내 선수"
    lines.append(f"포지션: {p['position']} / {origin}")

    # [실습 5] 신체 줄을 추가한다.   결과 모양:  신체: 194cm, 81kg / 출생: 2006년
    #   - 출생 연도 p['birth_year'] 는 비어 있을 수 있다 → 값이 있을 때만 뒤에 " / 출생: 2006년" 을 붙인다
    body = f"신체: {p['height_cm']}cm, {p['weight_kg']}kg"
    if p.get('birth_year'):
        body += f" / 출생: {p['birth_year']}년"
    lines.append(body)

    # [실습 6] 출신 / 드래프트 / 경력 줄을 추가한다. 각각 값이 있을 때만!
    #   출신:     p.get('school')          → "출신: 고려대학교"
    #   드래프트: p.get('draft')           → "드래프트: 2024 KBL 신인선수 드래프트 1라운드 1순위 (안양 정관장)"
    #   경력:     p.get('career_summary')  → "경력: ..."
    #   힌트: if p.get('school'): lines.append(f"출신: {p['school']}")   ← 이 모양을 3번
    if p.get('school'):
        lines.append(f"출신: {p['school']}")
    if p.get('draft'):
        lines.append(f"드래프트: {p['draft']}")
    if p.get('career_summary'):
        lines.append(f"경력: {p['career_summary']}")

    return "\n".join(lines)   # 줄들을 줄바꿈(\n)으로 이어 붙여 글 하나로 만든다

def build_metadata(p: dict) -> dict:
    """청크에 같이 저장할 '꼬리표'. ChromaDB는 None 과 목록을 못 넣으므로 걸러낸다."""
    meta = {
        # [실습 7] 아래 딕셔너리를 채운다. 선수 p 의 값을 그대로 꺼내면 된다.
        #   "player_id", "name", "team", "position", "is_foreign", 
        #   "jersey_number", "birth_year", "school", "data_as_of"
        #   ※ birth_year, school 은 None 일 수 있으니 p.get("...") 로 꺼낸다
        #   "source_url":   근거 표시용 원문 주소 = source_urls 목록의 첫 번째
        "player_id": p["player_id"],
        "name": p["name"],
        "team": p["team"],
        "position": p["position"],
        "is_foreign": p["is_foreign"],
        "jersey_number": p["jersey_number"],
        "birth_year": p.get("birth_year"),
        "school": p.get("school"),
        "data_as_of": p["data_as_of"],
        "source_url": (p.get("source_urls") or [None])[0],
    }

    # [실습 8] 값이 None 인 항목을 meta 에서 뺀다.
    return {k: v for k, v in meta.items() if v is not None}