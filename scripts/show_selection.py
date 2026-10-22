from src.data_prep.cache import get_query_record
from src.data_prep.players import load_players
from src.data_prep.wiki import search
from src.rag.candidate_selection import select_candidates
from src.rag.collector import get_page
from src.rag.query_extraction import extract_queries

p = next(x for x in load_players() if x["name"] == "이민서" and x["team"] == "서울 SK 나이츠")
q = "이 선수 팀은 챔피언결정전에서 몇 번 우승했어?"

for query in extract_queries(p, q):
    record = get_query_record(query)
    cands = record["candidates"] if record else search(query)
    chosen = select_candidates(q, p, cands)
    chosen_ids = {c["page_id"] for c in chosen}
    print(f"검색어: {query}")
    for c in cands:
        mark = "선택" if c["page_id"] in chosen_ids else "버림"
        print(f"  [{mark}] {c['title']}")
    for c in chosen:
        page = get_page(c["page_id"], c["title"])
        print("   ->", c["title"], "본문 길이:", None if page is None else len(page["text"]))