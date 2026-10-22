import html
import re
import time

import requests
import config

API_URL = "https://ko.wikipedia.org/w/api.php"

# [실습 20] User-Agent 를 우리 프로젝트용으로 만든다. (NF2006)
#   연락처는 config.WIKI_CONTACT. 앱 이름은 KBLRagStudy/0.1 로.
#   샘플의 USER_AGENT = ... 두 줄을 아래 모양으로 바꾼다.
USER_AGENT = (f"KBLRagStudy/0.1 ({config.WIKI_CONTACT}) python-requests" 
              if config.WIKI_CONTACT else "KBLRagStudy/0.1 python-requests")


def request_wikipedia(params: dict, max_retries: int = 4) -> dict:
    """위키백과 API를 호출합니다. 429(요청이 너무 많음)를 받으면 기다렸다가 다시 요청합니다."""
    time.sleep(0.4)      # [실습 21] 요청마다 먼저 잠깐 쉰다 (호출 간격 규칙)
    wait = 2.0
    for attempt in range(1, max_retries + 1):
        response = requests.get(
            API_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=20
        )
        if response.status_code == 200:
            return response.json()
        if response.status_code == 429:
            # 서버가 알려 주는 대기 시간을 따르고, 없으면 점점 길게 기다립니다.
            retry_after = float(response.headers.get("Retry-After") or wait)
            print(f"[429] {retry_after:.0f}초 기다린 뒤 다시 요청합니다 ({attempt}/{max_retries})")
            time.sleep(retry_after)
            wait *= 2
            continue
        response.raise_for_status()
    raise RuntimeError("요청 제한이 계속되어 실패했습니다. 잠시 뒤 다시 실행해 주세요.")


def search(query: str, limit: int = 5) -> list[dict]:
    """① 검색어로 후보 문서를 찾습니다. 본문은 주지 않고 제목과 짧은 요약만 줍니다."""
    data = request_wikipedia({
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
        "format": "json",
        "formatversion": 2,
    })
    return [
        {
            "page_id": item["pageid"],
            "title": item["title"],
            # 요약에는 <span class="searchmatch"> 같은 강조 태그가 섞여 있어 지웁니다.
            "snippet": html.unescape(re.sub(r"<[^>]+>", "", item.get("snippet", ""))),
        }
        for item in data["query"]["search"]
    ]


def fetch_page(title: str) -> dict | None:
    """② 문서 제목으로 본문과 원문 URL을 받습니다. 없는 문서면 None 을 돌려줍니다."""
    data = request_wikipedia({
        "action": "query",
        "prop": "extracts|info",
        "titles": title,
        "explaintext": 1,     # 태그 없는 본문 텍스트
        "inprop": "url",      # 원문 URL
        "redirects": 1,       # 넘겨주기 문서를 따라가 실제 문서를 받음
        "format": "json",
        "formatversion": 2,
    })
    page = data["query"]["pages"][0]
    if page.get("missing"):
        return None
    return {
        "page_id": page["pageid"],
        "title": page["title"],
        "url": page["fullurl"],
        "text": page.get("extract", ""),
    }