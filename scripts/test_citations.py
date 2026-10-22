from src.rag.citations import parse_citation_numbers, pick_cited_evidence

ev = [{"n": i, "title": f"문서{i}"} for i in range(1, 5)]

assert parse_citation_numbers("A. [근거 2][근거 1] B. [근거 2]") == [1, 2]
assert parse_citation_numbers("A. [근거 1, 3]") == [1, 3]
assert parse_citation_numbers("근거 인용 없음") == []
assert [e["n"] for e in pick_cited_evidence("[근거 3] [근거 99]", ev)] == [3]
assert parse_citation_numbers("[근거 1 3] [근거 ,]") == [1, 3]
print("모두 통과")