from src.rag.player_search import find_players

for text in ["고려대 출신 가드", "신인왕을 받은 선수", "NBA에서 뛴 적이 있는 외국인 센터"]:
    out = find_players(text, on_progress=print)
    print("조건:", text)
    print(" 결과:", len(out["players"]), "명")
    for p in out["players"][:5]:
        print("  -", p["name"], p["team"], "|", (p.get("career_summary") or "")[:50])
    if out["note"]:
        print(" 안내:", out["note"])
    print()