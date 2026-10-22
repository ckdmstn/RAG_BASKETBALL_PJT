"""위키 문서를 청크로 쪼갠다 (색인 전 단계)."""
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config


def make_splitter() -> RecursiveCharacterTextSplitter:
    # [실습 1] config 의 CHUNK_SIZE, CHUNK_OVERLAP 으로 splitter 를 만들어 돌려주세요.
    return RecursiveCharacterTextSplitter(chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP)


def split_doc(doc: dict) -> list[dict]:
    """문서 1개 -> [{"id", "text", "metadata"}, ...]"""
    pieces = make_splitter().split_text(doc["text"])
    chunks = []
    for seq, piece in enumerate(pieces):
        metadata = {
            # [실습 2] 아래 키들을 채우세요
            "doc_id": str(doc["page_id"]),
            "doc_title": doc["title"],
            "source_url": doc["url"],
            "source_type": "wiki",
            "scope": doc["scope"],
            "collected_at": doc["collected_at"],
            "chunk_seq": seq,
            "player_id": doc["player_id"],
            "team": doc["team"],
        }
        # 값이 None 인 키는 ChromaDB 가 못 받으니 빼야 해요. (선수 때 했던 것과 같아요)
        metadata = {k: v for k, v in metadata.items() if v is not None}  # [실습 3] None 이 아닌 것만 남기세요

        chunks.append({
            # [실습 4] id: "{scope}:{doc_id}:{seq}" 모양의 문자열
            "id": f"{doc['scope']}:{doc['page_id']}:{seq}",
            # [실습 5] text: "[문서 제목]\n조각" 모양 (제목을 앞에 붙이기)
            "text": f"[{doc['title']}]\n{piece}",
            "metadata": metadata,
        })
    return chunks