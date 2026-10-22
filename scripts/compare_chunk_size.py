import config
from src.data_prep.cache import load_page
from src.rag.chunking import split_doc

doc = {**load_page(315053), "scope": "team", "player_id": None, "team": "안양 정관장 레드부스터스"}
for size, overlap in [(1000, 200), (500, 100)]:
    config.CHUNK_SIZE, config.CHUNK_OVERLAP = size, overlap
    print(f"크기 {size} / 겹침 {overlap} → 청크 {len(split_doc(doc))}개")