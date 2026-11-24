import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
import pandas as pd

from app import analytics
from app.assistant import answer
from app.config import DB
from app.player_view import (
    CAREER_FIELDS, COMBINE_FIELDS, PLAYER_FIELDS, POSITION_NAMES, ROLE_METRICS,
    TEAM_NAMES, comparison_groups, formatted_fields, position_label, team_label,
)

LABELS = {
    "display_name": "Oyuncu", "nfl_position": "Pozisyon", "season": "Sezon",
    "season_type": "Sezon türü", "team_abbr": "Takım",
    "games": "Kayıtlı maç", "player_play_rows": "Kayıtlı oyun",
    "sacks": "Sack", "sacks_per_observed_game": "Maç başına sack",
    "tackles": "Tackle", "tackle_labeled_plays": "Tackle etiketi bulunan oyun",
    "pressure_allowed_rate": "Baskı verme oranı (0–1)",
    "pressure_labeled_plays": "Baskı etiketi bulunan oyun",
    "receiving_labeled_plays": "Pas yardı etiketi bulunan oyun",
    "rushing_labeled_plays": "Koşu yardı etiketi bulunan oyun",
    "sack_labeled_plays": "Sack etiketi bulunan oyun",
    "receiving_yards": "Pas yakalamayla kazanılan yard",
    "rushing_yards": "Koşuyla kazanılan yard",
}
SEASON_TYPES = {"REG": "Normal sezon", "POST": "Play-off", "PRE": "Sezon öncesi"}


def show_performance(payload, rows=None):
    rows = payload.get("data", []) if rows is None else rows
    if not rows:
        st.info("Bu seçim için kayıt bulunamadı.")
        return
    frame = pd.DataFrame(rows).drop(columns=["nfl_id"], errors="ignore")
    frame["season_type"] = frame["season_type"].replace(SEASON_TYPES)
    frame["team_abbr"] = frame["team_abbr"].map(team_label)
    display = frame.rename(columns=LABELS).round(2).fillna("Bilgi yok").astype(str)
    st.dataframe(display, hide_index=True, width="stretch")
    st.caption("Kayıtlı maç: oyuncunun yer aldığı benzersiz maç. Kayıtlı oyun: maçların içindeki oyuncu–oyun kayıtları. Boş alan, sıfır değil eksik bilgidir.")


def show_profile(player_id, directory_entry, expanded=False):
    profile = analytics.player_profile(player_id)
    player = next(iter(profile["data"]["player"]), None)
    if not player:
        st.info("Bu oyuncu için profil kaydı bulunamadı.")
        return
    teams = [team_label(team.strip()) for team in directory_entry["teams"].split(",")
             if team.strip() and team.strip() != "Takım kaydı yok"]
    with st.expander(f"{player['display_name']} · {position_label(player['nfl_position'])}",
                     expanded=expanded):
        st.caption("Kayıtlı takımlar: " + (", ".join(teams) if teams else "Bilgi yok") +
                   " · Bu liste güncel kadroyu göstermez.")
        profile_tab, combine_tab, career_tab = st.tabs(["Profil", "Combine", "Kariyer"])
        with profile_tab:
            st.table(pd.DataFrame(formatted_fields(player, PLAYER_FIELDS)))
        with combine_tab:
            combine = profile["data"]["combine"]
            if combine:
                for record in combine:
                    st.caption(f"Draft yılı: {record.get('draft_year') or 'Bilgi yok'}")
                    st.table(pd.DataFrame(formatted_fields(record, COMBINE_FIELDS)))
            else:
                st.info("Bu oyuncu için Combine kaydı yok.")
        with career_tab:
            career = profile["data"]["career_snapshot"]
            if career:
                st.caption("Kariyer toplamları zaman damgası olmayan anlık görüntüdür.")
                st.table(pd.DataFrame(formatted_fields(career[0], CAREER_FIELDS)))
            else:
                st.info("Bu oyuncu için kariyer özeti yok.")
        with st.expander("Teknik kayıtlar"):
            st.json(profile)


