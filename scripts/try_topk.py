# scripts/try_topk.py
# Top-k(3/6/10)에 따라 문서 근거가 어떻게 달라지는지 본다. (4.3, 설계문서의 Top-k 설명 재료)
# 실행: python -m scripts.try_topk
import json

import config
from src.rag.retrieval import search_docs

with open(config.PLAYERS_JSON, encoding="utf-8") as f:
    data = json.load(f)
players = data["players"] if isinstance(data, dict) else data
player = next(p for p in players if p["name"] == "박정웅")
question = "정관장은 창단 첫 우승을 언제 했어?"

for k in (3, 6, 10):
    print(f"\n== Top-k = {k}")
    for i, r in enumerate(search_docs(player, question, k), start=1):
        # 반환이 (문서, 점수) 이거나 문서 하나일 수 있어서 둘 다 처리한다
        doc, score = r if isinstance(r, tuple) else (r, None)
        title = doc.metadata.get("doc_title", "")
        head = doc.page_content.replace("\n", " ")[:40]
        print(i, title, f"{score:.3f}" if score is not None else "-", "|", head)