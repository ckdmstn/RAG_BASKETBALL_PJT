"""KBL 선수·팀 안내 화면. 검색과 LLM 호출은 src/ 에 있고, 여기서는 호출만 한다 (NF2005)."""
import streamlit as st

import config
from src.data_prep.players import load_players
from src.rag.pipeline import answer_question
from src.rag.player_search import find_players
from src.rag.team_guide import make_team_guide
from src.vectorstore.store import count, get_store

st.set_page_config(page_title="KBL 안내", page_icon="🏀")
st.title("🏀 KBL 선수 · 팀 안내")
st.caption("선수를 고르고 질문하면, 근거를 찾아 답하고 출처를 함께 보여 줍니다.")

VIEWS = ["선수에게 질문", "팀 가이드", "선수 찾기"]


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


def open_chat(team: str, player_id: str) -> None:
    """선수 카드의 '대화하기' 버튼: 사이드바 선택을 그 선수로 맞추고 대화 화면으로 이동한다.
    (on_click 콜백은 화면을 다시 그리기 전에 실행되므로 위젯 상태를 바꿀 수 있다)"""
    st.session_state["sb_team"] = team
    st.session_state[f"player_{team}"] = player_id
    st.session_state["view"] = "선수에게 질문"


def render_chat(player: dict) -> None:
    """선수와의 대화 화면."""
    player_id = player["player_id"]
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


def render_team_guide(team_names: list[str]) -> None:
    """팀 가이드 화면 (F2010)."""
    st.subheader("팀 가이드")
    guide_team = st.selectbox(
        "가이드를 볼 팀", team_names, index=None, placeholder="팀을 고르세요", key="guide_team"
    )
    if not guide_team:
        st.info("팀을 고르면 연고지·역사·성적·선수단을 정리해 드립니다.")
        return

    guides = st.session_state.setdefault("guides", {})     # {팀: 가이드 결과} (한 번 만든 건 저장해 토큰을 아낀다)
    label = "다시 만들기" if guide_team in guides else "가이드 만들기"

    # [실습 5] 버튼을 누르면 가이드를 만들어 guides[team] 에 저장하세요
    #   if st.button(label):
    #       with st.status("팀 가이드를 준비하는 중...", expanded=True) as status:
    #           (try) guides[team] = make_team_guide(team, on_progress=status.write)
    #                 status.update(label="완료", state="complete", expanded=False)
    #           (except) status.update(label="실패", state="error") 하고 st.error("팀 가이드를 만들지 못했습니다. ...")
    if st.button(label):
        with st.status("팀 가이드를 준비하는 중...", expanded=True) as status:
            try:
                guides[guide_team] = make_team_guide(guide_team, on_progress=status.write)
                status.update(label="완료", state="complete", expanded=False)
            except Exception:
                status.update(label="실패", state="error")
                st.error("팀 가이드를 만들지 못했습니다. 잠시 후 다시 시도해 주세요.")

    # 만들어 둔 가이드가 있으면 보여 주기 (다른 위젯을 눌러 화면이 다시 그려져도 유지됨)
    if guide_team in guides:
        st.markdown(guides[guide_team]["answer"])
        render_sources(guides[guide_team]["cited"])


def render_player_search() -> None:
    """선수 찾기 화면 (F2011): 조건을 글로 적으면 조건에 맞는 선수 카드를 보여 준다."""
    st.subheader("선수 찾기")
    st.caption("조건을 글로 적어 주세요. 예: 고려대 출신 가드 / 고양 소노의 외국인 선수 중 키 큰 순서로 3명 / 190cm 이상 국내 포워드")
    text = st.text_input("찾을 조건", key="find_text", placeholder="예: NBA에서 뛴 적이 있는 외국인 센터")

    if st.button("찾기") and text.strip():
        with st.status("선수를 찾는 중...", expanded=True) as status:
            try:
                st.session_state["find_result"] = find_players(text.strip(), on_progress=status.write)
                status.update(label="완료", state="complete", expanded=False)
            except Exception:
                st.session_state.pop("find_result", None)
                status.update(label="실패", state="error")
                st.error("선수를 찾지 못했습니다. 잠시 후 다시 시도해 주세요.")

    result = st.session_state.get("find_result")
    if not result:
        return

    # 해석한 조건을 보여 준다 (조건이 어떻게 이해됐는지 사용자가 확인할 수 있도록)
    shown_cond = {k: v for k, v in result["conditions"].items() if v not in (None, [])}
    st.caption(f"해석한 조건: {shown_cond}")
    if result["note"]:
        st.caption(result["note"])

    found = result["players"]
    if not found:
        st.info("조건에 맞는 선수를 찾지 못했습니다. 조건을 바꿔 보세요.")
        return

    cards = found[:12]
    st.write(f"{len(found)}명을 찾았습니다." + (f" (앞 {len(cards)}명만 표시)" if len(found) > len(cards) else ""))
    cols = st.columns(3)
    for i, p in enumerate(cards):
        with cols[i % 3].container(border=True):
            st.markdown(f"**{p['name']}**")
            st.caption(f"{p['team']} · {p['position']} · {p['jersey_number']}번")
            details = []
            if p.get("height_cm"):
                details.append(f"{p['height_cm']}cm")
            if p.get("weight_kg"):
                details.append(f"{p['weight_kg']}kg")
            if p.get("birth_year"):
                details.append(f"{p['birth_year']}년생")
            if p.get("school"):
                details.append(p["school"])
            st.caption(" · ".join(details))
            st.button("이 선수와 대화하기", key=f"open_{p['player_id']}",
                      on_click=open_chat, args=(p["team"], p["player_id"]))


players = get_players()
by_id = {p["player_id"]: p for p in players}

with st.sidebar:
    st.header("선수 선택")
    teams = sorted({p["team"] for p in players})
    team = st.selectbox("팀", teams, index=None, placeholder="팀을 고르세요", key="sb_team")
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

# 화면 선택 (탭 대신 radio: 코드로 화면을 바꿀 수 있어야 '카드 -> 대화' 이동이 된다)
view = st.radio("화면", VIEWS, horizontal=True, key="view", label_visibility="collapsed")

if view == "선수에게 질문":
    if player_id:
        render_chat(by_id[player_id])
    else:
        st.info("왼쪽에서 팀과 선수를 먼저 고르세요. 또는 '선수 찾기'에서 조건으로 찾아 보세요.")
elif view == "팀 가이드":
    render_team_guide(teams)
else:
    render_player_search()