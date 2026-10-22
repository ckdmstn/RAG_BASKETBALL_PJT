"""검색 영역: 두 컬렉션에서 질문에 쓸 근거를 모은다 (F2006, F2007)."""
import config
from src.vectorstore.store import get_store


def build_filter(player: dict) -> dict:
    """kbl_docs 검색 범위: 세 조건 중 하나라도 맞으면 통과."""
    # [실습 1] ChromaDB 필터를 만들어 돌려주세요.
    #   조건 A: metadata "player_id" == 선수의 player_id
    #   조건 B: metadata "team"      == 선수의 team
    #   조건 C: metadata "scope"     == "league"
    #   모양:  {"$or": [ {"키": 값}, {"키": 값}, {"키": 값} ]}
    return {"$or": [
        {"player_id": player["player_id"]},
        {"team": player["team"]},
        {"scope": "league"}
    ]}


def get_player_chunk(player: dict) -> str | None:
    """RAG1: 선택한 선수의 정보 글. id 를 알고 있으니 검색이 아니라 id 로 꺼낸다."""
    store = get_store(config.COL_PLAYERS)
    got = store.get(ids=[player["player_id"]])
    # [실습 2] got["documents"] 에 글이 있으면 첫 번째를, 없으면 None 을 돌려주세요
    if got["documents"]:
        return got["documents"][0]
    return None


def search_docs(player: dict, question: str, k: int = config.TOP_K):
    """RAG2: 위키/팀 정보 청크를 의미 검색한다 (선수와 관련된 범위만)."""
    store = get_store(config.COL_DOCS)
    # [실습 3] 검색 글을 "선수이름 팀 질문" 모양으로 만드세요.
    #          ("이 선수" 같은 말만으로는 어느 선수인지 검색이 모르기 때문이에요)
    query = f"{player['name']} {player['team']} {question}"
    return store.similarity_search_with_score(query, k=k, filter=build_filter(player))


def retrieve(player: dict, question: str) -> list[dict]:
    """질문에 쓸 근거 목록. 항목: n(번호), kind, title, source_url, text, score"""
    evidence = []

    # [실습 4-1] 선수 정보 글이 있으면 근거에 추가하세요
    #   {"kind": "선수 정보", "title": f"{선수이름} 선수 정보",
    #    "source_url": player.get("source_url"), "text": 글, "score": None}
    player_chunk = get_player_chunk(player)
    if player_chunk:
        evidence.append({
            "kind": "선수 정보",
            "title": f"{player['name']} 선수 정보",
            "source_url": player.get("source_url"),
            "text": player_chunk,
            "score": None
        })
    

    # [실습 4-2] search_docs 결과(문서, 점수)마다 근거에 추가하세요
    #   {"kind": "문서", "title": 메타데이터의 doc_title, "source_url": 메타데이터의 source_url (없을 수 있음),
    #    "text": 문서의 page_content, "score": 점수}
    search_results = search_docs(player, question)
    for doc, score in search_results:
        evidence.append({
            "kind": "문서",
            "title": doc.metadata.get("doc_title"),
            "source_url": doc.metadata.get("source_url"),
            "text": doc.page_content,
            "score": score
        })


    # [실습 4-3] 근거마다 "n" 을 1부터 매기세요 (답변의 [근거 n] 인용에 쓰여요)
    for i, e in enumerate(evidence, start=1):
        e["n"] = i

    return evidence