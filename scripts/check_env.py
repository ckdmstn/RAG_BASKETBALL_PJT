"""환경 점검.   실행: python scripts/check_env.py   (프로젝트 폴더에서)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


def main() -> int:
    ok = True
    print(f"[1] 선수 데이터 kbl_players.json: {config.PLAYERS_JSON.exists()} / 팀 정보 kbl_teams.json: {config.TEAMS_JSON.exists()}")
    ok &= config.PLAYERS_JSON.exists() and config.TEAMS_JSON.exists()

    print(f"[2] GMS_KEY: {'있음' if config.GMS_KEY else '없음'} (값은 출력하지 않음) / WIKI_CONTACT: {'있음' if config.WIKI_CONTACT else '없음'}")
    if not config.GMS_KEY:
        return 1

    from openai import OpenAI
    client = OpenAI(api_key=config.GMS_KEY, base_url=config.GMS_BASE_URL, timeout=20, max_retries=0)
    try:
        e = client.embeddings.create(model=config.EMBEDDING_MODEL, input="인터스텔라")
        print(f"[3] 임베딩 OK  모델={config.EMBEDDING_MODEL}  차원={len(e.data[0].embedding)}")
    except Exception as ex:
        print(f"[3] 임베딩 실패 (모델={config.EMBEDDING_MODEL}):", type(ex).__name__, str(ex)[:300]); ok = False
    try:
        r = client.chat.completions.create(
            model=config.CHAT_MODEL, messages=[{"role": "user", "content": "한 단어로 '안녕'이라고만 답해."}])
        print(f"[4] LLM OK  모델={config.CHAT_MODEL}  응답={r.choices[0].message.content!r}")
    except Exception as ex:
        print("[4] LLM 실패:", type(ex).__name__, str(ex)[:300]); ok = False

    print("\n결과:", "모두 통과" if ok else "실패 항목 있음")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
