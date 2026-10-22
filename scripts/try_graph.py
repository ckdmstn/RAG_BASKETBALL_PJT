from src.data_prep.players import load_players
from src.rag.graph import build_graph

p = next(x for x in load_players() if x["name"] == "박정웅")
q = "정관장은 창단 첫 우승을 언제 했어?"
app = build_graph()

# 1) 노드가 끝날 때마다 알려 주는 방식 (진행 표시에 쓸 방법)
for update in app.stream({"player": p, "question": q}, stream_mode="updates"):
    print("끝난 노드:", list(update.keys()))

# 2) 결과 전체를 한 번에 받는 방식
result = app.invoke({"player": p, "question": q})
print()
print("답변:", result["answer"])
print("인용된 근거:")
for e in result["cited"]:
    print(" ", e["n"], e["kind"], e["title"], e["source_url"])