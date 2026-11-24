import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

from app import analytics
from app.assistant import answer
from app.config import DB
from app.observability import configure_logging

configure_logging()
logger = logging.getLogger("nfl.ui")

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
COMBINE_LABELS = {
    "combine_position": "Combine pozisyonu",
    "combine_height": "Boy (inç)",
    "combine_weight": "Ağırlık (lb)",
    "hand_size": "El ölçüsü (inç)",
    "arm_length": "Kol uzunluğu (inç)",
    "wing_span": "Kanat açıklığı (inç)",
    "ten_yd_split": "10-yard split (sn)",
    "forty": "40-yard koşusu (sn)",
    "vertical": "Dikey sıçrama (inç)",
    "broad_jump": "Uzun atlama (inç)",
    "three_cone": "Üç koni drili (sn)",
    "short_shuttle": "Kısa shuttle (sn)",
    "bench_reps": "Bench tekrar sayısı",
    "ngs_athleticism_score": "NGS atletizm puanı",
    "ngs_college_production_score": "NGS kolej üretim puanı",
    "ngs_final_score": "NGS genel puanı",
}

OL_LIMITATION_LABELS = {
    "One mirror attempt per player; boundary robustness is not repeatability.": "Oyuncu başına tek mirror denemesi vardır; sınır duyarlılığı, tekrar ölçüm güvenilirliği değildir.",
    "Small cohorts and multiple research questions across the project.": "Örneklemler küçüktür ve projede birden fazla araştırma sorusu incelenmiştir.",
    "Pressure labels and dropback duration are supplied game outcomes; context adjustment is not causal.": "Baskı etiketleri ve dropback süresi maç verisinden gelir; bağlam düzeltmesi nedensellik göstermez.",
    "Conditional bootstrap excludes training uncertainty.": "Koşullu bootstrap eğitim belirsizliğini kapsamaz.",
    "Mirror phase includes the transition into exit until the geometric threshold is crossed.": "Geometrik eşik geçilene kadarki çıkışa geçiş, mirror fazına dahildir.",
    "The drill is coach-directed; faster movement can reflect different instructions.": "Dril koç yönlendirmelidir; daha hızlı hareket farklı talimatları yansıtabilir.",
}
WR_LIMITATION_LABELS = {
    "Route speed is not overall football success or receiver separation.": "Rota hızı genel futbol başarısı veya receiver separation ölçüsü değildir.",
    "All analyses exploratory; earlier outcomes from these years were inspected.": "Analizler keşifseldir; bu yılların sonuçları daha önce incelenmiştir.",
    "Bootstrap is conditional on fitted folds and ignores training uncertainty.": "Bootstrap eğitilmiş fold'lara koşulludur ve eğitim belirsizliğini kapsamaz.",
    "Only participating Combine players and observed rookie pass routes are included.": "Yalnız Combine'a katılan oyuncular ve gözlenen çaylak pas rotaları dahildir.",
    "Pre-throw window restriction selects longer-developing pass plays.": "Pas öncesi pencere kısıtı, daha uzun gelişen pas oyunlarını seçer.",
    "Additive context model does not remove all team, route depth, or tactical effects.": "Toplamsal bağlam modeli takım, rota derinliği ve taktik etkilerin tümünü gidermez.",
    "Official speed units are not yet verified.": "Resmî hız birimleri henüz doğrulanmamıştır.",
}


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


def show_combine_measurements(profile, player_label):
    rows = profile.get("data", {}).get("combine", [])
    with st.expander("Combine ölçümleri · " + player_label):
        if not rows:
            st.info("Bu oyuncu için Combine ölçümü bulunamadı.")
            return
        st.caption("— eksik ölçümdür; sıfır değerinden farklıdır.")
        for row in rows:
            draft_year = row.get("draft_year")
            st.markdown(f"**Draft sınıfı: {draft_year if draft_year is not None else 'Bilinmiyor'}**")
            measurements = [
                (key, value) for key, value in row.items()
                if key not in {"nfl_id", "draft_year"}
            ]
            columns = st.columns(3)
            for index, (key, value) in enumerate(measurements):
                if isinstance(value, float):
                    display_value = f"{value:,.3f}".rstrip("0").rstrip(".")
                elif value is None:
                    display_value = "—"
                else:
                    display_value = str(value)
                with columns[index % 3]:
                    st.metric(COMBINE_LABELS.get(key, key.replace("_", " ").title()), display_value)


def show_limitations(items, translations):
    with st.expander("Kapsam ve araştırma sınırları", expanded=True):
        for item in items:
            st.markdown(f"- {translations.get(item, item)}")


def show_research_source(digests):
    labels = " · ".join(f"{name}: {digest[:12]}" for name, digest in digests.items())
    st.caption(f"Kaynak: manifest ile doğrulanmış yerel araştırma çıktıları · SHA-256 {labels}")


