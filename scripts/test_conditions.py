from src.data_prep.players import load_players
from src.rag.search_conditions import apply_conditions, clean_conditions

players = load_players()
teams = {p["team"] for p in players}

c = clean_conditions({"position": "가드", "height_min": 190, "team": "없는팀", "sort_by": "이상한값"}, teams)
print(c)
r = apply_conditions(players, c)
print(len(r), all(p["position"] == "가드" and p["height_cm"] >= 190 for p in r))

c2 = clean_conditions({"is_foreign": True, "position": "센터", "sort_by": "height_cm", "limit": 3}, teams)
print(c2["sort_order"])
print([(p["name"], p["height_cm"]) for p in apply_conditions(players, c2)])