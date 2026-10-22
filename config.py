"""프로젝트 설정 모음 — 값은 코드가 아니라 여기(와 .env)에서만 바꾼다 (F2005, F2006, NF2003)."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
PLAYERS_JSON = DATA_DIR / "kbl_players.json"   # clean_kbl_data.py 가 만든 파일
TEAMS_JSON = DATA_DIR / "kbl_teams.json"
DOCS_DIR = DATA_DIR / "kbl_docs"               # 규정 PDF
CHROMA_DIR = ROOT / "chroma_db"

# --- 비밀값: 환경변수(.env)에서만 읽는다 ---
GMS_KEY = os.getenv("GMS_KEY", "")
WIKI_CONTACT = os.getenv("WIKI_CONTACT", "").strip()

# --- 모델 ---
GMS_BASE_URL = "https://gms.ssafy.io/gmsapi/api.openai.com/v1/"
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-5.4-nano")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# --- 컬렉션 이름 ---
COL_PLAYERS = "kbl_players"   # RAG 1: 선수 1명 = 청크 1개
COL_DOCS = "kbl_docs"         # RAG 2: 위키백과 · PDF · 팀 정보 청크

# --- 검색/청킹 설정 (나중에 바꿔서 비교할 값) ---
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 6
SEARCH_TYPE = "similarity"   # 심화 F2014: "mmr"

MAX_SELECTED = 3   # 검색어 하나당 색인할 문서 최대 수 (프롬프트 2가 고르는 개수의 상한)
MIN_DOC_CHARS = 500   # 이보다 짧은 위키 문서는 근거로 쓰기 어려워 제외 (선수 본인 문서는 예외)