def show_ol_research(study):
    summary = study["summary"]
    measurements = study["measurements"]
    mirror_drill = next(
        drill for drill in measurements["ol_drill_suite"]
        if drill["drill"] == "Pass-Pro Mirror Drill"
    )
    st.subheader("Hücum hattı · Pass-Pro Mirror faz ayrıştırması")
    st.markdown(
        "Mirror drilindeki yanal ayna hareketi ile sondaki düz çıkış sprinti "
        "ayrı ölçülür. İnceleyici oyuncuya göre saha izini ve zaman içindeki "
        "toplam/yanal hızı gösterir; turuncu alan çıkış fazını belirtir."
    )
    metric_columns = st.columns(3)
    metric_columns[0].metric("Kabul edilen mirror oyuncusu", f'{mirror_drill["accepted_players"]}')
    metric_columns[1].metric("Zirve hız çıkış fazında", f'{mirror_drill["peak_in_exit_fraction"]:.0%}')
    metric_columns[2].metric(
        "Yanal / tüm hız sıralaması",
        f'ρ = {mirror_drill["phase_vs_whole_spearman"]:+.3f}',
    )
    st.caption(
        "Bu örneklemde zirve hız çıkış sprintinde oluştu; yanal faz ölçümü "
        "tüm dril hız sıralamasını temsil etmiyor. Bu, oyuncu yeteneği sıralaması değildir."
    )

    primary_scores = [
        score for score in summary["scores"]
        if score["variant"] == "primary_with_duration" and score["test_year"] == 2025
    ]
    classic = next(score for score in primary_scores if score["model"] == "classic")
    phase = next(score for score in primary_scores if score["model"] == "mirror_phase")
    score_columns = st.columns(2)
    score_columns[0].metric("2025 klasik ölçümler MAE", f'{classic["mae_pp"]:.3f} pp')
    score_columns[1].metric("2025 mirror fazı MAE", f'{phase["mae_pp"]:.3f} pp')
    st.caption(
        f"Faz modelinin klasik modele göre hata azalması {phase['improvement_over_classic_pp']:+.3f} pp; "
        f"koşullu %95 aralık [{phase['ci_low']:+.3f}, {phase['ci_high']:+.3f}] pp. "
        "Aralık sıfırı kapsadığı için ek tahmin üstünlüğü kanıtlanmış değildir."
    )
    st.image(study["model_chart"], caption="İleri yıl pas koruma model karşılaştırması", use_container_width=True)
    show_research_source(study["digests"])

    st.markdown("#### Aynı pozisyon ve draft sınıfında oyuncu karşılaştırması")
    cohort = pd.DataFrame(study["cohort"])
    cohort["draft_year"] = pd.to_numeric(cohort["draft_year"])
    position_col, year_col = st.columns(2)
    positions = sorted(cohort["nfl_position"].dropna().unique())
    draft_years = sorted(cohort["draft_year"].dropna().astype(int).unique())
    with position_col:
        selected_position = st.selectbox("OL pozisyonu", positions, key="research_ol_position")
    with year_col:
        selected_year = st.selectbox("Draft sınıfı", draft_years, key="research_ol_draft_year")
    cohort = cohort[
        (cohort["nfl_position"] == selected_position)
        & (cohort["draft_year"] == selected_year)
    ]
    st.caption(f"{len(cohort)} oyuncu · aynı pozisyon ve draft sınıfı")
    st.dataframe(
        cohort[[
            "display_name", "nfl_position", "draft_year", "lateral_speed_p75",
            "whole_drill_speed", "lateral_speed_p75_percentile",
            "whole_drill_speed_percentile", "rank_difference_pp",
        ]].rename(columns={
            "display_name": "Oyuncu",
            "nfl_position": "Pozisyon",
            "draft_year": "Draft yılı",
            "lateral_speed_p75": "Yanal hız p75 (yd/s)",
            "whole_drill_speed": "Tüm dril hızı (yd/s)",
            "lateral_speed_p75_percentile": "Yanal hız yüzdeliği",
            "whole_drill_speed_percentile": "Tüm dril yüzdeliği",
            "rank_difference_pp": "Yüzdelik farkı (puan)",
        }).round(2),
        hide_index=True,
        width="stretch",
    )
    with st.expander("Etkileşimli faz ve zaman-hız inceleyicisi", expanded=False):
        components.html(study["explorer_html"], height=1300, scrolling=True)
    show_limitations(summary["limitations"], OL_LIMITATION_LABELS)


