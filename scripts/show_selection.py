from src.data_prep.cache import get_query_record
from src.data_prep.players import load_players
from src.data_prep.wiki import search
from src.rag.candidate_selection import select_candidates
from src.rag.query_extraction import extract_queries

p = next(x for x in load_players() if x["name"] == "박정웅")
q = "이 선수가 속한 팀은 어떤 팀이야?"

for query in extract_queries(p, q):
    record = get_query_record(query)
    cands = record["candidates"] if record else search(query)
    chosen = {c["page_id"] for c in select_candidates(q, p, cands)}
    print(f"검색어: {query}")
    for c in cands:
        mark = "선택" if c["page_id"] in chosen else "버림"
        print(f"  [{mark}] {c['title']}")