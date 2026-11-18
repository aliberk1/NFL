import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from app import analytics
from app.assistant import answer
from app.config import DB

st.set_page_config(page_title="NFL Veri Asistanı", page_icon="🏈", layout="wide")
st.title("🏈 NFL Veri Asistanı")
st.caption("Yalnızca yerel dataset • Gözlenen veriler ve kaynaklı analiz • MVP 0.1")
if not DB.exists():
    st.info("Önce terminalde `python -m pipelines.ingest` çalıştırın.")
    st.stop()

chat, players, coverage = st.tabs(["Sohbet", "Oyuncu analizi", "Veri kapsamı"])
with coverage:
    summary = analytics.dataset_summary()
    st.warning(analytics.COVERAGE_NOTE)
    st.dataframe(summary["data"]["seasons"], hide_index=True)
    st.dataframe(summary["data"]["coverage"], hide_index=True)
with players:
    name = st.text_input("Oyuncu adında ara", placeholder="Will")
    if name:
        matches = analytics.search_players(name)["data"]
        lookup = {p["nfl_id"]: f'{p["display_name"]} — {p["nfl_position"]} ({p["draft_year"]})' for p in matches}
        selected = st.multiselect("En fazla 10 oyuncu seç", list(lookup), format_func=lookup.get, max_selections=10)
        if selected:
            st.dataframe(analytics.player_performance(selected)["data"], hide_index=True)
            for player_id in selected:
                with st.expander(lookup[player_id]):
                    st.json(analytics.player_profile(player_id))
with chat:
    st.caption("Sohbet, yapılandırılmış bir LLM bağlantısı gerektirir. Oyuncu analizi ve veri kapsamı anahtarsız kullanılabilir.")
    if st.button("Konuşmayı temizle"):
        st.session_state.messages = []
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    question = st.chat_input("Dataset hakkında bir soru sorun")
    if question:
        history = st.session_state.messages[-12:]
        with st.chat_message("user"):
            st.markdown(question)
        try:
            with st.spinner("Veriler inceleniyor..."):
                response = answer(question, history)
            st.session_state.messages.extend([{"role": "user", "content": question},
                                              {"role": "assistant", "content": response["answer"]}])
            with st.chat_message("assistant"):
                st.markdown(response["answer"])
                with st.expander("Veri kanıtları"):
                    st.json(response["evidence"])
        except Exception as exc:
            st.error(f"İşlem tamamlanamadı: {exc}")