def show_comparisons(rows):
    groups = comparison_groups(rows)
    for role, players in groups.items():
        metric, title, unit = ROLE_METRICS[role]
        st.subheader(role)
        st.caption(f"{title} ({unit}) · Aynı sezon, maç türü ve takım filtresi içinde")
        if metric == "pressure_allowed_rate":
            st.caption("Daha düşük oran daha az baskı izni anlamına gelir.")
        measured = [p for p in players if p["Değer"] is not None]
        if measured:
            chart = pd.DataFrame({"Oyuncu": [p["Oyuncu"] for p in measured],
                                  title: [p["Değer"] for p in measured]}).set_index("Oyuncu")
            st.bar_chart(chart, horizontal=True, x_label="Oyuncu",
                         y_label=f"{title} ({unit})",
                         height=min(560, max(240, 72 * len(measured) + 80)))
        else:
            st.info("Bu pozisyon grubu için seçilen bağlamda ölçülebilir metrik yok.")
        table = pd.DataFrame([{
            "Oyuncu": p["Oyuncu"], "Pozisyon": p["Pozisyon"],
            title: f"{p['Değer']:.2f} {unit}" if p["Değer"] is not None else "Bilgi yok",
            "Gözlenen maç": p["Gözlenen maç"],
            "Ölçüm kapsamı": (
                "Bilgi yok" if p["Etiketli kayıt"] is None
                else f"{p['Etiketli kayıt']} gözlenen maç" if metric == "games"
                else f"{p['Etiketli kayıt']} etiketli oyun"
            ),
            "Veri uyarısı": "Az gözlem" if p["Az veri"] else "",
        } for p in players])
        st.dataframe(table, hide_index=True, width="stretch")
        if any(p["Az veri"] for p in players):
            st.warning("Ölçüm kapsamı bilinmiyorsa veya gözlem azsa oranlar ve toplamlar güçlü performans kanıtı sayılmamalı.")


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
    provenance = summary.get("provenance")
    if provenance:
        st.caption(
            f"Kaynak: {provenance['source']} · Yükleme (UTC): {provenance['loaded_at_utc']} "
            f"· Veri sürümü (SHA-256): {provenance['data_version'][:12]}"
        )
        st.caption("Veri kalite raporu: data/curated/quality_report.json")
    st.dataframe(summary["data"]["seasons"], hide_index=True)
    st.dataframe(summary["data"]["coverage"], hide_index=True)
