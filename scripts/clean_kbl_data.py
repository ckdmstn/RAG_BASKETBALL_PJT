"""KBL 원본 JSON 정리: 파일 끝에 붙은 {"sources_summary"}/{"notes"} 줄을 분리하고, 선수 ID를 붙인다.

사용:  python scripts/clean_kbl_data.py
입력:  data/kbl/*_roster.json , data/kbl/kbl_teams.json          (AI가 만든 원본 — 수정하지 않는다)
출력:  data/kbl_players.json       유효한 JSON 배열 (선수 ID 포함)      → F2001 에서 읽는 파일
       data/kbl_teams.json         팀 정보 10건
       data/kbl_source_notes.json  출처·이용조건·AI 메모 모음         → NF2007 기록의 재료
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "kbl"
OUT = ROOT / "data"

# 팀 이름 속 키워드 → 팀 코드 (선수 ID 접두어)
TEAM_CODES = [("한국가스공사", "kogas"), ("현대모비스", "mobis"), ("정관장", "jkj"), ("삼성", "samsung"),
              ("소노", "sono"), ("SK", "sk"), ("DB", "db"), ("KCC", "kcc"), ("LG", "lg"), ("KT", "kt")]


def team_code(team: str) -> str:
    for key, code in TEAM_CODES:
        if key in team:
            return code
    raise ValueError(f"알 수 없는 팀: {team}")


def read_values(path: Path) -> list:
    """파일 안에 이어 붙어 있는 JSON 값들을 전부 읽는다 (배열 1개 + 객체 여러 줄)."""
    text, dec, i, values = path.read_text(encoding="utf-8"), json.JSONDecoder(), 0, []
    while True:
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text):
            return values
        obj, i = dec.raw_decode(text, i)
        values.append(obj)


def main() -> int:
    players, notes = [], []
    for path in sorted(RAW.glob("*_roster.json")):
        first, *rest = read_values(path)
        for p in first:
            p.pop("ko_wiki_title", None)     # AI가 확인 못 한 값 — 위키 문서 연결은 우리 코드가 판정한다
            p["_file"] = path.name
        players += first
        notes.append({"file": path.name, "team": first[0]["team"], "count": len(first),
                      **{k: v for obj in rest for k, v in obj.items()}})

    # 선수 ID: 이름은 겹칠 수 있다(이정현, 최승욱 …) → "팀코드-등번호"
    for p in players:
        p["player_id"] = f"{team_code(p['team'])}-{p['jersey_number']}"
        del p["_file"]
    dup = [k for k, v in Counter(p["player_id"] for p in players).items() if v > 1]
    if dup:
        print("선수 ID 중복 — 등번호가 같은 선수가 있습니다:", dup)
        return 1

    teams = read_values(RAW / "kbl_teams.json")
    team_notes = [o for o in teams[1:]]
    teams = teams[0]
    if team_notes:
        notes.append({"file": "kbl_teams.json", "count": len(teams),
                      **{k: v for obj in team_notes for k, v in obj.items()}})

    players.sort(key=lambda p: (p["team"], p["jersey_number"] if p["jersey_number"] is not None else 999))
    (OUT / "kbl_players.json").write_text(json.dumps(players, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "kbl_teams.json").write_text(json.dumps(teams, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "kbl_source_notes.json").write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")

    names = Counter(p["name"] for p in players)
    print(f"선수 {len(players)}명 / 팀 {len(teams)}개 / 선수 ID 중복 없음")
    print("이름이 같은 선수:", {n: [p['player_id'] for p in players if p['name'] == n] for n, c in names.items() if c > 1})
    return 0


if __name__ == "__main__":
    sys.exit(main())