def show_wr_research(study):
    summary = study["summary"]
    st.subheader("Wide receiver · Combine hızının maç rotalarına aktarımı")
    st.markdown(
        "Bu çalışma Combine hız ölçümleri ile çaylak sezonundaki rota hızını "
        "karşılaştırır. Rota hızı genel oyuncu başarısı veya receiver separation değildir."
    )
    metric_columns = st.columns(3)
    metric_columns[0].metric("WR oyuncusu", f'{summary["primary_players"]}')
    metric_columns[1].metric("Gözlenen rota oyunu", f'{summary["primary_plays"]:,}')
    metric_columns[2].metric("Combine / maç hızı korelasyonu", f'{summary["raw_peak_game_correlation"]:+.3f}')
    st.caption(
        "Korelasyon betimseldir. Tracking hızlarının resmî birimi doğrulanmadığı için "
        "bu değerler birim adı olmadan karşılaştırılır."
    )

    rows = []
    for score in summary["scores"]:
        rows.append({
            "Test draft sınıfı": score["test_year"],
            "Eğitim / test oyuncusu": f'{score["train_players"]} / {score["test_players"]}',
            "Klasik MAE": score["traditional_mae"],
            "Klasik + hareket MAE": score["with_tracking_mae"],
            "MAE azalması": score["movement_mae_improvement"],
            "%95 aralık alt": score["ci_low"],
            "%95 aralık üst": score["ci_high"],
        })
    st.markdown("#### İleri draft sınıfında model karşılaştırması")
    st.dataframe(pd.DataFrame(rows).round(4), hide_index=True, width="stretch")
    st.caption(
        "2024 testinde MAE azalmış, 2025 testinde azalmamıştır; iki aralık da sıfırı kapsar. "
        "Tutarlı ek tahmin katkısı gösterilmemiştir."
    )
    st.image(study["model_chart"], caption="WR hız aktarımı: ileri yıl model sonuçları", use_container_width=True)
    show_research_source(study["digests"])

    st.markdown("#### Aynı WR draft sınıfında Combine ve rota ölçümleri")
    cohort = pd.DataFrame(study["cohort"])
    cohort["draft_year"] = pd.to_numeric(cohort["draft_year"])
    draft_years = sorted(cohort["draft_year"].dropna().astype(int).unique())
    selected_year = st.selectbox("WR draft sınıfı", draft_years, key="research_wr_draft_year")
    cohort = cohort[(cohort["nfl_position"] == "WR") & (cohort["draft_year"] == selected_year)]
    st.caption(f"{len(cohort)} oyuncu · WR pozisyonu, {selected_year} draft sınıfı")
    st.dataframe(
        cohort[[
            "display_name", "draft_year", "forty", "combine_peak_speed",
            "combine_early_speed", "game_peak_speed", "valid_game_plays",
        ]].rename(columns={
            "display_name": "Oyuncu",
            "draft_year": "Draft yılı",
            "forty": "40-yard süresi",
            "combine_peak_speed": "Combine zirve hızı",
            "combine_early_speed": "Combine erken hız",
            "game_peak_speed": "Maç rota zirve hızı",
            "valid_game_plays": "Geçerli rota oyunu",
        }).round(3),
        hide_index=True,
        width="stretch",
    )
    show_limitations(summary["limitations"], WR_LIMITATION_LABELS)


st.set_page_config(page_title="NFL Veri Asistanı", page_icon="🏈", layout="wide")
st.title("🏈 NFL Veri Asistanı")
st.caption("Yalnızca yerel dataset • Gözlenen veriler ve kaynaklı analiz • MVP 0.1")
if DB.exists():
    players, research, chat, coverage = st.tabs(["Oyuncu analizi", "Araştırma", "Sohbet", "Veri kapsamı"])
else:
    st.info("Oyuncu analizi ve veri kapsamı için önce `python -m pipelines.ingest` çalıştırın. Araştırma sonuçları manifestlerden görüntülenebilir.")
    research, = st.tabs(["Araştırma"])
with research:
    studies = analytics.research_snapshot()
    ol_research, wr_research = st.tabs(["OL faz ayrıştırması", "WR hız aktarımı"])
    with ol_research:
        show_ol_research(studies["ol"])
    with wr_research:
        show_wr_research(studies["wr"])
