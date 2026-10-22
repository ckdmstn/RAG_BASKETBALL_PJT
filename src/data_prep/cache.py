"""데이터 준비 영역: 수집 캐시 (NF2002). 같은 검색어·같은 문서를 다시 받지 않게 기록한다."""
import json
from datetime import date

import config

CACHE_DIR = config.DATA_DIR / "cache"
QUERY_CACHE = CACHE_DIR / "queries.json"
PAGE_DIR = CACHE_DIR / "pages"


def _load(path, default):
    """JSON 파일을 읽는다. 파일이 아직 없으면 default 를 돌려준다."""
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save(path, data) -> None:
    """데이터를 JSON 파일로 저장한다. 폴더가 없으면 만든다."""
    # [실습 27] 세 줄을 쓴다.
    #   path.parent.mkdir(parents=True, exist_ok=True)      ← 폴더 만들기 (이미 있어도 오류 없이)
    #   with open(path, "w", encoding="utf-8") as f:        ← "w" = 쓰기 모드
    #       json.dump(data, f, ensure_ascii=False, indent=2)   ← 한글이 \uXXXX 로 깨지지 않게, 들여쓰기 2칸
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_query_record(query: str) -> dict | None:
    """이미 검색한 검색어면 저장된 후보 목록 기록을, 아니면 None 을 돌려준다."""
    return _load(QUERY_CACHE, {}).get(query.strip())


def put_query_record(query: str, candidates: list[dict]) -> None:
    """검색어의 검색 결과(후보 목록)를 기록한다."""
    records = _load(QUERY_CACHE, {})
    records[query.strip()] = {"candidates": candidates, "collected_at": str(date.today())}
    _save(QUERY_CACHE, records)


def save_page(page: dict) -> None:
    """받은 위키 문서(제목, 본문, URL 등)를 파일로 보관한다."""
    _save(PAGE_DIR / f"{page['page_id']}.json", page)


def load_page(page_id: int) -> dict | None:
    """보관한 문서를 읽는다. 없으면 None."""
    return _load(PAGE_DIR / f"{page_id}.json", None)