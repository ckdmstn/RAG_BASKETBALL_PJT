from src.data_prep.players import load_players
from src.rag.pipeline import answer_question

p = next(x for x in load_players() if x["name"] == "이민서" and x["team"] == "서울 SK 나이츠")
q = "이 선수 팀은 챔피언결정전에서 몇 번 우승했어?"

out = answer_question(p, q, on_progress=print)
print()
print("답변:", out["answer"])
for e in out["cited"]:
    print(" 인용:", e["n"], e["kind"], e["title"], e["source_url"])