with players:
    st.subheader("Oyuncu bul ve karşılaştır")
    st.caption("Oyuncu ara, listeye ekle ve aynı sezon ile maç türündeki kayıtları karşılaştır.")
    with st.spinner("Oyuncu kayıtları yükleniyor..."):
        directory = analytics.player_directory()["data"]
    by_id = {p["nfl_id"]: p for p in directory}
    seasons = sorted({r["season"] for r in analytics.dataset_summary()["data"]["seasons"]}, reverse=True)
    teams = sorted({team.strip() for p in directory for team in p["teams"].split(",")
                    if team.strip() and team.strip() != "Takım kaydı yok"})
    filter_cols = st.columns([2, 1, 1, 1])
    with filter_cols[0]:
        search = st.text_input("Oyuncu veya takım ara", placeholder="İsim, takım kodu veya adı")
    with filter_cols[1]:
        position = st.selectbox("Pozisyon", ["Tümü"] + sorted({
            p["nfl_position"] for p in directory if p["nfl_position"]
        }), format_func=lambda value: "Tümü" if value == "Tümü" else position_label(value))
    with filter_cols[2]:
        team = st.selectbox("Takım", ["Tümü"] + teams,
                            format_func=lambda value: "Tümü" if value == "Tümü" else team_label(value))
    with filter_cols[3]:
        season = st.selectbox("Sezon", seasons, index=0) if seasons else None
    search_term = search.strip().casefold()
    matches = [
        p for p in directory
        if (not search_term or search_term in (
            f"{p['display_name']} {p['teams']} " +
            " ".join(TEAM_NAMES.get(code.strip(), "") for code in p["teams"].split(","))
        ).casefold())
        and (position == "Tümü" or p["nfl_position"] == position)
        and (team == "Tümü" or team in {code.strip() for code in p["teams"].split(",")})
    ]
    if matches:
        st.caption(f"{len(matches)} sonuç · İlk 20 oyuncu gösteriliyor")
        preview = pd.DataFrame([{
            "Oyuncu": p["display_name"],
            "Pozisyon": position_label(p["nfl_position"]),
            "Kayıtlı takımlar": ", ".join(team_label(t.strip()) for t in p["teams"].split(",")
                                        if t.strip() != "Takım kaydı yok") or "Bilgi yok",
            "Draft yılı": p["draft_year"] if p["draft_year"] is not None else "Bilgi yok",
        } for p in matches[:20]])
        st.dataframe(preview, hide_index=True, width="stretch")
        add_col, button_col = st.columns([3, 1])
        with add_col:
            candidate = st.selectbox(
                "Sonuçlardan ekle", [p["nfl_id"] for p in matches],
                format_func=lambda player_id: f"{by_id[player_id]['display_name']} · "
                                              f"{position_label(by_id[player_id]['nfl_position'])}",
                key="candidate_player",
            )
        with button_col:
            st.write("")
            if st.button("Listeye ekle", disabled=len(st.session_state.get("selected_player_ids", [])) >= 10):
                selected_now = st.session_state.get("selected_player_ids", [])
                if candidate not in selected_now:
                    st.session_state.selected_player_ids = selected_now + [candidate]
                    st.rerun()
    else:
        st.info("Bu arama ve filtrelerle oyuncu bulunamadı. İsim, takım veya pozisyon filtresini değiştir.")
    selected = st.multiselect(
        "Seçilen oyuncular (en fazla 10)",
        options=list(by_id),
        format_func=lambda player_id: f"{by_id[player_id]['display_name']} · "
                                      f"{position_label(by_id[player_id]['nfl_position'])}",
        key="selected_player_ids", max_selections=10,
    )
    st.caption("Takımlar verideki geçmiş kayıtlardır; güncel kadro bilgisi değildir. Seçim arama değişince korunur.")
    if selected:
        active = [player_id for player_id in selected
                  if position == "Tümü" or by_id[player_id]["nfl_position"] == position]
        if len(active) < len(selected):
            st.info("Pozisyon filtresiyle eşleşmeyen seçili oyuncular listede korunur; aşağıdaki sonuçlara katılmaz.")
        if not active:
            st.info("Bu pozisyonda seçili oyuncu yok.")
        else:
            season_type = st.selectbox("Maç türü", list(SEASON_TYPES), format_func=SEASON_TYPES.get)
            with st.spinner("Sezon verileri hazırlanıyor..."):
                payload = analytics.player_performance(active, season=season, season_type=season_type)
            rows = [row for row in payload["data"] if team == "Tümü" or row["team_abbr"] == team]
            st.caption(f"Bağlam: {season} · {SEASON_TYPES[season_type]} · "
                       f"{'Tüm takımlar' if team == 'Tümü' else team_label(team)}")
            if rows:
                show_comparisons(rows)
                with st.expander("Sezon kayıtları ve metrik açıklamaları"):
                    show_performance(payload, rows)
                    for label in ("games", "pressure_allowed_rate", "receiving_yards",
                                  "rushing_yards", "sacks", "tackles"):
                        st.caption(payload["metric_definitions"][label])
            else:
                st.info("Seçilen sezon, maç türü ve takım için kayıt bulunamadı. Filtreleri değiştir.")
        st.divider()
        st.subheader("Oyuncu profilleri")
        for player_id in selected:
            show_profile(player_id, by_id[player_id], expanded=len(selected) == 1)
    else:
        st.info("Karşılaştırmaya başlamak için arama sonucundan bir oyuncu ekle.")
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
