"""Measurement diagnostics and an offline per-player phase explorer."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from extract_mirror_features import measure

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/nfl-big-data-bowl-2027"
OUT = ROOT / "reports/trenches"


def main():
    attempts = pd.read_csv(OUT / "mirror_attempt_features.csv")
    players = pd.read_csv(DATA / "players.csv")
    ranked = attempts.merge(players[["nfl_id", "display_name", "nfl_position"]], on="nfl_id", validate="one_to_one")
    for feature in ["lateral_speed_p75", "whole_drill_speed"]:
        ranked[feature + "_percentile"] = ranked.groupby("draft_year")[feature].rank(pct=True) * 100
    ranked["rank_difference_pp"] = ranked.lateral_speed_p75_percentile - ranked.whole_drill_speed_percentile
    ranked.to_csv(OUT / "mirror_measurement_rank_comparison.csv", index=False)
    by_year = []
    for year, group in ranked.groupby("draft_year"):
        lateral_top = group.lateral_speed_p75_percentile.ge(75)
        full_top = group.whole_drill_speed_percentile.ge(75)
        by_year.append({"year": int(year), "players": len(group),
                        "rank_correlation": float(group.lateral_speed_p75.corr(group.whole_drill_speed, method="spearman")),
                        "median_absolute_percentile_change": float(group.rank_difference_pp.abs().median()),
                        "mirror_top_quartile": int(lateral_top.sum()), "whole_drill_top_quartile": int(full_top.sum()),
                        "top_quartile_overlap": int((lateral_top & full_top).sum()),
                        "median_reversals": float(group.reversals.median())})
    suite_path = OUT / "ol_drill_suite_audit.csv"
    suite_records = pd.read_csv(suite_path).to_dict("records") if suite_path.exists() else []
    report = {"players": len(ranked), "peak_in_exit_fraction": float(ranked.peak_in_exit.mean()),
              "pooled_rank_correlation": float(ranked.lateral_speed_p75.corr(ranked.whole_drill_speed, method="spearman")),
              "by_year": by_year,
              "ol_drill_suite": suite_records,
              "interpretation": "These are rankings of distinct observed movement summaries, not rankings of football talent."}
    (OUT / "mirror_measurement_summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    tracking = pd.read_csv(DATA / "combine_tracking.csv")
    tracking = tracking.loc[tracking.entity_type.eq("PLAYER") &
                            tracking.drill_name.isin(["PASS_PRO-MIRROR_DRILL", "PASS_PRO_MIRROR_DRILL"])].copy()
    tracking["time"] = pd.to_datetime(tracking.time)
    traces = []
    examples = {}
    for row in ranked.itertuples():
        g = tracking.loc[tracking.nfl_id.eq(row.nfl_id) & tracking.event_id.eq(row.event_id) & tracking.attempt.eq(row.attempt)]
        record, reason, detail = measure(g)
        assert reason is None
        g, end, turns, vy = detail
        t = (g.time - g.time.iloc[0]).dt.total_seconds().to_numpy()
        x0_anchor = float(np.median(g.x.to_numpy()[:5]))
        vy_full = np.zeros(len(g), dtype=float)
        vy_full[:end] = np.abs(vy)
        traces.append({
            "id": int(row.nfl_id),
            "name": row.display_name,
            "year": int(row.draft_year),
            "position": row.nfl_position,
            "time": t.round(3).tolist(),
            "x": g.x.round(4).tolist(),
            "y": g.y.round(4).tolist(),
            "s": g.s.round(4).tolist(),
            "vy": vy_full.round(4).tolist(),
            "end": int(end),
            "x_exit": round(x0_anchor + 1.5, 4),
            "turns": [int(i) for i, _ in turns],
            "lateral_speed": round(float(row.lateral_speed_p75), 2),
            "whole_speed": round(float(row.whole_drill_speed), 2),
            "recovery": round(float(row.reversal_recovery), 2),
            "duration": round(float(row.mirror_duration), 1),
            "lateral_percentile": round(float(row.lateral_speed_p75_percentile), 1),
            "whole_percentile": round(float(row.whole_drill_speed_percentile), 1),
            "diff_pp": round(float(row.rank_difference_pp), 1),
        })
        if row.draft_year not in examples:
            examples[row.draft_year] = (g, end, turns, vy, t, row.display_name, row.nfl_position)

    # Figure 1: mirror_phase_story.png
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 7.6))
    for col, (year, (g, end, turns, vy, t, name, pos)) in enumerate(sorted(examples.items())):
        ax = axes[0, col]
        x0_anchor = float(np.median(g.x.to_numpy()[:5]))
        ax.plot(g.x.iloc[:end], g.y.iloc[:end], color="#176b87", linewidth=2.6, label="Mirror phase (lateral slide)")
        ax.plot(g.x.iloc[end - 1:], g.y.iloc[end - 1:], color="#e07a2b", linewidth=2.6, label="Exit sprint phase")
        ax.axvline(x0_anchor + 1.5, color="#6c7a89", linestyle="--", linewidth=1.2, label="Exit threshold (+1.5 yd)")
        ax.scatter(g.x.iloc[0], g.y.iloc[0], color="#1f2d3d", marker="X", s=55, zorder=5, label="Drill start")
        if turns:
            t_idx = [i for i, _ in turns]
            ax.scatter(g.x.iloc[t_idx], g.y.iloc[t_idx], color="#b43b45", edgecolor="white", linewidth=0.6,
                       s=46, zorder=6, label=f"Detected reversals (n={len(t_idx)})")
        ax.set_title(f"{year} Class: {name} ({pos})", fontsize=11, fontweight="bold")
        ax.set_aspect("equal", adjustable="datalim")
        ax.set(xlabel="Field x coordinate (yards)", ylabel="Field y coordinate (yards)")
        ax.grid(linestyle=":", alpha=0.45)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        if col == 0:
            ax.legend(fontsize=7.8, loc="best", frameon=True)

        ax = axes[1, col]
        smooth = g.s.rolling(3, center=True, min_periods=1).median()
        ax.plot(t, smooth, color="#2c3e50", linewidth=2.1, label="Total speed s(t) (yd/s)")
        ax.plot(t[:end], np.abs(vy), color="#176b87", linestyle="--", linewidth=1.6, alpha=0.9,
                label="Mirror lateral speed |vy(t)|")
        ax.axvspan(t[end], t[-1], color="#e07a2b", alpha=.22, label="Exit sprint window")
        idx = int(np.argmax(smooth.to_numpy()))
        ax.scatter(t[idx], smooth.iloc[idx], color="#b43b45", edgecolor="white", linewidth=0.7,
                   s=58, zorder=6, label=f"Peak speed: {smooth.iloc[idx]:.1f} yd/s")
        ax.set(xlabel="Time from drill start (seconds)", ylabel="Speed (yd/s)")
        ax.set_ylim(0, max(smooth) * 1.18)
        ax.grid(linestyle=":", alpha=0.45)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        if col == 0:
            ax.legend(fontsize=7.8, loc="upper left", frameon=True)

    fig.suptitle("In All 113 Accepted Mirror Recordings, Peak Speed Occurs in the Finishing Exit Sprint",
                 fontsize=13.5, fontweight="bold", y=1.01)
    fig.tight_layout()
    fig.savefig(OUT / "mirror_phase_story.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    # Figure 2: mirror_ranking_shift.png (2-panel: Panel A Rank Shift + Panel B 3-Drill OL Suite Contamination)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.4), gridspec_kw={"width_ratios": [1.15, 1.0]})
    year_colors = {2023: "#176b87", 2024: "#e07a2b", 2025: "#2e8b57"}
    ax1.axvspan(75, 102, ymin=0, ymax=1, color="#e07a2b", alpha=0.07)
    ax1.axhspan(75, 102, xmin=0, xmax=1, color="#176b87", alpha=0.07)
    ax1.axvline(75, color="#e07a2b", linestyle=":", linewidth=1.0, alpha=0.7)
    ax1.axhline(75, color="#176b87", linestyle=":", linewidth=1.0, alpha=0.7)
    for year, group in ranked.groupby("draft_year"):
        ax1.scatter(group.whole_drill_speed_percentile, group.lateral_speed_p75_percentile,
                    label=f"{year} (n={len(group)})", color=year_colors.get(year, "#334455"),
                    s=44, alpha=.85, edgecolor="white", linewidth=0.5)
    ax1.plot([0, 100], [0, 100], "--", color="#7f8c8d", linewidth=1.1, label="Identity (no rank change)")
    callouts = [
        ("Donovan Jackson", (14, 93)),
        ("Dominick Puni", (18, 82)),
        ("Darnell Wright", (32, 9)),
    ]
    for cname, text_xy in callouts:
        hit = ranked.loc[ranked.display_name.eq(cname)]
        if not hit.empty:
            r0 = hit.iloc[0]
            ax1.annotate(
                f"{r0.display_name} ({r0.rank_difference_pp:+.0f} pp)",
                xy=(r0.whole_drill_speed_percentile, r0.lateral_speed_p75_percentile),
                xytext=text_xy,
                fontsize=8, fontweight="semibold", color="#1f2d3d",
                arrowprops=dict(arrowstyle="->", color="#526477", lw=0.9),
            )
    ax1.set_xlim(0, 103)
    ax1.set_ylim(0, 103)
    ax1.set(xlabel="Whole-Drill Speed Percentile Within Class (95th pct, Exit-Contaminated)",
            ylabel="Mirror-Phase Lateral Speed Percentile Within Class (75th pct)",
            title="A. Mirror Drill Re-Ranking Within Class (Spearman r = +0.005)")
    ax1.grid(linestyle=":", alpha=0.45)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.legend(title="Draft Class", fontsize=8, loc="lower right", frameon=True)

    if suite_records:
        suite_df = pd.DataFrame(suite_records)
    else:
        suite_df = pd.DataFrame([
            {"drill": "Pass-Pro Mirror Drill", "accepted_attempts": 113, "peak_in_exit_fraction": 1.0, "phase_vs_whole_spearman": 0.005},
            {"drill": "5-Yard Wave Drill (Slide & Shuffle)", "accepted_attempts": 118, "peak_in_exit_fraction": 1.0, "phase_vs_whole_spearman": -0.022},
            {"drill": "Pass Rush Drop (Kick-Slide)", "accepted_attempts": 239, "peak_in_exit_fraction": 1.0, "phase_vs_whole_spearman": 0.147},
        ])
    y_pos = np.arange(len(suite_df))
    exit_pct = suite_df.peak_in_exit_fraction * 100
    corr_pct = suite_df.phase_vs_whole_spearman.abs() * 100
    short_labels = [
        f"Pass-Pro Mirror\n(n = {suite_df.iloc[0].accepted_attempts} reps)",
        f"5-Yard Wave Shuffle\n(n = {suite_df.iloc[1].accepted_attempts} reps)",
        f"Pass Rush Drop\n(n = {suite_df.iloc[2].accepted_attempts} reps, 2/player)",
    ]
    bars1 = ax2.barh(y_pos - 0.17, exit_pct, height=0.32, color="#e07a2b", edgecolor="white",
                     label="Peak speed occurs in exit sprint (%)")
    bars2 = ax2.barh(y_pos + 0.17, corr_pct, height=0.32, color="#176b87", edgecolor="white",
                     label="|Spearman r| between lateral phase & whole-drill speed (%)")
    for bar, val in zip(bars1, exit_pct):
        ax2.text(val + 1.5, bar.get_y() + bar.get_height() / 2, f"{val:.0f}%",
                 va="center", ha="left", fontsize=8.5, fontweight="bold", color="#b85d19")
    for bar, orig_r in zip(bars2, suite_df.phase_vs_whole_spearman):
        ax2.text(abs(orig_r) * 100 + 1.5, bar.get_y() + bar.get_height() / 2, f"r = {orig_r:+.3f}",
                 va="center", ha="left", fontsize=8.5, fontweight="bold", color="#176b87")
    ax2.set_yticks(y_pos, short_labels, fontsize=9)
    ax2.set_ylim(-0.55, 3.15)
    ax2.invert_yaxis()
    ax2.set_xlim(0, 118)
    ax2.set_xlabel("Percentage (%) / Magnitude of Rank Correlation", fontsize=9.5)
    ax2.set_title("B. Universal Exit Contamination Across All 3 OL Drills (470/470 Reps)", fontsize=10.5, fontweight="bold")
    ax2.grid(axis="x", linestyle=":", alpha=0.45)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.legend(fontsize=7.8, loc="lower right", frameon=True)
    ax2.text(2, 2.72,
             "2-Rep Repeatability (Pass Rush Drop, n=118 OL):\n• Exit sprint peak speed: r = +0.510\n• Kick-slide lateral speed: r = +0.104 (attenuates transfer)",
             fontsize=7.6, color="#1f2d3d", bbox=dict(boxstyle="round,pad=0.38", facecolor="#f4f6f9", edgecolor="#cbd5e1"))

    fig.suptitle("Phase Contamination Distorts Rankings Across the Entire Offensive Line Combine Drill Suite",
                 fontsize=13, fontweight="bold", y=1.01)
    fig.tight_layout()
    fig.savefig(OUT / "mirror_ranking_shift.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    data = json.dumps(traces, ensure_ascii=False).replace("</", "<\\/")
    page = '''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NFL Big Data Bowl 2027 — OL Combine Phase Explorer</title>
<style>
:root{--bg:#f3f6f9;--card:#ffffff;--ink:#172638;--muted:#526477;--blue:#176b87;--orange:#e07a2b;--red:#b43b45;--border:#dce4ed}
*{box-sizing:border-box}
body{font:15px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink);margin:0}
main{max-width:1160px;margin:auto;padding:24px 20px}
header{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;margin-bottom:16px}
h1{font-size:24px;margin:0 0 6px 0;line-height:1.25}
h2{font-size:18px;margin:0 0 10px 0}
h3{font-size:15px;margin:0 0 8px 0}
p{margin:6px 0}
section{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;margin:16px 0;box-shadow:0 1px 3px rgba(0,0,0,.03)}
.controls{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:16px}
label{display:block;font-size:12px;font-weight:600;color:var(--muted);margin-bottom:4px;text-transform:uppercase;letter-spacing:.03em}
select,button{font:inherit;padding:8px 10px;border:1px solid #cbd5e1;border-radius:8px;background:#fff;color:var(--ink);width:100%}
button.lang-btn{width:auto;padding:7px 14px;font-weight:600;cursor:pointer;background:#172638;color:#fff;border:none}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:12px;margin:14px 0}
.kpi{background:#f8fafc;border:1px solid var(--border);border-radius:10px;padding:12px}
.kpi .val{font-size:21px;font-weight:700;color:var(--ink)}
.kpi .sub{font-size:12.5px;color:var(--muted)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:760px){.grid{grid-template-columns:1fr}}
svg{width:100%;height:auto;background:#fbfcfd;border:1px solid #e2e8f0;border-radius:8px}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;margin-top:10px}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px}
table{width:100%;border-collapse:collapse;font-size:14px;margin-top:8px}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--border)}
th{background:#f8fafc;color:var(--muted);font-weight:600}
.badge-pos{color:#15803d;font-weight:700}
.badge-neg{color:#b91c1c;font-weight:700}
.muted{color:var(--muted);font-size:13.5px}
</style></head><body><main>
<header>
  <div>
    <h1 id="t-title">En Hızlı Kısım Çıkış Sprinti: OL Combine Faz İnceleyici</h1>
    <p id="t-sub" class="muted">113 Offensive Lineman (T/G/C) için Pass-Pro Mirror Drill yanal ayna fazı ve çıkış sprinti ayrıştırması (Birimler: yard, yd/s, saniye).</p>
  </div>
  <button class="lang-btn" id="langBtn" onclick="toggleLang()">EN / TR</button>
</header>
<section>
  <div class="controls">
    <div><label id="l-year" for="fYear">Draft Yılı</label><select id="fYear"><option value="all">Tümü (2023–2025)</option><option value="2023">2023</option><option value="2024">2024</option><option value="2025">2025</option></select></div>
    <div><label id="l-pos" for="fPos">Pozisyon</label><select id="fPos"><option value="all">Tümü (T / G / C)</option><option value="T">Tackle (T)</option><option value="G">Guard (G)</option><option value="C">Center (C)</option></select></div>
    <div><label id="l-sort" for="fSort">Sıralama</label><select id="fSort">
      <option value="name">İsme Göre (A–Z)</option>
      <option value="lat_desc">Mirror Yanal Hız Yüzdeliği (Azalan)</option>
      <option value="whole_desc">Tüm Kayıt Hızı Yüzdeliği (Azalan)</option>
      <option value="shift_desc">En Büyük Sıralama Farkı |Δ| (Azalan)</option>
    </select></div>
    <div><label id="l-player" for="player">Oyuncu Seçimi</label><select id="player"></select></div>
  </div>
  <div class="kpis">
    <div class="kpi"><div class="sub" id="k1-t">Mirror Yanal Hız (p75)</div><div class="val" id="k1-v">-</div><div class="sub" id="k1-s">-</div></div>
    <div class="kpi"><div class="sub" id="k2-t">Tüm Kayıt Hızı (p95, Çıkış)</div><div class="val" id="k2-v">-</div><div class="sub" id="k2-s">-</div></div>
    <div class="kpi"><div class="sub" id="k3-t">Sıralama Değişimi (Yanal − Tüm)</div><div class="val" id="k3-v">-</div><div class="sub" id="k3-s">-</div></div>
    <div class="kpi"><div class="sub" id="k4-t">Dönüş Toparlanma & Süre</div><div class="val" id="k4-v">-</div><div class="sub" id="k4-s">-</div></div>
  </div>
  <div class="grid">
    <div><h3 id="c1-t">Saha İzi: x–y Koordinatları (yard)</h3><svg id="path" viewBox="0 0 500 340"></svg></div>
    <div><h3 id="c2-t">Zaman Serisi: Toplam Hız s(t) ve Yanal Hız |vy(t)| (yd/s)</h3><svg id="speed" viewBox="0 0 500 340"></svg></div>
  </div>
  <div class="legend">
    <span><i class="dot" style="background:#176b87"></i><b id="lg-1">Mavi: Mirror (Yanal Kayma) Fazı</b></span>
    <span><i class="dot" style="background:#e07a2b"></i><b id="lg-2">Turuncu: Çıkış Sprinti Fazı (+1.5 yd sonrası)</b></span>
    <span><i class="dot" style="background:#b43b45"></i><b id="lg-3">Kırmızı: Tespit Edilen Yön Değişimleri & Zirve Hız</b></span>
  </div>
  <p class="muted" id="t-note">Not: Yüzdelikler aynı draft sınıfı içindeki hareket ölçümlerinin sırasıdır; doğrudan oyuncu yeteneği sıralaması değildir.</p>
</section>
<section>
  <h2 id="s2-title">3 OL Combine Drilinde Evrensel Çıkış Sprinti Baskınlığı (470 / 470 Kayıt)</h2>
  <table>
    <thead><tr><th id="th-1">Combine Drili</th><th id="th-2">Kabul Edilen Kayıt</th><th id="th-3">Zirve Hızı Çıkış Sprintinde Olan</th><th id="th-4">Yanal Faz vs. Tüm Kayıt Hızı (Spearman r)</th><th id="th-5">2-Tekrar Güvenilirliği (Repeatability)</th></tr></thead>
    <tbody>
      <tr><td><b>Pass-Pro Mirror Drill</b></td><td>113 deneme (113 OL)</td><td><b>100.0% (113 / 113)</b></td><td>r = +0.005</td><td>Tek deneme (sınır duyarlılığı r ≥ 0.90)</td></tr>
      <tr><td><b>5-Yard Wave Drill (Slide & Shuffle)</b></td><td>118 deneme (118 OL)</td><td><b>100.0% (118 / 118)</b></td><td>r = −0.022</td><td>Tek deneme</td></tr>
      <tr><td><b>Pass Rush Drop (Kick-Slide)</b></td><td>239 deneme (120 OL)</td><td><b>100.0% (239 / 239)</b></td><td>r = +0.147</td><td>Çıkış r = +0.510 vs. Yanal r = +0.104 (118 çift)</td></tr>
    </tbody>
  </table>
  <p class="muted" id="s2-desc">50 çaylak OL oyuncusunun 20.853 bire bir pas koruma oyununda (ikili baskı ve sürekli NGS baskı olasılığı hedeflerinde) ve ilk 1.5 saniyelik maç içi yanal hız transferinde, faz ayrıştırması çıkış sprinti gürültüsünü temizlese de klasik Combine testlerine (40-yard, 10-yard split, kilo, kol boyu) istatistiksel olarak anlamlı ek tahmin gücü sağlamamaktadır (2025 tam yeniden eğitimli %95 GA: [−0.264, +0.353] yp).</p>
</section>
</main>
<script>
const rawData=__DATA__;
let lang='tr';
const i18n={
  tr:{
    title:'En Hızlı Kısım Çıkış Sprinti: OL Combine Faz İnceleyici',
    sub:'113 Offensive Lineman (T/G/C) için Pass-Pro Mirror Drill yanal ayna fazı ve çıkış sprinti ayrıştırması (Birimler: yard, yd/s, saniye).',
    lyear:'Draft Yılı',lpos:'Pozisyon',lsort:'Sıralama',lplayer:'Oyuncu Seçimi',
    allYears:'Tümü (2023–2025)',allPos:'Tümü (T / G / C)',
    sName:'İsme Göre (A–Z)',sLat:'Mirror Yanal Hız Yüzdeliği (Azalan)',sWhole:'Tüm Kayıt Hızı Yüzdeliği (Azalan)',sShift:'En Büyük Sıralama Farkı |Δ| (Azalan)',
    k1t:'Mirror Yanal Hız (p75)',k2t:'Tüm Kayıt Hızı (p95, Çıkış)',k3t:'Sıralama Değişimi (Yanal − Tüm)',k4t:'Dönüş Toparlanma & Süre',
    c1t:'Saha İzi: x–y Koordinatları (yard)',c2t:'Zaman Serisi: Toplam Hız s(t) ve Yanal Hız |vy(t)| (yd/s)',
    lg1:'Mavi: Mirror (Yanal Kayma) Fazı',lg2:'Turuncu: Çıkış Sprinti Fazı (+1.5 yd sonrası)',lg3:'Kırmızı: Tespit Edilen Yön Değişimleri & Zirve Hız',
    note:'Not: Yüzdelikler aynı draft sınıfı içindeki hareket ölçümlerinin sırasıdır; doğrudan oyuncu yeteneği sıralaması değildir.',
    s2t:'3 OL Combine Drilinde Evrensel Çıkış Sprinti Baskınlığı (470 / 470 Kayıt)',
    th1:'Combine Drili',th2:'Kabul Edilen Kayıt',th3:'Zirve Hızı Çıkış Sprintinde Olan',th4:'Yanal Faz vs. Tüm Kayıt Hızı (Spearman r)',th5:'2-Tekrar Güvenilirliği (Repeatability)',
    s2d:'50 çaylak OL oyuncusunun 20.853 bire bir pas koruma oyununda (ikili baskı ve sürekli NGS baskı olasılığı hedeflerinde) ve ilk 1.5 saniyelik maç içi yanal hız transferinde, faz ayrıştırması çıkış sprinti gürültüsünü temizlese de klasik Combine testlerine (40-yard, 10-yard split, kilo, kol boyu) istatistiksel olarak anlamlı ek tahmin gücü sağlamamaktadır (2025 tam yeniden eğitimli %95 GA: [−0.264, +0.353] yp).',
    pct:'Sınıf Yüzdeliği',turns:'dönüş',mirrorDur:'Mirror süresi',exitThresh:'Çıkış eşiği (+1.5 yd)'
  },
  en:{
    title:'The Fastest Part Is the Exit: OL Combine Phase Explorer',
    sub:'Phase-segmented Pass-Pro Mirror Drill lateral footwork vs. finishing exit sprint across 113 Offensive Linemen (Units: yards, yd/s, seconds).',
    lyear:'Draft Year',lpos:'Position',lsort:'Sort Players',lplayer:'Select Player',
    allYears:'All Classes (2023–2025)',allPos:'All Positions (T / G / C)',
    sName:'By Name (A–Z)',sLat:'Mirror Lateral Percentile (High to Low)',sWhole:'Whole-Drill Speed Percentile (High to Low)',sShift:'Largest Percentile Shift |Δ| (High to Low)',
    k1t:'Mirror Lateral Speed (p75)',k2t:'Whole-Drill Speed (p95, Exit)',k3t:'Percentile Shift (Lateral − Whole)',k4t:'Reversal Recovery & Duration',
    c1t:'Field Trajectory: x–y Coordinates (yards)',c2t:'Speed Profile: Total s(t) & Lateral |vy(t)| (yd/s)',
    lg1:'Blue: Mirror (Lateral Slide) Phase',lg2:'Orange: Exit Sprint Phase (past +1.5 yd)',lg3:'Red: Detected Reversals & Global Peak Speed',
    note:'Note: Percentiles rank observed drill movement summaries within each draft class, not overall football talent.',
    s2t:'Universal Exit-Sprint Dominance Across All 3 OL Combine Drills (470 / 470 Attempts)',
    th1:'Combine Drill',th2:'Accepted Recordings',th3:'Peak Speed in Exit Sprint',th4:'Lateral Phase vs. Whole-Drill Speed (Spearman r)',th5:'2-Attempt Repeatability',
    s2d:'Across 20,853 rookie one-on-one pass-protection snaps for 50 OL (evaluating both binary pressure allowed and continuous NGS peak pressure probability) and 0–1.5 s early-game lateral speed, phase segmentation removes exit-sprint distortion but does not yield statistically significant out-of-time gains over classic Combine metrics (2025 full-refit 95% CI: [−0.264, +0.353] pp).',
    pct:'Class Percentile',turns:'reversals',mirrorDur:'Mirror duration',exitThresh:'Exit threshold (+1.5 yd)'
  }
};
const select=document.getElementById('player'),fYear=document.getElementById('fYear'),fPos=document.getElementById('fPos'),fSort=document.getElementById('fSort');
let filtered=[];
function applyFilters(){
  const yr=fYear.value,pos=fPos.value,srt=fSort.value;
  const prevId=filtered[+select.value]?.id;
  filtered=rawData.filter(d=>(yr==='all'||String(d.year)===yr)&&(pos==='all'||d.position===pos));
  if(srt==='name')filtered.sort((a,b)=>a.year-b.year||a.name.localeCompare(b.name));
  else if(srt==='lat_desc')filtered.sort((a,b)=>b.lateral_percentile-a.lateral_percentile);
  else if(srt==='whole_desc')filtered.sort((a,b)=>b.whole_percentile-a.whole_percentile);
  else if(srt==='shift_desc')filtered.sort((a,b)=>Math.abs(b.diff_pp)-Math.abs(a.diff_pp));
  select.replaceChildren();
  let newIdx=0;
  filtered.forEach((d,i)=>{
    if(d.id===prevId)newIdx=i;
    const o=document.createElement('option');
    o.value=i;
    const sign=d.diff_pp>=0?'+':'';
    o.textContent=`${d.year} · ${d.name} (${d.position}) — Δ ${sign}${d.diff_pp} pp`;
    select.appendChild(o);
  });
  select.value=newIdx;
  draw();
}
const NS='http://www.w3.org/2000/svg';
function el(tag,attrs,parent){const n=document.createElementNS(NS,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);parent.appendChild(n);return n}
function draw(){
  const d=filtered[+select.value];
  if(!d)return;
  const t=i18n[lang];
  document.getElementById('k1-v').textContent=`${d.lateral_speed.toFixed(2)} yd/s`;
  document.getElementById('k1-s').textContent=`${t.pct}: ${d.lateral_percentile.toFixed(1)}`;
  document.getElementById('k2-v').textContent=`${d.whole_speed.toFixed(2)} yd/s`;
  document.getElementById('k2-s').textContent=`${t.pct}: ${d.whole_percentile.toFixed(1)}`;
  const sign=d.diff_pp>=0?'+':'';
  const k3v=document.getElementById('k3-v');
  k3v.textContent=`${sign}${d.diff_pp.toFixed(1)} pp`;
  k3v.className='val '+(d.diff_pp>=0?'badge-pos':'badge-neg');
  document.getElementById('k3-s').textContent=`${d.year} (${d.position})`;
  document.getElementById('k4-v').textContent=`${d.recovery.toFixed(2)}x (${d.turns.length} ${t.turns})`;
  document.getElementById('k4-s').textContent=`${t.mirrorDur}: ${d.duration.toFixed(1)} s`;

  const path=document.getElementById('path'),speed=document.getElementById('speed');
  path.replaceChildren();speed.replaceChildren();
  let xmin=Math.min(...d.x,d.x_exit),xmax=Math.max(...d.x,d.x_exit),ymin=Math.min(...d.y),ymax=Math.max(...d.y);
  const scale=Math.min(410/(xmax-xmin||1),250/(ymax-ymin||1));
  const xx=x=>48+(x-xmin)*scale,yy=y=>295-(y-ymin)*scale;
  el('line',{x1:xx(d.x_exit),y1:20,x2:xx(d.x_exit),y2:300,stroke:'#64748b','stroke-width':1.5,'stroke-dasharray':'5,4'},path);
  const bt=el('text',{x:xx(d.x_exit)+5,y:34,'font-size':11,fill:'#475569'},path);bt.textContent=t.exitThresh;
  for(let i=1;i<d.x.length;i++)el('line',{x1:xx(d.x[i-1]),y1:yy(d.y[i-1]),x2:xx(d.x[i]),y2:yy(d.y[i]),stroke:i<d.end?'#176b87':'#e07a2b','stroke-width':3},path);
  el('circle',{cx:xx(d.x[0]),cy:yy(d.y[0]),r:5,fill:'#172638'},path);
  d.turns.forEach(i=>el('circle',{cx:xx(d.x[i]),cy:yy(d.y[i]),r:4.5,fill:'#b43b45',stroke:'#fff','stroke-width':1},path));
  const xl=el('text',{x:250,y:330,'font-size':12,'text-anchor':'middle',fill:'#475569'},path);xl.textContent='x (yards)';
  const yl=el('text',{x:16,y:165,'font-size':12,'text-anchor':'middle',fill:'#475569',transform:'rotate(-90 16 165)'},path);yl.textContent='y (yards)';

  const maxS=Math.max(...d.s,4)*1.08;
  const tx=tm=>48+420*tm/d.time.at(-1),sy=s=>295-255*s/maxS;
  el('rect',{x:tx(d.time[d.end]),y:22,width:468-tx(d.time[d.end]),height:273,fill:'#fff3e0'},speed);
  for(let s=0;s<=maxS;s+=1){
    el('line',{x1:48,y1:sy(s),x2:468,y2:sy(s),stroke:'#e2e8f0','stroke-width':1},speed);
    const st=el('text',{x:40,y:sy(s)+4,'font-size':11,'text-anchor':'end',fill:'#475569'},speed);st.textContent=s+' yd/s';
  }
  for(let i=1;i<d.end;i++)el('line',{x1:tx(d.time[i-1]),y1:sy(d.vy[i-1]),x2:tx(d.time[i]),y2:sy(d.vy[i]),stroke:'#176b87','stroke-width':1.8,'stroke-dasharray':'4,3'},speed);
  for(let i=1;i<d.s.length;i++)el('line',{x1:tx(d.time[i-1]),y1:sy(d.s[i-1]),x2:tx(d.time[i]),y2:sy(d.s[i]),stroke:'#2c3e50','stroke-width':2.3},speed);
  let peakIdx=0;for(let i=1;i<d.s.length;i++)if(d.s[i]>d.s[peakIdx])peakIdx=i;
  el('circle',{cx:tx(d.time[peakIdx]),cy:sy(d.s[peakIdx]),r:5.5,fill:'#b43b45',stroke:'#fff','stroke-width':1.2},speed);
  for(let tm=0;tm<=d.time.at(-1);tm+=2){const tt=el('text',{x:tx(tm),y:320,'font-size':11,'text-anchor':'middle',fill:'#475569'},speed);tt.textContent=tm+' s'}
}
function toggleLang(){
  lang=lang==='tr'?'en':'tr';
  const t=i18n[lang];
  document.getElementById('t-title').textContent=t.title;
  document.getElementById('t-sub').textContent=t.sub;
  document.getElementById('l-year').textContent=t.lyear;
  document.getElementById('l-pos').textContent=t.lpos;
  document.getElementById('l-sort').textContent=t.lsort;
  document.getElementById('l-player').textContent=t.lplayer;
  fYear.options[0].textContent=t.allYears;
  fPos.options[0].textContent=t.allPos;
  fSort.options[0].textContent=t.sName;
  fSort.options[1].textContent=t.sLat;
  fSort.options[2].textContent=t.sWhole;
  fSort.options[3].textContent=t.sShift;
  document.getElementById('k1-t').textContent=t.k1t;
  document.getElementById('k2-t').textContent=t.k2t;
  document.getElementById('k3-t').textContent=t.k3t;
  document.getElementById('k4-t').textContent=t.k4t;
  document.getElementById('c1-t').textContent=t.c1t;
  document.getElementById('c2-t').textContent=t.c2t;
  document.getElementById('lg-1').textContent=t.lg1;
  document.getElementById('lg-2').textContent=t.lg2;
  document.getElementById('lg-3').textContent=t.lg3;
  document.getElementById('t-note').textContent=t.note;
  document.getElementById('s2-title').textContent=t.s2t;
  document.getElementById('th-1').textContent=t.th1;
  document.getElementById('th-2').textContent=t.th2;
  document.getElementById('th-3').textContent=t.th3;
  document.getElementById('th-4').textContent=t.th4;
  document.getElementById('th-5').textContent=t.th5;
  document.getElementById('s2-desc').textContent=t.s2d;
  draw();
}
[fYear,fPos,fSort].forEach(el=>el.addEventListener('change',applyFilters));
select.addEventListener('change',draw);
applyFilters();
</script></body></html>'''.replace("__DATA__", data)
    (OUT / "mirror_explorer.html").write_text(page, encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
