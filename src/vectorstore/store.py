"""Vector Store 영역: 임베딩 모델 · ChromaDB 컬렉션 만들기와 조회 (NF2005)."""
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

import config


def get_embeddings() -> OpenAIEmbeddings:
    # [실습 9] OpenAIEmbeddings 를 만들어 돌려준다. 인자 네 개:
    #   model=config.EMBEDDING_MODEL
    #   api_key=config.GMS_KEY
    #   base_url=config.GMS_BASE_URL
    #   check_embedding_ctx_length=False
    model = config.EMBEDDING_MODEL
    api_key = config.GMS_KEY
    base_url = config.GMS_BASE_URL
    check_embedding_ctx_length = False
    return OpenAIEmbeddings(model=model, api_key=api_key, base_url=base_url, check_embedding_ctx_length=check_embedding_ctx_length)


def get_store(collection_name: str, embeddings=None) -> Chroma:
    """컬렉션을 열거나(없으면 만들어서) 돌려준다. 데이터는 chroma_db/ 폴더에 저장된다."""
    # [실습 10] Chroma(...) 를 만들어 돌려준다. 인자 세 개:
    #   collection_name=collection_name
    #   embedding_function=embeddings or get_embeddings()
    #   persist_directory=str(config.CHROMA_DIR)
    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings or get_embeddings(),
        persist_directory=str(config.CHROMA_DIR)
    )


def count(store: Chroma) -> int:
    """컬렉션에 저장된 청크 수 (화면 사이드바에 표시할 값, F2002)."""
    return store._collection.count()


def upsert_chunks(store, chunks: list[dict]) -> tuple[int, int]:
    """청크 목록을 저장한다. 이미 같은 글이 저장돼 있으면 건너뛴다.
    -> (새로 저장한 수, 건너뛴 수)"""
    if not chunks:
        return 0, 0
    ids = [c["id"] for c in chunks]

    # [실습 1] index_players.py 와 같은 방식으로 todo 를 구하세요.
    #   old   = store.get(ids=ids)
    #   saved = {id: 저장된 글} 딕셔너리
    #   todo  = 저장된 글이 없거나 달라진 청크의 번호 목록
    old = store.get(ids=ids)
    saved = dict(zip(old["ids"], old["documents"]))      # {id: 저장된 글}
    todo = [
        i for i, c in enumerate(chunks)
        if c["id"] not in saved or c["text"] != saved[c["id"]]
    ]

    # [실습 2] todo 에 해당하는 청크만 저장하세요.
    #   store.add_texts(texts=[...], metadatas=[...], ids=[...])
    #   (todo 가 비어 있으면 호출하지 않아요)
    if todo:
            store.add_texts(
                texts=[chunks[i]["text"] for i in todo],
                metadatas=[chunks[i]["metadata"] for i in todo],
                ids=[chunks[i]["id"] for i in todo],
            )

    return len(todo), len(chunks) - len(todo)