"""답변에서 [근거 n] 인용을 읽어 실제로 쓰인 근거만 골라낸다 (F2008)."""
import re

CITATION_PATTERN = re.compile(r"\[근거\s*([\d\s,]+)\]")


def parse_citation_numbers(answer: str) -> list[int]:
    """답변 속 [근거 n] 의 번호들 -> 중복 없이 작은 수부터."""
    # [실습 8] CITATION_PATTERN.findall(answer) 로 괄호 안 글들을 꺼내고,
    #          "1, 3" 처럼 쉼표로 여러 개가 들어 있어도 모두 정수로 바꿔 모으세요.
    #          중복을 없애고 정렬해서 돌려주세요.
    citation_numbers = set()
    for match in CITATION_PATTERN.findall(answer):
        for num in re.findall(r"\d+", match):
            citation_numbers.add(int(num))
    return sorted(citation_numbers)


def pick_cited_evidence(answer: str, evidence: list[dict]) -> list[dict]:
    """evidence 중 답변이 인용한 것만, 번호 순서로. 목록에 없는 번호는 무시한다."""
    # [실습 9] parse_citation_numbers 결과 중 evidence 에 실제로 있는 "n" 의 근거만 돌려주세요
    cited_numbers = parse_citation_numbers(answer)
    return [e for e in evidence if e["n"] in cited_numbers]