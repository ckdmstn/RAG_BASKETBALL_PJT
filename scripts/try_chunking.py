from src.data_prep.players import load_players
from src.rag.collector import collect_documents
from src.rag.chunking import split_doc

p = next(x for x in load_players() if x["name"] == "박정웅")
docs = collect_documents(p, "이 선수가 속한 팀은 어떤 팀이야?")
doc = next(d for d in docs if d["scope"] == "team")
chunks = split_doc(doc)

print("원문 글자 수:", len(doc["text"]), "/ 청크 수:", len(chunks))
print("청크 길이:", [len(c["text"]) for c in chunks])
print("--- 0번 끝 100자 ---")
print(chunks[0]["text"][-100:])
print("--- 1번 앞 100자 ---")
print(chunks[1]["text"][:100])
print()
print(chunks[0]["id"])
print(chunks[0]["metadata"])