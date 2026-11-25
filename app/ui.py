import sys
import logging
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

from app import analytics
from app.assistant import answer, provider_configured
from app.config import DB
from app.limits import LimitExceeded
from app.observability import configure_logging
from app.player_view import (
    CAREER_FIELDS, COMBINE_FIELDS, PLAYER_FIELDS, ROLE_METRICS,
    comparison_groups, formatted_fields, position_label, team_label,
)

configure_logging()
logger = logging.getLogger("nfl.ui")

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
        profile_tab, combine_tab, career_tab, technical_tab = st.tabs(["Profil", "Combine", "Kariyer", "Teknik"])
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
        with technical_tab:
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
    columns = [
        "display_name", "draft_year", "forty", "combine_peak_speed",
        "combine_early_speed", "valid_game_plays",
    ]
    if "game_peak_speed" in cohort.columns:
        columns.insert(-1, "game_peak_speed")
    else:
        st.caption("Oyuncu bazlı rota zirve hızı bu araştırma çıktısında bulunmuyor.")
    st.dataframe(
        cohort[columns].rename(columns={
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



def show_research():
    if analytics.is_demo():
        st.info("Demo yalnızca kurgusal veri içerir. Gerçek oyunculara ait araştırma çıktıları "
                "bu ortamda yayınlanmaz; proje deposundaki araştırma yazılarından incelenebilir.")
        return
    try:
        studies = analytics.research_snapshot()
    except FileNotFoundError as exc:
        logger.warning("research_unavailable", extra={"event": "research_unavailable", "error_type": type(exc).__name__})
        st.info("Araştırma çıktıları bu kurulumda bulunmuyor.")
        return
    ol_research, wr_research = st.tabs(["OL faz ayr\u0131\u015ft\u0131rmas\u0131", "WR h\u0131z aktar\u0131m\u0131"])
    with ol_research:
        show_ol_research(studies["ol"])
    with wr_research:
        show_wr_research(studies["wr"])


st.set_page_config(page_title="NFL Veri Asistanı", page_icon="🏈", layout="wide")
st.title("🏈 NFL Veri Asistanı")
if analytics.is_demo():
    st.warning(analytics.DEMO_NOTE)
st.caption("Yalnızca yerel dataset • Gözlenen veriler ve kaynaklı analiz • MVP 0.1")
if not DB.exists():
    st.info("Oyuncu analizi i\u00e7in \u00f6nce `python -m pipelines.ingest` \u00e7al\u0131\u015ft\u0131r\u0131n. Ara\u015ft\u0131rma sonu\u00e7lar\u0131 manifestlerden g\u00f6r\u00fcnt\u00fclenebilir.")
    research, = st.tabs(["Ara\u015ft\u0131rma"])
    with research:
        show_research()
    st.stop()

players, research, chat, coverage = st.tabs(["Oyuncu analizi", "Ara\u015ft\u0131rma", "Sohbet", "Veri kapsam\u0131"])
with research:
    show_research()
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
    options = analytics.player_filter_options()["data"]
    filter_cols = st.columns([3, 1, 1, 1])
    with filter_cols[0]:
        search = st.text_input("Oyuncu veya takım ara", placeholder="İsim, takım kodu veya adı")
    with filter_cols[1]:
        positions = [row["nfl_position"] for row in options["positions"]]
        position = st.selectbox("Pozisyon", ["Tümü"] + positions,
                                format_func=lambda value: "Tümü" if value == "Tümü" else position_label(value))
    with filter_cols[2]:
        teams = [row["team_abbr"] for row in options.get("teams", [])]
        team = st.selectbox("Takım", ["Tümü"] + teams,
                            format_func=lambda value: "Tümü" if value == "Tümü" else team_label(value))
    with filter_cols[3]:
        seasons = sorted({r["season"] for r in analytics.dataset_summary()["data"]["seasons"]}, reverse=True)
        season = st.selectbox("Sezon", seasons, index=0) if seasons else None
    page_size = 100
    query_args = (search, None if position == "Tümü" else position)
    team_filter = {} if team == "Tümü" else {"team": team}
    first_page = analytics.player_directory(*query_args, limit=page_size, offset=0,
                                             paginated=True, **team_filter)["data"]
    total = first_page["total"]
    page_count = max(1, (total + page_size - 1) // page_size)
    page = st.number_input("Oyuncu listesi · sayfa", min_value=1, max_value=page_count, value=1, step=1)
    directory = first_page if page == 1 else analytics.player_directory(
        *query_args, limit=page_size, offset=(page - 1) * page_size,
        paginated=True, **team_filter,
    )["data"]
    matches = directory["rows"]
    selected_ids = st.session_state.setdefault("selected_player_ids", [])
    selected_records = st.session_state.setdefault("selected_player_records", {})
    selected_records.update({player["nfl_id"]: player for player in matches})
    by_id = selected_records
    if matches:
        st.caption(f"{total} oyuncu · Sayfa {page}/{page_count} · Bu sayfadan en fazla 10 oyuncu seç")
        st.dataframe(pd.DataFrame(matches)[["display_name", "teams", "nfl_position", "draft_year"]].rename(columns={
            "display_name": "Oyuncu", "teams": "Kayıtlı takımlar",
            "nfl_position": "Pozisyon", "draft_year": "Draft yılı",
        }), hide_index=True, width="stretch")
        player_options = {
            f'{player["display_name"]} · {player["nfl_position"]} · {player["draft_year"]} · #{player["nfl_id"]}': player["nfl_id"]
            for player in matches
        }
        widget_key = f"player_selection:{search.strip().casefold()}:{position}:{team}:{page}"
        page_defaults = [label for label, player_id in player_options.items() if player_id in selected_ids]
        if widget_key not in st.session_state:
            st.session_state[widget_key] = page_defaults
        selected_labels = st.multiselect("Kar\u015f\u0131la\u015ft\u0131r\u0131lacak oyuncular", list(player_options),
                                         max_selections=10, key=widget_key)
        page_selected = [player_options[label] for label in selected_labels]
        current_page_ids = {player["nfl_id"] for player in matches}
        selected_ids = [player_id for player_id in selected_ids if player_id not in current_page_ids]
        remaining_slots = max(0, 10 - len(selected_ids))
        if len(page_selected) > remaining_slots:
            st.warning("Karşılaştırma listesinde en fazla 10 oyuncu olabilir.")
        selected_ids.extend(page_selected[:remaining_slots])
        st.session_state.selected_player_ids = selected_ids
        selected = list(selected_ids)
        selected_players = [by_id[player_id] for player_id in selected if player_id in by_id]
    else:
        selected = list(selected_ids)
        selected_players = [by_id[player_id] for player_id in selected if player_id in by_id]
        st.info("Oyuncu bulunamad\u0131. Arama veya filtreleri de\u011fi\u015ftir.")
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
    if not provider_configured():
        st.info("Bu ortamda sohbet sağlayıcısı yapılandırılmamış; diğer sekmeler kullanılabilir.")
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
    question = st.chat_input("Dataset hakkında bir soru sorun", max_chars=4000)
    if st.session_state.get("pending_chat_example"):
        question = st.session_state.pop("pending_chat_example")
    if question:
        history = st.session_state.messages[-12:]
        with st.chat_message("user"):
            st.markdown(question)
        try:
            with st.spinner("Veriler inceleniyor..."):
                client_id = st.session_state.setdefault("client_id", f"ui:{uuid.uuid4()}")
                response = answer(question, history, client_id=client_id)
            st.session_state.messages.extend([{"role": "user", "content": question},
                                              {"role": "assistant", "content": response["answer"],
                                               "evidence": response["evidence"]}])
            with st.chat_message("assistant"):
                st.markdown(response["answer"])
                show_evidence(response["evidence"])
        except LimitExceeded as exc:
            logger.warning("chat_limited", extra={"event": "chat_limited", "error_type": "LimitExceeded"})
            st.warning(str(exc))
        except Exception as exc:
            logger.error("chat_ui_failed", extra={"event": "chat_ui_failed", "error_type": type(exc).__name__})
            st.error("Sohbet tamamlanamadı. Bağlantı ayarlarını kontrol edip tekrar deneyin.")
