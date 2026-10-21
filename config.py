"""프로젝트 설정 모음 — 값은 코드가 아니라 여기(와 .env)에서만 바꾼다 (F2005, F2006, NF2003)."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
MOVIES_JSON = DATA_DIR / "movies.json"
WIKI_DIR = DATA_DIR / "movielab_wiki" / "wikipedia"
CHROMA_DIR = ROOT / "chroma_db"

# --- 비밀값: 환경변수(.env)에서만 읽는다. 실습 폴더와 같은 이름 사용 ---
GMS_KEY = os.getenv("GMS_KEY", "")
WIKI_CONTACT = os.getenv("WIKI_CONTACT", "").strip()

# --- 모델 (실습 0단계와 동일한 GMS 설정) ---
GMS_BASE_URL = "https://gms.ssafy.io/gmsapi/api.openai.com/v1/"
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-5.4-nano")
# 임베딩 모델명은 check_env.py 로 GMS에서 실제 되는지 확인한 뒤 확정한다
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# --- 컬렉션 이름 ---
COL_META = "movie_meta"   # RAG 1: 영화 1편 = 청크 1개
COL_WIKI = "movie_wiki"   # RAG 2: 위키 문서 청크

# --- 검색/청킹 설정 (나중에 바꿔서 비교할 값) ---
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 6
SEARCH_TYPE = "similarity"   # 심화 F2014: "mmr"