if DB.exists():
    with coverage:
        summary = analytics.dataset_summary()
        st.warning(analytics.COVERAGE_NOTE)
        st.dataframe(summary["data"]["seasons"], hide_index=True)
        st.dataframe(summary["data"]["coverage"], hide_index=True)
    with players:
        st.subheader("Oyuncu bul ve karşılaştır")
        st.caption("İsim veya takım ara; ardından listeden en fazla 10 oyuncu seç.")
        options = analytics.player_filter_options()["data"]
        search_col, position_col, draft_col = st.columns([3, 1, 1])
        with search_col:
            search = st.text_input("Oyuncu veya takım ara", placeholder="Örnek: Alan Ali veya MIN")
        with position_col:
            position = st.selectbox("Pozisyon", ["Tümü"] + [row["nfl_position"] for row in options["positions"]])
        with draft_col:
            draft_years = [str(row["draft_year"]) for row in options["draft_years"]]
            draft_class = st.selectbox("Draft sınıfı", ["Tümü"] + draft_years)
        draft_year = int(draft_class) if draft_class != "Tümü" else None
        page_size = 100
        filters = (search, None if position == "Tümü" else position, draft_year)
        total = analytics.player_directory(*filters, limit=page_size, offset=0)["data"]["total"]
        page_count = max(1, (total + page_size - 1) // page_size)
        page = st.number_input("Sayfa", min_value=1, max_value=page_count, value=1, step=1)
        directory = analytics.player_directory(*filters, limit=page_size, offset=(page - 1) * page_size)["data"]
        matches = directory["rows"]
        lookup = {p["nfl_id"]: f'{p["display_name"]} — {p["teams"]} — {p["nfl_position"]} — Draft: {p["draft_year"]}' for p in matches}
        selected = []
        if matches:
            st.caption(f"{directory['total']} oyuncu · Sayfa {page}/{page_count} · Bu sayfadan en fazla 10 oyuncu seç")
            st.dataframe(
                pd.DataFrame(matches)[["display_name", "teams", "nfl_position", "draft_year"]].rename(columns={
                    "display_name": "Oyuncu", "teams": "Kayıtlı takımlar",
                    "nfl_position": "Pozisyon", "draft_year": "Draft yılı",
                }),
                hide_index=True, width="stretch",
                height=min(390, 36 * (len(matches) + 1) + 4),
                column_config={"Draft yılı": st.column_config.NumberColumn(format="%d")},
                key=f"player_table:{search.strip().casefold()}:{position}:{draft_class}:{page}",
            )
            player_options = {
                f'{player["display_name"]} · {player["nfl_position"]} · {player["draft_year"]} · #{player["nfl_id"]}': player["nfl_id"]
                for player in matches
            }
            selected_labels = st.multiselect(
                "Karşılaştırılacak oyuncular", list(player_options), max_selections=10,
                key=f"player_selection:{search.strip().casefold()}:{position}:{draft_class}:{page}",
            )
            selected = [player_options[label] for label in selected_labels]
            selected_players = [p for p in matches if p["nfl_id"] in selected]
            st.caption("Takımlar verideki geçmiş kayıtlardır; güncel kadro bilgisi değildir.")
        else:
            st.info("Oyuncu bulunamadı. Başka bir isim veya takım dene ya da pozisyon filtresini değiştir.")
        if len(selected) > 10:
            st.info("Karşılaştırma için en fazla 10 oyuncu seçebilirsin. Lütfen bazı seçimleri kaldır.")
        elif len(selected) > 1 and not analytics.same_comparison_context(selected_players):
            st.warning("Adil karşılaştırma için oyuncular aynı pozisyon ve draft sınıfında olmalı. İki filtreyi de seç.")
        elif selected:
            st.divider()
            st.subheader("Sezon performansı")
            st.write("**Seçilenler:** " + ", ".join(
                p["display_name"] for p in matches if p["nfl_id"] in selected
            ))
            season_type = st.selectbox("Gösterilecek maçlar", list(SEASON_TYPES), format_func=SEASON_TYPES.get)
            show_performance(analytics.player_performance(selected, season_type=season_type))
            for player_id in selected:
                profile = analytics.player_profile(player_id)
                show_combine_measurements(profile, lookup[player_id])
                with st.expander("Teknik profil ve kariyer kaydı · " + lookup[player_id]):
                    st.json({
                        "player": profile["data"]["player"],
                        "career_snapshot": profile["data"]["career_snapshot"],
                    })
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
        st.caption("Örnek sorular")
        example_columns = st.columns(3)
        examples = [
            ("Veri kapsamı", "Dataset hangi sezonları ve maç türlerini içeriyor?"),
            ("Oyuncu karşılaştır", "<Oyuncu A> ve <Oyuncu B>'yi aynı sezon ve maç türünde karşılaştır."),
            ("Kanıt sınırı", "Üçüncü hakta 3–6 yard mesafede hangi rota daha çok first down kazandırıyor?"),
        ]
        for column, (label, prompt) in zip(example_columns, examples):
            if column.button(label, key=f"chat_example_{label}"):
                st.session_state.pending_chat_example = prompt
        question = st.chat_input("Dataset hakkında bir soru sorun")
        if st.session_state.get("pending_chat_example"):
            question = st.session_state.pop("pending_chat_example")
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
                logger.error("chat_ui_failed", extra={"event": "chat_ui_failed", "error_type": type(exc).__name__})
                st.error("Sohbet tamamlanamadı. Bağlantı ayarlarını kontrol edip tekrar deneyin.")
