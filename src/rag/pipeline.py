"""질문 1개를 처음부터 끝까지 처리한다. 화면은 이 함수만 부른다 (NF2005)."""
import config
from src.rag.collector import collect_documents
from src.rag.graph import build_graph
from src.rag.ingest import ingest_documents
from src.vectorstore.store import get_store


def answer_question(player: dict, question: str, on_progress=None) -> dict:
    """-> {"answer": 답변, "cited": 인용된 근거들, "evidence": 검색한 근거 전체}"""
    say = on_progress or (lambda message: None)

    # [실습 13] 위키 수집이 실패해도 멈추지 않게 하세요
    #   try: docs = collect_documents(player, question, on_progress=on_progress)
    #   except Exception as e: say(f"문서 수집에 실패해 이미 모은 자료로 답합니다: {e}"); docs = []
    docs = collect_documents(player, question, on_progress=on_progress)

    say(f"문서 {len(docs)}개를 색인하는 중...")
    store = get_store(config.COL_DOCS)
    added, skipped = ingest_documents(docs, store)
    say(f"새 청크 {added}개 저장 (이미 있던 청크 {skipped}개)")

    # [실습 14] 그래프를 stream 으로 실행하며 노드가 끝날 때마다 say 로 알리고,
    #           각 노드가 돌려준 값을 result 딕셔너리에 모으세요.
    #   for update in app.stream({"player": player, "question": question}, stream_mode="updates"):
    #       for node, values in update.items():   # values 는 그 노드가 바꾼 값들
    #           result.update(values)
    #           (retrieve 가 끝나면 "근거 N개를 찾았습니다", generate 가 끝나면 "답변을 작성했습니다" 라고 say)
    app = build_graph()
    result = {}
    for update in app.stream({"player": player, "question": question}, stream_mode="updates"):
        for node, values in update.items():   # values 는 그 노드가 바꾼 값들
            result.update(values)
            if node == "retrieve" and "evidence" in values:
                say(f"근거 {len(values['evidence'])}개를 찾았습니다")
            elif node == "generate" and "answer" in values:
                say("답변을 작성했습니다")

    return {
        "answer": result.get("answer", ""),
        "cited": result.get("cited", []),
        "evidence": result.get("evidence", []),
    }