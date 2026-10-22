from src.rag.team_guide import make_team_guide

out = make_team_guide("안양 정관장 레드부스터스", on_progress=print)
print()
print(out["answer"])
print()
for e in out["cited"]:
    print("인용:", e["n"], e["kind"], e["title"])