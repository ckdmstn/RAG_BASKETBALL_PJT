import config
from src.data_prep.players import load_players
from src.rag.collector import collect_documents
from src.rag.ingest import ingest_documents
from src.vectorstore.store import get_store, count

p = next(x for x in load_players() if x["name"] == "박정웅")
docs = collect_documents(p, "이 선수가 속한 팀은 어떤 팀이야?")

store = get_store(config.COL_DOCS)
print("색인 전 청크 수:", count(store))
added, skipped = ingest_documents(docs, store, on_progress=print)
print("새로 저장:", added, "/ 건너뜀:", skipped)
print("색인 후 청크 수:", count(store))

print()
hits = store.similarity_search_with_score("정관장은 창단 첫 우승을 언제 했어?", k=3)
for d, score in hits:
    m = d.metadata
    print(round(score, 3), m["doc_title"], m["chunk_seq"], m.get("team"), "|", d.page_content[:50].replace("\n", " "))