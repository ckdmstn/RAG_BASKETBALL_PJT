from src.data_prep.players import load_players
from src.rag.retrieval import retrieve

players = load_players()
cases = [
    (next(x for x in players if x["name"] == "박정웅"), "정관장은 창단 첫 우승을 언제 했어?"),
    (next(x for x in players if x["team"] == "서울 SK 나이츠"), "이 선수 팀은 챔피언결정전에서 몇 번 우승했어?"),
]
for p, q in cases:
    print("==", p["name"], p["team"], "|", q)
    for e in retrieve(p, q):
        s = "-" if e["score"] is None else round(e["score"], 3)
        print(e["n"], e["kind"], e["title"], s, "|", e["text"][:40].replace("\n", " "))
    print()