"""수집한 문서를 청크로 쪼개 kbl_docs 에 색인한다."""
from src.rag.chunking import split_doc
from src.vectorstore.store import upsert_chunks


def ingest_documents(docs: list[dict], store, on_progress=None) -> tuple[int, int]:
    """-> (새로 저장한 청크 수, 건너뛴 청크 수)"""
    say = on_progress or (lambda m: None)
    added = skipped = 0
    for doc in docs:
        chunks = split_doc(doc)
        # [실습 3] upsert_chunks(store, chunks) 를 호출해서 a, s 를 받고
        #          added, skipped 에 더하세요
        a, s = upsert_chunks(store, chunks)
        added += a
        skipped += s
        say(f"{doc['title']}: 청크 {len(chunks)}개 (새로 {a}, 건너뜀 {s})")
    return added, skipped