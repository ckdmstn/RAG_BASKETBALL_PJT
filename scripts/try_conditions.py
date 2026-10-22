from src.data_prep.players import load_players
from src.rag.search_conditions import apply_conditions, parse_conditions

players = load_players()
for text in [
    "고려대 출신 가드",
    "고양 소노의 외국인 선수 중 키가 큰 순서로 3명",
    "190cm 이상 국내 포워드",
    "신인왕을 받은 선수",
]:
    cond = parse_conditions(text)
    found = apply_conditions(players, cond)
    print("조건:", text)
    print(" 파싱:", {k: v for k, v in cond.items() if v not in (None, [])})
    print(" 결과:", len(found), "명", [p["name"] for p in found[:5]])
    print()