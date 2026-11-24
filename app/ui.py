import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
import pandas as pd

from app import analytics
from app.assistant import answer
from app.config import DB

LABELS = {
    "display_name": "Oyuncu", "nfl_position": "Pozisyon", "season": "Sezon",
    "season_type": "Sezon türü", "team_abbr": "Takım",
    "games": "Kayıtlı maç", "player_play_rows": "Kayıtlı oyun",
    "sacks": "Sack", "sacks_per_observed_game": "Maç başına sack",
    "pressure_allowed_rate": "Baskı verme oranı (0–1)",
    "pressure_labeled_plays": "Baskı etiketi bulunan oyun",
    "sack_labeled_plays": "Sack etiketi bulunan oyun",
    "receiving_yards": "Pas yakalamayla kazanılan yard",
    "rushing_yards": "Koşuyla kazanılan yard",
}
SEASON_TYPES = {"REG": "Normal sezon", "POST": "Play-off", "PRE": "Sezon öncesi"}


def show_performance(payload):
    rows = payload.get("data", [])
    if not rows:
        st.info("Bu seçim için kayıt bulunamadı.")
        return
    frame = pd.DataFrame(rows).drop(columns=["nfl_id"], errors="ignore")
    frame["season_type"] = frame["season_type"].replace(SEASON_TYPES)
    st.dataframe(frame.rename(columns=LABELS).round(2), hide_index=True)
    st.caption("Kayıtlı maç: oyuncunun yer aldığı benzersiz maç. Kayıtlı oyun: maçların içindeki oyuncu–oyun kayıtları. Boş alan, sıfır değil eksik bilgidir.")


def show_evidence(evidence):
    if not evidence:
        return
    with st.expander("Cevabın dayandığı veriler"):
        for item in evidence:
            if item.get("tool") == "player_performance":
                show_performance(item["result"])
        st.caption("Aşağıdaki araç çıktıları hesaplanan verilerdir; sohbet metni modelin yorumudur.")
        st.json(evidence)


st.set_page_config(page_title="NFL Veri Asistanı", page_icon="🏈", layout="wide")
st.title("🏈 NFL Veri Asistanı")
st.caption("Yalnızca yerel dataset • Gözlenen veriler ve kaynaklı analiz • MVP 0.1")
if not DB.exists():
    st.info("Önce terminalde `python -m pipelines.ingest` çalıştırın.")
    st.stop()

players, chat, coverage = st.tabs(["Oyuncu analizi", "Sohbet", "Veri kapsamı"])
with coverage:
    summary = analytics.dataset_summary()
    st.warning(analytics.COVERAGE_NOTE)
    st.dataframe(summary["data"]["seasons"], hide_index=True)
    st.dataframe(summary["data"]["coverage"], hide_index=True)
with players:
    st.subheader("Oyuncu bul ve karşılaştır")
    st.caption("İsim veya takımla ara, ardından tablonun solundaki kutudan oyuncu seç.")
    directory = analytics.player_directory()["data"]
    lookup = {
        p["nfl_id"]: f'{p["display_name"]} — {p["teams"]} — {p["nfl_position"]} — Draft: {p["draft_year"]}'
        for p in directory
    }
    search_col, position_col = st.columns([3, 1])
    with search_col:
        search = st.text_input("Oyuncu veya takım ara", placeholder="Örnek: Alan Ali veya MIN")
    with position_col:
        position = st.selectbox("Pozisyon", ["Tümü"] + sorted({
            p["nfl_position"] for p in directory if p["nfl_position"]
        }))
    matches = [
        p for p in directory
        if (not search.strip() or search.strip().casefold() in lookup[p["nfl_id"]].casefold())
        and (position == "Tümü" or p["nfl_position"] == position)
    ]
    selected = []
    if matches:
        st.caption(f"{len(matches)} oyuncu · Karşılaştırmak için en fazla 10 oyuncu seç")
        selection = st.dataframe(
            pd.DataFrame(matches)[["display_name", "teams", "nfl_position", "draft_year"]].rename(columns={
                "display_name": "Oyuncu", "teams": "Kayıtlı takımlar",
                "nfl_position": "Pozisyon", "draft_year": "Draft yılı",
            }),
            hide_index=True, width="stretch",
            height=min(390, 36 * (len(matches) + 1) + 4),
            column_config={"Draft yılı": st.column_config.NumberColumn(format="%d")},
            on_select="rerun", selection_mode="multi-row",
            key=f"player_table:{search.strip().casefold()}:{position}",
        )
        selected = [matches[i]["nfl_id"] for i in selection.selection.rows]
        st.caption("Takımlar verideki geçmiş kayıtlardır; güncel kadro bilgisi değildir.")
    else:
        st.info("Oyuncu bulunamadı. Başka bir isim veya takım dene ya da pozisyon filtresini değiştir.")
    if len(selected) > 10:
        st.info("Karşılaştırma için en fazla 10 oyuncu seçebilirsin. Lütfen bazı seçimleri kaldır.")
    elif selected:
        st.divider()
        st.subheader("Sezon performansı")
        st.write("**Seçilenler:** " + ", ".join(
            p["display_name"] for p in matches if p["nfl_id"] in selected
        ))
        season_type = st.selectbox("Gösterilecek maçlar", list(SEASON_TYPES), format_func=SEASON_TYPES.get)
        show_performance(analytics.player_performance(selected, season_type=season_type))
        for player_id in selected:
            with st.expander("Detaylı oyuncu kaydı · " + lookup[player_id]):
                st.json(analytics.player_profile(player_id))
    elif matches:
        st.info("Bir oyuncu seçtiğinde sezon istatistikleri burada açılacak.")
with chat:
    st.caption("Sohbet, yapılandırılmış bir LLM bağlantısı gerektirir. Oyuncu analizi ve veri kapsamı anahtarsız kullanılabilir.")
    if st.button("Konuşmayı temizle"):
        st.session_state.messages = []
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            show_evidence(message.get("evidence"))
    if st.session_state.messages:
        transcript = "\n\n".join(
            f"## {'Kullanıcı' if m['role'] == 'user' else 'Asistan'}\n\n{m['content']}"
            for m in st.session_state.messages
        )
        st.download_button("Konuşmayı indir", transcript, file_name="nfl_analiz.md", mime="text/markdown")
    question = st.chat_input("Dataset hakkında bir soru sorun")
    if question:
        history = st.session_state.messages[-12:]
        with st.chat_message("user"):
            st.markdown(question)
        try:
            with st.spinner("Veriler inceleniyor..."):
                response = answer(question, history)
            st.session_state.messages.extend([{"role": "user", "content": question},
                                              {"role": "assistant", "content": response["answer"],
                                               "evidence": response["evidence"]}])
            with st.chat_message("assistant"):
                st.markdown(response["answer"])
                show_evidence(response["evidence"])
        except Exception as exc:
            st.error(f"İşlem tamamlanamadı: {exc}")
