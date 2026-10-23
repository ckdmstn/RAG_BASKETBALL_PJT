# scripts/measure_time.py
# 질문 1건의 응답 시간을 잰다. (NF2001)
# 실행: python -m scripts.measure_time
import json
import time

import config
from src.rag.pipeline import answer_question

# 선수 데이터 파일에서 박정웅을 찾는다 (JSON 형태에 따라 리스트 또는 {"players": [...]})
with open(config.PLAYERS_JSON, encoding="utf-8") as f:
    data = json.load(f)
players = data["players"] if isinstance(data, dict) else data
player = next(p for p in players if p["name"] == "박정웅")

question = "이 선수가 속한 팀은 창단 첫 우승을 언제 했어?"

for label in ("1회차(수집·색인 포함)", "2회차(캐시 사용)"):
    start = time.perf_counter()
    result = answer_question(player, question, on_progress=lambda msg: None)
    sec = time.perf_counter() - start
    print(f"{label}: {sec:.1f}초 / 인용 {len(result['cited'])}건")