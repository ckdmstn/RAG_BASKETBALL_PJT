"""KBL 선수 ↔ 한국어 위키백과 문서 정밀 점검 (v2).

사용:  python scripts/check_wiki_coverage_v2.py data/kbl/*.json
       (.env 에 WIKI_CONTACT = 영문 이메일 필요)

선수마다 아래 중 하나로 판정한다.
  CATEGORY   팀 선수 카테고리에 문서가 있다            → 선수 본인 문서 확실
  BASKETBALL 같은 이름 문서의 분류에 '농구'가 있다       → 선수 본인일 가능성 높음
  DISAMBIG   동음이의(여러 사람) 문서다                  → 본인 문서 아님 (괄호 제목을 따로 찾아야 함)
  OTHER      같은 이름 문서가 있지만 농구와 무관하다      → 다른 사람 (예: 야구선수)
  MISSING    문서 없음
마지막에 '다른 팀 선수 카테고리 후보'도 찾아서 보여 준다.
"""
import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

API = "https://ko.wikipedia.org/w/api.php"
KNOWN_CATS = ["분류:안양 정관장 레드부스터스 선수", "분류:서울 삼성 썬더스 선수"]
TEAM_KEYWORDS = ["정관장", "삼성 썬더스", "현대모비스", "KCC 이지스", "SK 나이츠",
                 "KT 소닉붐", "DB 프로미", "LG 세이커스", "한국가스공사", "소노 스카이거너스"]


def session():
    if not config.WIKI_CONTACT or not config.WIKI_CONTACT.isascii():
        raise SystemExit("WIKI_CONTACT 를 .env 에 영문 이메일로 넣어 주세요 (NF2006).")
    s = requests.Session()
    s.headers["User-Agent"] = f"MovieLabStudy/0.1 ({config.WIKI_CONTACT}) requests"
    return s


def get(s, **params):
    params.update(format="json", formatversion=2)
    r = s.get(API, params=params, timeout=20)
    r.raise_for_status()
    time.sleep(0.3)
    return r.json()


def load_players(paths):
    dec, players = json.JSONDecoder(), []
    for p in paths:
        arr, _ = dec.raw_decode(Path(p).read_text(encoding="utf-8").lstrip())
        players += arr
    return players


def category_members(s, cat):
    out, cont = [], {}
    while True:
        d = get(s, action="query", list="categorymembers", cmtitle=cat,
                cmtype="page", cmlimit=500, **cont)
        out += [m["title"] for m in d["query"]["categorymembers"]]
        if "continue" in d:
            cont = d["continue"]
        else:
            return out


def page_info(s, names):
    """이름 그대로의 문서: 동음이의 여부 / 분류 / 소개 첫 문장"""
    info = {}
    for i in range(0, len(names), 20):
        batch = names[i:i + 20]
        params = dict(action="query", titles="|".join(batch), redirects=1,
                      prop="pageprops|categories|extracts", ppprop="disambiguation",
                      cllimit="max", exintro=1, explaintext=1, exlimit="max", exchars=120)
        pages, back, cont = {}, {}, {}
        while True:
            d = get(s, **params, **cont)
            q = d["query"]
            for n in q.get("normalized", []):
                back[n["to"]] = n["from"]
            for rd in q.get("redirects", []):
                back[rd["to"]] = back.get(rd["from"], rd["from"])
            for pg in q["pages"]:
                cur = pages.setdefault(pg["title"], {"cats": [], "extract": "", "disambig": False,
                                                      "missing": bool(pg.get("missing"))})
                cur["cats"] += [c["title"] for c in pg.get("categories", [])]
                cur["extract"] = cur["extract"] or pg.get("extract", "")
                cur["disambig"] = cur["disambig"] or ("disambiguation" in pg.get("pageprops", {}))
            if "continue" in d:
                cont = d["continue"]
            else:
                break
        for title, v in pages.items():
            if not v["missing"]:
                info[back.get(title, title)] = dict(v, title=title)
    return info


def main(paths):
    s = session()
    players = load_players(paths)
    names = [p["name"] for p in players]
    print(f"선수 {len(names)}명\n")

    members = set()
    for cat in KNOWN_CATS:
        m = category_members(s, cat)
        members.update(m)
        print(f"[카테고리] {cat}: {len(m)}건")
    print()

    def in_category(name):
        return [t for t in members if t == name or t.startswith(name + " (")]

    info = page_info(s, names)
    verdict = {}
    for n in names:
        hit = in_category(n)
        pi = info.get(n)
        if hit:
            verdict[n] = ("CATEGORY", hit[0])
        elif pi and pi["disambig"]:
            verdict[n] = ("DISAMBIG", pi["title"])
        elif pi and any("농구" in c for c in pi["cats"]):
            verdict[n] = ("BASKETBALL", pi["title"])
        elif pi:
            verdict[n] = ("OTHER", pi["extract"][:60].replace("\n", " "))
        else:
            verdict[n] = ("MISSING", "")

    order = ["CATEGORY", "BASKETBALL", "DISAMBIG", "OTHER", "MISSING"]
    for key in order:
        rows = [(n, v[1]) for n, v in verdict.items() if v[0] == key]
        print(f"■ {key}: {len(rows)}명")
        for n, extra in rows:
            print(f"    {n}  {extra}")
        print()
    ok = sum(1 for v in verdict.values() if v[0] in ("CATEGORY", "BASKETBALL"))
    print(f"==> 선수 본인 문서가 있다고 볼 수 있는 선수: {ok} / {len(names)}\n")

    print("[다른 팀 카테고리 후보 찾기]  ('분류:...' 이름을 복사해 KNOWN_CATS 에 추가)")
    for kw in TEAM_KEYWORDS:
        d = get(s, action="query", list="search", srnamespace=14, srsearch=f"{kw} 선수", srlimit=3)
        print(f"  {kw}: {[x['title'] for x in d['query']['search']]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(sys.argv[1:])
