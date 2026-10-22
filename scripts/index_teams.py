"""팀 정보 10건을 kbl_docs 에 색인한다."""
import config
from src.data_prep.players import load_players
from src.data_prep.teams import load_teams, build_team_chunk
from src.vectorstore.store import get_store, upsert_chunks, count


def main():
    teams = load_teams()
    chunks = [build_team_chunk(t) for t in teams]

    store = get_store(config.COL_DOCS)
    print("색인 전 청크 수:", count(store))

    # [실습 3] upsert_chunks 로 저장하고 "새로 저장: n / 건너뜀: m" 을 출력하세요
    added, skipped = upsert_chunks(store, chunks)
    print(f"새로 저장: {added} / 건너뜀: {skipped}")

    print("색인 후 청크 수:", count(store))

    # 선수 데이터의 팀 이름과 팀 정보의 이름이 같은지 검사 (필터가 맞으려면 같아야 함)
    player_teams = {p["team"] for p in load_players()}
    team_names = {t["team_name"] for t in teams}
    print("선수에만 있는 팀 이름:", player_teams - team_names)
    print("팀 정보에만 있는 팀 이름:", team_names - player_teams)

    print()
    hits = store.similarity_search_with_score("서울 SK 나이츠는 챔피언결정전에서 몇 번 우승했어?", k=3)
    for d, score in hits:
        m = d.metadata
        print(round(score, 3), m["doc_title"], m["scope"], m["source_type"])


if __name__ == "__main__":
    main()