"""팀 정보(kbl_teams.json) -> 청크 (kbl_docs 에 scope=team 으로 저장)."""
import json

import config


def load_teams() -> list[dict]:
    with open(config.TEAMS_JSON, encoding="utf-8") as f:
        return json.load(f)


def build_team_text(t: dict) -> str:
    lines = [f"[{t['team_name']} 팀 정보]"]
    lines.append(f"팀: {t['team_name']} (연고지 {t['city']}, 홈구장 {t['home_arena']})")
    lines.append(f"창단: {t['founded_year']}년 / 모기업: {t['parent_company']}")

    # [실습 1] 아래 세 줄을 값이 있을 때만 추가하세요 (없으면 줄째 생략)
    #   "이전 이름: " + former_names 를 ", " 로 이은 것     (목록이에요)
    #   "우승: " + championships
    #   "소개: " + team_summary
    if t.get("former_names"):
        lines.append("이전 이름: " + ", ".join(t["former_names"]))

    if t.get("championships"):
        lines.append("우승: " + t["championships"])

    if t.get("team_summary"):
        lines.append("소개: " + t["team_summary"])

    return "\n".join(lines)


def build_team_chunk(t: dict) -> dict:
    """팀 1건 -> upsert_chunks 에 넣을 수 있는 청크 1개 (위키 청크와 같은 모양)"""
    # [실습 2] metadata 를 채우세요
    metadata = {
        "doc_id": f"info-{t['team_name']}",
        "doc_title": t["team_name"],
        "source_url": t["source_urls"][0] if t.get("source_urls") else None,
        "source_type": "team_info",
        "scope": "team",
        "team": t["team_name"],
        "collected_at": t.get("data_as_of"),
        "chunk_seq": 0,
    }
    metadata = {k: v for k, v in metadata.items() if v is not None}

    return {
        "id": f"team:info-{t['team_name']}:0",
        "text": build_team_text(t),
        "metadata": metadata,
    }