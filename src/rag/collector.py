"""RAG 파이프라인 영역: 질문 1개에 대해 위키백과 문서를 수집한다 (F2003, F2004, NF2002)."""
import config

from datetime import date

from src.data_prep.cache import get_query_record, load_page, put_query_record, save_page
from src.data_prep.wiki import fetch_page, search
from src.rag.candidate_selection import is_own_doc, select_candidates
from src.rag.query_extraction import extract_queries
from src.data_prep.teams import load_teams


def get_page(page_id: int, title: str) -> dict | None:
    """보관한 문서가 있으면 그걸 쓰고, 없으면 위키에서 받아 보관한다."""
    # [실습 30] ① page = load_page(page_id) 가 있으면(None 이 아니면) 그대로 돌려준다.
    #           ② 없으면 page = fetch_page(title) 로 받는다.
    #           ③ 받았으면(None 이 아니면) page["collected_at"] = str(date.today()) 를 넣고 save_page(page) 로 보관한다.
    #           ④ page 를 돌려준다.
    page = load_page(page_id)
    if page is not None:
        return page
    page = fetch_page(title)
    if page is not None:
        page["collected_at"] = str(date.today())
        save_page(page)
    return page


def collect_documents(player: dict, question: str, on_progress=None) -> list[dict]:
    """질문에 쓸 위키 문서들을 모아 돌려준다. on_progress 는 진행 상황을 알려 주는 함수(화면 안내용, F2012)."""
    say = on_progress or (lambda message: None)

    say("검색어를 뽑는 중...")
    queries = extract_queries(player, question)
    say(f"검색어: {queries}")

    team_names = {t["team_name"] for t in load_teams()}
    docs, seen = [], set()
    for query in queries:
        record = get_query_record(query)
        if record is not None:
            say(f"이미 검색한 검색어: {query}")
            candidates = record["candidates"]
        else:
            say(f"위키백과 검색: {query}")
            candidates = search(query)
            put_query_record(query, candidates)      # 후보 목록을 기록 (비어 있어도)

        # 선별은 질문에 따라 달라지므로 매번 한다 (후보 제목·요약만 보내서 토큰이 적다)
        for c in select_candidates(question, player, candidates):
            if c["page_id"] in seen:
                continue
            page = get_page(c["page_id"], c["title"])
            if page is None:
                continue
            doc_team = None
            if is_own_doc(player, {"title": page["title"], "snippet": page["text"][:300]}):
                scope = "player"
            elif page["title"] in team_names:
                scope = "team"
                doc_team = page["title"]          # 선수 팀이 아니라 '문서가 다루는 팀'
            else:
                scope = "league"
            if scope != "player" and len(page["text"]) < config.MIN_DOC_CHARS:
                say(f"너무 짧아 제외: {page['title']} ({len(page['text'])}자)")
                continue
            seen.add(c["page_id"])
            docs.append({
                **page,
                "scope": scope,
                "player_id": player["player_id"] if scope == "player" else None,
                "team": doc_team,
            })
    return docs