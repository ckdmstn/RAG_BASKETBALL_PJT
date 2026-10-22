"""LangGraph: 질문 -> 검색(retrieve) -> 답변 생성(generate)."""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from src.rag.citations import pick_cited_evidence
from src.rag.generation import generate_answer
from src.rag.retrieval import retrieve


class RagState(TypedDict, total=False):
    player: dict          # 선택한 선수
    question: str         # 질문
    evidence: list[dict]  # 검색한 근거 (retrieve 노드가 채움)
    answer: str           # 답변 (generate 노드가 채움)
    cited: list[dict]     # 답변이 실제 인용한 근거 (generate 노드가 채움)


def retrieve_node(state: RagState) -> dict:
    # [실습 10] state 의 player, question 으로 retrieve 를 호출하고
    #           {"evidence": 결과} 를 돌려주세요 (바꿀 값만 돌려줘요)
    evidence = retrieve(state["player"], state["question"])
    return {"evidence": evidence}


def generate_node(state: RagState) -> dict:
    # [실습 11] state 의 player, question, evidence 로 generate_answer 를 호출하고,
    #           pick_cited_evidence(answer, evidence) 로 인용된 근거를 골라
    #           {"answer": 답변, "cited": 인용된 근거} 를 돌려주세요
    answer = generate_answer(state["player"], state["question"], state["evidence"])
    cited = pick_cited_evidence(answer, state["evidence"])
    return {"answer": answer, "cited": cited}


def build_graph():
    graph = StateGraph(RagState)
    # [실습 12] 노드 두 개를 추가하세요: graph.add_node("이름", 함수)
    #           선을 연결하세요: graph.add_edge(START, "retrieve") -> "retrieve" -> "generate" -> END
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)

    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)

    return graph.compile()