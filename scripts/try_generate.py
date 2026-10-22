from src.data_prep.players import load_players
from src.rag.retrieval import retrieve
from src.rag.generation import generate_answer

p = next(x for x in load_players() if x["name"] == "박정웅")
questions = [
    "정관장은 창단 첫 우승을 언제 했어?",   # 근거에 있음
    "이 선수의 출신 학교는 어디야?",          # 선수 정보에 있음
    "이 선수의 혈액형은 뭐야?",               # 어디에도 없음
]
for q in questions:
    evidence = retrieve(p, q)
    print("Q:", q)
    print(generate_answer(p, q, evidence))
    print()