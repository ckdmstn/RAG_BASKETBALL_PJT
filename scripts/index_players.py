"""선수 메타데이터 색인 (F2001~F2002).

    python scripts/index_players.py --dry-run     # API 호출 없이 글 모양만 확인 (토큰 0)
    python scripts/index_players.py --limit 5     # 5명만 색인해서 시험
    python scripts/index_players.py               # 전체 색인
"""
import argparse
import sys
from pathlib import Path

# scripts/ 폴더에서 실행해도 프로젝트 루트의 src/ 를 찾을 수 있게 한다
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from src.data_prep.players import build_metadata, build_text, load_players
from src.vectorstore.store import count, get_store


def index_players(store, players: list[dict]) -> tuple[int, int]:
    # [실습 11] 선수 목록에서 세 가지 리스트를 만든다.
    #   ids   = 선수마다 player_id          (청크의 고유 번호)
    #   texts = 선수마다 build_text(p)      (임베딩할 글)
    #   metas = 선수마다 build_metadata(p)  (꼬리표)
    ids = [p["player_id"] for p in players]
    texts = [build_text(p) for p in players]
    metas = [build_metadata(p) for p in players]

    # [실습 13] 이미 저장된 글을 가져와 {player_id: 저장된 글} 사전을 만든다.
    old = store.get(ids=ids)
    saved = dict(zip(old["ids"], old["documents"]))

    # [실습 14] '새로 저장해야 할 선수의 순번'만 모은다.
    #   조건: 저장된 글(saved.get(ids[i]))이 지금 글(texts[i])과 다르면 (저장이 없으면 None 이라 다름)
    todo = [i for i in range(len(ids)) if saved.get(ids[i]) != texts[i]]

    # [실습 15] todo 가 비어 있지 않을 때만, 그 선수들만 저장한다.
    if todo:
        store.add_texts(
            texts=[texts[i] for i in todo],
            metadatas=[metas[i] for i in todo],
            ids=[ids[i] for i in todo],
        )
    
    return len(todo), len(players) - len(todo)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="API 호출 없이 글 모양만 출력")
    ap.add_argument("--limit", type=int, help="앞에서 N명만 색인")
    ap.add_argument("--search", help="색인된 선수에서 의미 검색") 
    args = ap.parse_args()

    if args.search:
        store = get_store(config.COL_PLAYERS)
        # [실습 16] 질문과 뜻이 가까운 선수 5명을 찾아서 출력한다.
        #   results = store.similarity_search_with_score(args.search, k=5)
        #     → (청크, 거리) 쌍이 5개 돌아온다. 거리가 작을수록 질문과 뜻이 가깝다.
        #   각 쌍에서 꼬리표는 doc.metadata 로 꺼낸다.
        #   출력 모양:  0.812  박정웅 (안양 정관장 레드부스터스) 홍익대학교사범대학부속고등학교
        results = store.similarity_search_with_score(args.search, k=5)
        for doc, dist in results:
            m = doc.metadata
            print(f"{dist:.3f}  {m['name']} ({m['team']}) {m.get('school', '')}")
        return 0

    players = load_players()
    if args.limit:
        players = players[: args.limit]
    print(f"읽은 선수: {len(players)}명")

    if args.dry_run:
        for p in players[:3]:
            print("-" * 50)
            print(build_text(p))
            print("메타데이터:", build_metadata(p))
        return 0

    if not config.GMS_KEY:
        print("GMS_KEY 가 없습니다. .env 를 확인하세요.")
        return 1

    store = get_store(config.COL_PLAYERS)
    new, skipped = index_players(store, players)
    print(f"새로 색인/갱신: {new}건, 건너뜀(이미 같음): {skipped}건")
    print(f"컬렉션 '{config.COL_PLAYERS}' 저장된 청크 수: {count(store)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())