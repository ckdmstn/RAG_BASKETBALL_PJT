"""KBL 선수·팀 안내 화면. 검색과 LLM 호출은 src/ 에 있고, 여기서는 호출만 한다 (NF2005)."""
import streamlit as st

import config
from src.data_prep.players import load_players
from src.rag.pipeline import answer_question
from src.vectorstore.store import count, get_store

st.set_page_config(page_title="KBL 안내", page_icon="🏀")
st.title("🏀 KBL 선수 · 팀 안내")
st.caption("선수를 고르고 질문하면, 근거를 찾아 답하고 출처를 함께 보여 줍니다.")


@st.cache_data
def get_players() -> list[dict]:
    return load_players()


def render_sources(cited: list[dict]) -> None:
    """답변 아래 근거 목록. 답변이 실제로 인용한 근거만 보여 주고, 없으면 안내한다. (F2008)"""
    if not cited:
        st.caption("ⓘ 답변에 인용된 근거가 없습니다.")
        return
    with st.expander(f"답변에 사용한 근거 {len(cited)}건"):
        for e in cited:
            # [실습 1] 근거 하나를 이렇게 보여 주세요
            #   첫 줄:  **[근거 n]** (종류) 제목 · [원문](링크)     <- 링크(source_url)가 없으면 [원문] 부분은 생략
            #   둘째 줄: 본문 앞 200자 정도를 st.caption 으로 (줄바꿈은 공백으로 바꿔서)
            link = ""
            if e.get("source_url"):
                url = e["source_url"].replace("(", "%28").replace(")", "%29")
                link = f" · [원문]({url})"
            st.markdown(f"**[근거 {e['n']}]** ({e['kind']}) {e['title']}{link}")
            st.caption(e["text"][:200].replace("\n", " ") + " ...")
        st.caption("위키백과 문서는 CC BY-SA 4.0 라이선스입니다.")


players = get_players()
by_id = {p["player_id"]: p for p in players}

with st.sidebar:
    st.header("선수 선택")
    teams = sorted({p["team"] for p in players})
    team = st.selectbox("팀", teams, index=None, placeholder="팀을 고르세요")
    team_players = [p for p in players if p["team"] == team] if team else []
    player_id = st.selectbox(
        "선수",
        [p["player_id"] for p in team_players],
        format_func=lambda pid: f"{by_id[pid]['name']} ({by_id[pid]['jersey_number']}번)",
        index=None,
        placeholder="선수를 고르세요",
        key=f"player_{team}",          # 팀이 바뀌면 선수 선택이 초기화되도록 팀별로 다른 키
    )

    st.divider()
    st.subheader("색인 현황")
    # [실습 2] 두 컬렉션의 청크 수를 보여 주세요 (F2002)
    #   count(get_store(config.COL_PLAYERS)), count(get_store(config.COL_DOCS)) 를 st.caption 으로
    #   읽는 중 에러가 나면 "색인을 읽지 못했습니다" 라고만 보여 주세요 (try / except)
    try:
        player_count = count(get_store(config.COL_PLAYERS))
        doc_count = count(get_store(config.COL_DOCS))
        st.caption(f"선수 청크: {player_count}건, 문서 청크: {doc_count}건")
    except Exception:
        st.caption("색인을 읽지 못했습니다.")

if not player_id:
    st.info("왼쪽에서 팀과 선수를 먼저 고르세요.")
    st.stop()

player = by_id[player_id]
st.subheader(f"{player['name']} · {player['team']}")
st.caption(f"{player['position']} · 등번호 {player['jersey_number']}번")

# [실습 3] 선수별 대화 기록
#   chats    = st.session_state.setdefault("chats", {})      # {선수 id: 메시지 목록}
#   messages = chats.setdefault(player_id, [])                # 이 선수의 메시지 목록
#   사이드바에 "이 선수와의 대화 지우기" 버튼을 만들고, 누르면 messages.clear()
#   그리고 messages 를 순서대로 다시 그리세요. 메시지 모양: {"role", "content", "cited"}
#     - st.chat_message(m["role"]) 안에 st.markdown(m["content"])
#     - assistant 메시지는 render_sources(m["cited"]) 도 함께 (다시 그릴 때 근거가 사라지지 않도록)
chats = st.session_state.setdefault("chats", {})
messages = chats.setdefault(player_id, [])

if st.sidebar.button("이 선수와의 대화 지우기"):
    messages.clear()

for message in messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            render_sources(message["cited"])

question = st.chat_input(f"{player['name']} 선수에 대해 궁금한 점을 물어보세요")

if question:
    messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        out = None
        # [실습 4] 파이프라인을 호출하세요
        #   with st.status("답변을 준비하는 중...", expanded=True) as status:
        #       out = answer_question(player, question, on_progress=status.write)
        #       status.update(label="완료", state="complete", expanded=False)
        #   이 호출 전체를 try / except 로 감싸고, 에러가 나면 st.error("답변을 만들지 못했습니다. ...") 로 안내하세요
        try:
            with st.status("답변을 준비하는 중...", expanded=True) as status:
                out = answer_question(player, question, on_progress=status.write)
                status.update(label="완료", state="complete", expanded=False)
        except Exception:
            st.error("답변을 만들지 못했습니다. 잠시 후 다시 시도해 주세요.")

        # out 이 있으면 답변과 근거를 보여 주고, 대화 기록에 저장하세요
        #   st.markdown(out["answer"]) ; render_sources(out["cited"])
        #   messages.append({"role": "assistant", "content": out["answer"], "cited": out["cited"]})
        if out:
            st.markdown(out["answer"])
            render_sources(out["cited"])
            messages.append({"role": "assistant", "content": out["answer"], "cited": out["cited"]})