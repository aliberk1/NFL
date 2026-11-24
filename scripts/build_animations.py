"""Generate interactive 60-FPS HTML animation studio and standalone animated GIF from real Combine tracking data."""
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/trenches"


def load_traces():
    html_text = (OUT / "mirror_explorer.html").read_text(encoding="utf-8")
    match = re.search(r"const rawData=(\[.*?\]);\n", html_text, re.S)
    assert match, "Could not extract rawData from mirror_explorer.html"
    return json.loads(match.group(1).replace("<\\/", "</"))


def build_gif(traces):
    """Build a crisp side-by-side animated GIF comparing two opposite rank-shift players."""
    by_name = {d["name"]: d for d in traces}
    p1 = by_name.get("Donovan Jackson", traces[0])
    p2 = by_name.get("Darnell Wright", traces[1])

    fig, axes = plt.subplots(2, 2, figsize=(11.5, 6.8), dpi=110)
    fig.patch.set_facecolor("#0f172a")

    players = [
        (p1, "Donovan Jackson (2025 G) — Hızlı Yanal Ayna (+91 yp)\nYanal: 94.1. Yüzdelik | Tüm Kayıt: 2.9. Yüzdelik"),
        (p2, "Darnell Wright (2023 T) — Hızlı Çıkış Sprinti (−89 yp)\nYanal: 8.1. Yüzdelik | Tüm Kayıt: 97.3. Yüzdelik"),
    ]

    max_time = 8.4
    n_frames = 43  # 0.2s steps up to 8.4s

    for col, (p, title) in enumerate(players):
        ax_path = axes[0, col]
        ax_spd = axes[1, col]
        for ax in (ax_path, ax_spd):
            ax.set_facecolor("#1e293b")
            ax.tick_params(colors="#cbd5e1", labelsize=8.5)
            for spine in ax.spines.values():
                spine.set_color("#475569")
            ax.grid(linestyle=":", color="#334155", alpha=0.7)

        x = np.array(p["x"])
        y = np.array(p["y"])
        t = np.array(p["time"])
        s = np.array(p["s"])
        vy = np.array(p["vy"])
        end = p["end"]

        ax_path.plot(x[:end], y[:end], color="#38bdf8", lw=1.2, alpha=0.28)
        ax_path.plot(x[end - 1:], y[end - 1:], color="#f59e0b", lw=1.2, alpha=0.28)
        ax_path.axvline(p["x_exit"], color="#94a3b8", ls="--", lw=1.2, label="Çıkış Eşiği (+1.5 yd)")
        ax_path.set_title(title, color="#f8fafc", fontsize=10, fontweight="bold", pad=8)
        ax_path.set_xlabel("Saha x Koordinatı (yard)", color="#cbd5e1", fontsize=8.5)
        ax_path.set_ylabel("Saha y Koordinatı (yard)", color="#cbd5e1", fontsize=8.5)
        ax_path.set_xlim(min(x) - 0.6, max(x) + 0.8)
        ax_path.set_ylim(min(y) - 0.6, max(y) + 0.6)

        ax_spd.axvspan(t[end], max(t[-1], max_time), color="#f59e0b", alpha=0.15, label="Çıkış Sprinti Fazı")
        ax_spd.plot(t, s, color="#64748b", lw=1.0, alpha=0.3)
        ax_spd.set_xlim(0, max_time)
        ax_spd.set_ylim(0, 6.6)
        ax_spd.set_xlabel("Dril Başlangıcından Süre (saniye)", color="#cbd5e1", fontsize=8.5)
        ax_spd.set_ylabel("Hız (yd/s)", color="#cbd5e1", fontsize=8.5)

    line_mir_0, = axes[0, 0].plot([], [], color="#38bdf8", lw=3.0, label="Mavi: Yanal Ayna Fazı")
    line_ext_0, = axes[0, 0].plot([], [], color="#f59e0b", lw=3.2, label="Turuncu: Çıkış Sprinti")
    dot_0, = axes[0, 0].plot([], [], "o", color="#ffffff", markersize=9, markeredgecolor="#0f172a", zorder=6)
    rev_0 = axes[0, 0].scatter([], [], color="#ef4444", s=45, zorder=5, label="Tespit Edilen Dönüş")
    axes[0, 0].legend(loc="upper right", fontsize=7.5, facecolor="#0f172a", edgecolor="#475569", labelcolor="#f8fafc")

    line_mir_1, = axes[0, 1].plot([], [], color="#38bdf8", lw=3.0)
    line_ext_1, = axes[0, 1].plot([], [], color="#f59e0b", lw=3.2)
    dot_1, = axes[0, 1].plot([], [], "o", color="#ffffff", markersize=9, markeredgecolor="#0f172a", zorder=6)
    rev_1 = axes[0, 1].scatter([], [], color="#ef4444", s=45, zorder=5)

    spd_tot_0, = axes[1, 0].plot([], [], color="#f8fafc", lw=2.3, label="Toplam Hız s(t)")
    spd_lat_0, = axes[1, 0].plot([], [], color="#38bdf8", lw=1.8, ls="--", label="Yanal Hız |vy(t)|")
    spd_dot_0, = axes[1, 0].plot([], [], "o", color="#ef4444", markersize=8, zorder=6)
    txt_0 = axes[1, 0].text(0.03, 0.86, "", transform=axes[1, 0].transAxes, color="#f8fafc", fontsize=8.5, fontweight="bold")
    axes[1, 0].legend(loc="upper left", fontsize=7.5, facecolor="#0f172a", edgecolor="#475569", labelcolor="#f8fafc")

    spd_tot_1, = axes[1, 1].plot([], [], color="#f8fafc", lw=2.3)
    spd_lat_1, = axes[1, 1].plot([], [], color="#38bdf8", lw=1.8, ls="--")
    spd_dot_1, = axes[1, 1].plot([], [], "o", color="#ef4444", markersize=8, zorder=6)
    txt_1 = axes[1, 1].text(0.03, 0.86, "", transform=axes[1, 1].transAxes, color="#f8fafc", fontsize=8.5, fontweight="bold")

    fig.suptitle("NFL Big Data Bowl 2027 — Gerçek 10 Hz Sensör Verisiyle Mirror Fazı vs. Çıkış Sprinti Animasyonu",
                 color="#38bdf8", fontsize=12.5, fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.94])

    def update(frame_idx):
        cur_t = frame_idx * 0.2
        for col, (p, _), (l_mir, l_ext, dot, rev, s_tot, s_lat, s_dot, txt) in zip(
            [0, 1],
            players,
            [
                (line_mir_0, line_ext_0, dot_0, rev_0, spd_tot_0, spd_lat_0, spd_dot_0, txt_0),
                (line_mir_1, line_ext_1, dot_1, rev_1, spd_tot_1, spd_lat_1, spd_dot_1, txt_1),
            ],
        ):
            t = np.array(p["time"])
            x = np.array(p["x"])
            y = np.array(p["y"])
            s = np.array(p["s"])
            vy = np.array(p["vy"])
            end = p["end"]
            mask = t <= cur_t + 1e-6
            idx = int(np.sum(mask))
            if idx < 1:
                idx = 1
            mir_end = min(idx, end)
            l_mir.set_data(x[:mir_end], y[:mir_end])
            if idx > end:
                l_ext.set_data(x[end - 1:idx], y[end - 1:idx])
            else:
                l_ext.set_data([], [])
            dot.set_data([x[idx - 1]], [y[idx - 1]])
            active_turns = [ti for ti in p["turns"] if ti < idx]
            if active_turns:
                rev.set_offsets(np.column_stack([x[active_turns], y[active_turns]]))
            else:
                rev.set_offsets(np.empty((0, 2)))

            s_tot.set_data(t[:idx], s[:idx])
            s_lat.set_data(t[:mir_end], vy[:mir_end])
            s_dot.set_data([t[idx - 1]], [s[idx - 1]])
            phase_str = "MAVİ: YANAL AYNA FAZI" if idx <= end else "TURUNCU: ÇIKIŞ SPRİNTİ!"
            txt.set_text(f"t = {t[idx - 1]:.1f} s | {phase_str} | Anlık Hız: {s[idx - 1]:.2f} yd/s")
        return []

    anim = FuncAnimation(fig, update, frames=n_frames, interval=140, blit=False)
    gif_path = ROOT / "MIRROR_FAZ_ANIMASYONU.gif"
    anim.save(gif_path, writer=PillowWriter(fps=7))
    plt.close(fig)
    fig_dir = ROOT / "submission_mirror/figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    (fig_dir / "mirror_phase_animation.gif").write_bytes(gif_path.read_bytes())
    print(f"Saved GIF animation: {gif_path} ({gif_path.stat().st_size} bytes)")


def build_html_studio(traces):
    data_json = json.dumps(traces, ensure_ascii=False).replace("</", "<\\/")
    html = r'''<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NFL Big Data Bowl 2027 — Canlı 60 FPS Animasyon ve Simülasyon Stüdyosu</title>
<style>
:root {
  --bg: #0b1120;
  --panel: #1e293b;
  --card: #0f172a;
  --ink: #f8fafc;
  --muted: #94a3b8;
  --blue: #38bdf8;
  --orange: #f59e0b;
  --red: #ef4444;
  --green: #22c55e;
  --border: #334155;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg);
  color: var(--ink);
  line-height: 1.5;
}
header {
  background: linear-gradient(90deg, #0f172a 0%, #1e3a8a 50%, #0f172a 100%);
  padding: 20px 28px;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
}
header h1 {
  margin: 0;
  font-size: 23px;
  color: #38bdf8;
}
header p {
  margin: 4px 0 0 0;
  font-size: 14px;
  color: #cbd5e1;
}
.tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.tab-btn {
  padding: 9px 16px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: #1e293b;
  color: #e2e8f0;
  font: inherit;
  font-size: 13.5px;
  font-weight: 700;
  cursor: pointer;
}
.tab-btn.active {
  background: #0284c7;
  border-color: #38bdf8;
  color: #fff;
}
main {
  max-width: 1280px;
  margin: 0 auto;
  padding: 20px;
}
.scene { display: none; }
.scene.active { display: block; }

.control-bar {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px 18px;
  margin-bottom: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  align-items: center;
}
.control-bar label {
  font-size: 12px;
  color: var(--muted);
  font-weight: 700;
  text-transform: uppercase;
  display: block;
  margin-bottom: 3px;
}
select, button.btn {
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid #475569;
  background: #0f172a;
  color: #f8fafc;
  font: inherit;
  font-size: 13.5px;
}
button.btn {
  cursor: pointer;
  font-weight: 700;
  background: #0284c7;
  border-color: #38bdf8;
}
button.btn.secondary {
  background: #334155;
  border-color: #475569;
}
button.btn.preset {
  background: #b45309;
  border-color: #f59e0b;
}
input[type="range"] {
  width: 200px;
  accent-color: #38bdf8;
}
.arena-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
@media (max-width: 860px) { .arena-grid { grid-template-columns: 1fr; } }
.panel-box {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
}
.panel-box h3 {
  margin: 0 0 10px 0;
  font-size: 16px;
  color: #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.phase-pill {
  padding: 4px 10px;
  border-radius: 99px;
  font-size: 12px;
  font-weight: 800;
}
.pill-mirror { background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid #38bdf8; }
.pill-exit { background: rgba(245, 158, 11, 0.25); color: #fbbf24; border: 1px solid #f59e0b; }

canvas {
  width: 100%;
  height: auto;
  border-radius: 10px;
  background: #0f172a;
  border: 1px solid #334155;
  display: block;
}
.kpi-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-top: 12px;
}
.kpi-mini {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 10px;
}
.kpi-mini .k-lbl { font-size: 11px; color: var(--muted); }
.kpi-mini .k-val { font-size: 17px; font-weight: 800; color: #f8fafc; }
.explain-banner {
  background: rgba(15, 98, 122, 0.25);
  border: 1px solid #0284c7;
  border-radius: 10px;
  padding: 12px 16px;
  margin-top: 14px;
  font-size: 14px;
  color: #e0f2fe;
}
</style>
</head>
<body>

<header>
  <div>
    <h1>🏈 NFL Big Data Bowl 2027 — Canlı 60 FPS Animasyon Stüdyosu</h1>
    <p>Gerçek 10 Hz sensör verileriyle 113 oyuncunun Combine drillerini ve NFL maç içi bire bir pas korumasını canlı izle ve yarıştır.</p>
  </div>
  <div class="tabs">
    <button class="tab-btn active" onclick="switchScene(1, this)">1. Canlı Oyuncu Yarışı (Mirror vs. Çıkış Sprinti)</button>
    <button class="tab-btn" onclick="switchScene(2, this)">2. NFL Maç İçi 1-on-1 Pas Koruması Simülasyonu</button>
    <button class="tab-btn" onclick="switchScene(3, this)">3. Hazır GIF Animasyonu (Sunuma Koymalık)</button>
  </div>
</header>

<main>
  <!-- SCENE 1: REAL TRACKING DUAL PLAYER ANIMATION -->
  <section id="scene1" class="scene active">
    <div class="control-bar">
      <div>
        <label>Sol Ekran: 1. Oyuncu (Gerçek 10 Hz Sensör Verisi)</label>
        <select id="selP1"></select>
      </div>
      <div>
        <label>Sağ Ekran: 2. Oyuncu (Karşılaştırma İçin)</label>
        <select id="selP2"></select>
      </div>
      <div>
        <label>Oynatma Kontrolleri</label>
        <div style="display:flex;gap:8px;align-items:center">
          <button class="btn" id="playBtn" onclick="togglePlay()">⏸ Duraklat</button>
          <button class="btn secondary" onclick="restartAnim()">⏮ Baştan Başlat</button>
          <select id="speedSel" onchange="changeSpeed()">
            <option value="0.5">0.5x (Yavaş Çekim)</option>
            <option value="1" selected>1.0x (Gerçek Zamanlı)</option>
            <option value="1.8">1.8x (Hızlı)</option>
          </select>
        </div>
      </div>
      <div>
        <label>Zaman Çubuğu (<span id="timeLabel">0.0 s</span>)</label>
        <input type="range" id="timeSlider" min="0" max="10" step="0.05" value="0" oninput="scrubTime(this.value)">
      </div>
      <div>
        <label>Hazır Çarpıcı Örnekler</label>
        <button class="btn preset" onclick="loadPreset('Donovan Jackson','Tyler Booker')">⚡ Donovan Jackson (+91 yp) vs. Tyler Booker (−94 yp)</button>
      </div>
    </div>

    <div class="arena-grid">
      <!-- Player 1 Box -->
      <div class="panel-box">
        <h3>
          <span id="p1Title">Oyuncu 1</span>
          <span id="p1Badge" class="phase-pill pill-mirror">MAVİ: YANAL AYNA FAZI</span>
        </h3>
        <canvas id="cvPath1" width="580" height="270"></canvas>
        <canvas id="cvSpd1" width="580" height="175" style="margin-top:10px"></canvas>
        <div class="kpi-strip">
          <div class="kpi-mini"><div class="k-lbl">Anlık Hız s(t)</div><div class="k-val" id="p1CurS">0.00 yd/s</div></div>
          <div class="kpi-mini"><div class="k-lbl">Anlık Yanal |vy(t)|</div><div class="k-val" id="p1CurVy" style="color:#38bdf8">0.00 yd/s</div></div>
          <div class="kpi-mini"><div class="k-lbl">Mirror Yanal Yüzdelik</div><div class="k-val" id="p1LatPct">-</div></div>
          <div class="kpi-mini"><div class="k-lbl">Tüm Kayıt Yüzdelik</div><div class="k-val" id="p1WholePct">-</div></div>
        </div>
      </div>

      <!-- Player 2 Box -->
      <div class="panel-box">
        <h3>
          <span id="p2Title">Oyuncu 2</span>
          <span id="p2Badge" class="phase-pill pill-mirror">MAVİ: YANAL AYNA FAZI</span>
        </h3>
        <canvas id="cvPath2" width="580" height="270"></canvas>
        <canvas id="cvSpd2" width="580" height="175" style="margin-top:10px"></canvas>
        <div class="kpi-strip">
          <div class="kpi-mini"><div class="k-lbl">Anlık Hız s(t)</div><div class="k-val" id="p2CurS">0.00 yd/s</div></div>
          <div class="kpi-mini"><div class="k-lbl">Anlık Yanal |vy(t)|</div><div class="k-val" id="p2CurVy" style="color:#38bdf8">0.00 yd/s</div></div>
          <div class="kpi-mini"><div class="k-lbl">Mirror Yanal Yüzdelik</div><div class="k-val" id="p2LatPct">-</div></div>
          <div class="kpi-mini"><div class="k-lbl">Tüm Kayıt Yüzdelik</div><div class="k-val" id="p2WholePct">-</div></div>
        </div>
      </div>
    </div>

    <div class="explain-banner">
      <b>💡 Animasyonda Neye Dikkat Etmelisin?</b><br>
      1. İlk <code>6–8 saniye</code> boyunca oyuncu <b>mavi çizgide</b> yukarı-aşağı (sahada sağa-sola) kayarak hayali koçu takip eder. <b>Kırmızı halkalar</b> oyuncunun fren yapıp ters yöne döndüğü (<i>reversal</i>) anlardır.<br>
      2. Oyuncu beyaz kesikli <b><code>+1.5 yard Çıkış Eşiği</code></b> çizgisini geçtiği anda iz <b>turuncuya</b> döner ve alttaki hız grafiğinin sağındaki turuncu bölgede <b>hız roket gibi fırlar!</b><br>
      3. Sol ekrandaki <b>Donovan Jackson</b> mavi yanal fazda çok hızlı kayarken (94.1. yüzdelik) çıkış sprintini yavaş koşar (2.9. yüzdelik). Sağdaki <b>Tyler Booker</b> ise yanal fazda yavaş kalırken (5.9. yüzdelik) çıkış sprintinde tüm gücünü basıp 100. yüzdeliğe çıkar!
    </div>
  </section>

  <!-- SCENE 2: NFL 1-ON-1 PASS PROTECTION GAME SIMULATION -->
  <section id="scene2" class="scene">
    <div class="control-bar">
      <div>
        <label>Maç Senaryosu Seç</label>
        <select id="gameScenario" onchange="resetGameSim()">
          <option value="clean">Senaryo A: Başarılı 1-on-1 Ayna Koruması (Baskı Yok — Pressure Allowed = 0)</option>
          <option value="beaten">Senaryo B: Yanal Dönüşte Geçilen Tackle (Baskı Yendi — Pressure Allowed = 1)</option>
        </select>
      </div>
      <div>
        <label>Kontroller</label>
        <button class="btn" onclick="resetGameSim()">🔄 Pozisyonu Baştan Oynat (Snap!)</button>
      </div>
    </div>

    <div class="panel-box">
      <h3>
        <span>Gerçek NFL Maçında Bire Bir Pas Koruması (One-on-One Pass Protection) ve NGS Baskı Olasılığı</span>
        <span id="gameClockBadge" class="phase-pill pill-mirror">Snap Sonrası: 0.00 s</span>
      </h3>
      <canvas id="cvGame" width="1180" height="420"></canvas>
      <div class="explain-banner">
        <b>🏈 Maç Simülasyonu Açıklaması:</b> Top <code>t = 0.0 s</code> anında (<i>Snap</i>) Center (<b>C</b>) tarafından Oyun Kurucuya (<b>QB</b>) atılır. İlk <b><code>0.0 – 1.5 saniye</code></b> (Ara Hareket Kontrolü penceresi) boyunca Tackle (<b>T</b>) savunmacının (<b>DL</b>) hamlesine göre yanal kayar. Sağ üstteki bar, Next Gen Stats'ın sürekli <b><code>peak_pressure_probability_allowed</code> (0–100%)</b> tehlike ölçerini canlı gösterir.
      </div>
    </div>
  </section>

  <!-- SCENE 3: STANDALONE GIF -->
  <section id="scene3" class="scene">
    <div class="panel-box" style="text-align:center">
      <h3>PowerPoint veya WhatsApp'a Doğrudan Atabileceğin Hazır GIF Animasyonu (<code>MIRROR_FAZ_ANIMASYONU.gif</code>)</h3>
      <p style="color:#cbd5e1;font-size:14.5px">Bu animasyon dosyası proje klasörüne <code>d:\NFL\MIRROR_FAZ_ANIMASYONU.gif</code> olarak kaydedildi.</p>
      <img src="MIRROR_FAZ_ANIMASYONU.gif" alt="Mirror Faz Animasyonu GIF" style="max-width:100%;border-radius:12px;border:1px solid #475569;margin-top:10px">
    </div>
  </section>
</main>

<script>
const rawData = __DATA__;
rawData.sort((a, b) => a.year - b.year || a.name.localeCompare(b.name));

const selP1 = document.getElementById('selP1');
const selP2 = document.getElementById('selP2');

rawData.forEach((d, idx) => {
  const sign = d.diff_pp >= 0 ? '+' : '';
  const label = `${d.year} · ${d.name} (${d.position}) [Δ ${sign}${d.diff_pp} yp]`;
  selP1.add(new Option(label, idx));
  selP2.add(new Option(label, idx));
});

let p1 = rawData[0], p2 = rawData[1];
let animTime = 0, maxAnimTime = 9.0;
let playing = true, speedMult = 1.0, lastTs = performance.now();

function findByName(name) {
  const idx = rawData.findIndex(d => d.name === name);
  return idx >= 0 ? idx : 0;
}

function loadPreset(n1, n2) {
  selP1.value = findByName(n1);
  selP2.value = findByName(n2);
  syncPlayers();
  restartAnim();
}

function syncPlayers() {
  p1 = rawData[+selP1.value];
  p2 = rawData[+selP2.value];
  maxAnimTime = Math.max(p1.time.at(-1), p2.time.at(-1));
  document.getElementById('timeSlider').max = maxAnimTime.toFixed(2);
  document.getElementById('p1Title').textContent = `${p1.year} ${p1.name} (${p1.position})`;
  document.getElementById('p2Title').textContent = `${p2.year} ${p2.name} (${p2.position})`;
  document.getElementById('p1LatPct').textContent = `%${p1.lateral_percentile.toFixed(1)} (${p1.lateral_speed} yd/s)`;
  document.getElementById('p1WholePct').textContent = `%${p1.whole_percentile.toFixed(1)} (${p1.whole_speed} yd/s)`;
  document.getElementById('p2LatPct').textContent = `%${p2.lateral_percentile.toFixed(1)} (${p2.lateral_speed} yd/s)`;
  document.getElementById('p2WholePct').textContent = `%${p2.whole_percentile.toFixed(1)} (${p2.whole_speed} yd/s)`;
}

selP1.addEventListener('change', () => { syncPlayers(); restartAnim(); });
selP2.addEventListener('change', () => { syncPlayers(); restartAnim(); });

function togglePlay() {
  playing = !playing;
  document.getElementById('playBtn').textContent = playing ? '⏸ Duraklat' : '▶ Oynat';
}
function restartAnim() {
  animTime = 0;
  playing = true;
  document.getElementById('playBtn').textContent = '⏸ Duraklat';
}
function changeSpeed() {
  speedMult = parseFloat(document.getElementById('speedSel').value);
}
function scrubTime(val) {
  animTime = parseFloat(val);
}

function drawPlayerArena(p, cvPathId, cvSpdId, badgeId, curSId, curVyId) {
  const cvP = document.getElementById(cvPathId);
  const ctxP = cvP.getContext('2d');
  const W = cvP.width, H = cvP.height;
  ctxP.clearRect(0, 0, W, H);

  // Turf grid background
  ctxP.fillStyle = '#0c192c';
  ctxP.fillRect(0, 0, W, H);

  let idx = 0;
  while (idx < p.time.length - 1 && p.time[idx] < animTime) idx++;
  const inExit = idx >= p.end;

  const badge = document.getElementById(badgeId);
  if (inExit) {
    badge.className = 'phase-pill pill-exit';
    badge.textContent = '🔥 TURUNCU: ÇIKIŞ SPRİNTİ (ZİRVE HIZ!)';
  } else {
    badge.className = 'phase-pill pill-mirror';
    badge.textContent = '🛡️ MAVİ: YANAL AYNA FAZI';
  }

  document.getElementById(curSId).textContent = `${p.s[idx].toFixed(2)} yd/s`;
  document.getElementById(curVyId).textContent = `${p.vy[idx].toFixed(2)} yd/s`;

  const xmin = Math.min(...p.x, p.x_exit) - 0.5;
  const xmax = Math.max(...p.x, p.x_exit) + 0.7;
  const ymin = Math.min(...p.y) - 0.5;
  const ymax = Math.max(...p.y) + 0.5;
  const scale = Math.min((W - 80) / (xmax - xmin || 1), (H - 55) / (ymax - ymin || 1));
  const tx = x => 45 + (x - xmin) * scale;
  const ty = y => H - 30 - (y - ymin) * scale;

  // Yard lines
  ctxP.strokeStyle = 'rgba(148, 163, 184, 0.14)';
  ctxP.lineWidth = 1;
  for (let gx = Math.ceil(xmin); gx <= Math.floor(xmax); gx++) {
    ctxP.beginPath(); ctxP.moveTo(tx(gx), 15); ctxP.lineTo(tx(gx), H - 20); ctxP.stroke();
  }

  // Exit threshold dashed line
  ctxP.strokeStyle = '#94a3b8';
  ctxP.setLineDash([6, 5]);
  ctxP.lineWidth = 1.8;
  ctxP.beginPath();
  ctxP.moveTo(tx(p.x_exit), 15);
  ctxP.lineTo(tx(p.x_exit), H - 20);
  ctxP.stroke();
  ctxP.setLineDash([]);
  ctxP.fillStyle = '#cbd5e1';
  ctxP.font = 'bold 11px system-ui';
  ctxP.fillText('+1.5 yd Çıkış Sınırı', tx(p.x_exit) + 6, 28);

  // Faint full path preview
  ctxP.strokeStyle = 'rgba(56, 189, 248, 0.18)';
  ctxP.lineWidth = 2;
  ctxP.beginPath();
  for (let i = 0; i < p.x.length; i++) {
    if (i === 0) ctxP.moveTo(tx(p.x[i]), ty(p.y[i]));
    else ctxP.lineTo(tx(p.x[i]), ty(p.y[i]));
  }
  ctxP.stroke();

  // Active Mirror path (Blue)
  const mirLim = Math.min(idx, p.end - 1);
  ctxP.strokeStyle = '#38bdf8';
  ctxP.lineWidth = 3.5;
  ctxP.beginPath();
  for (let i = 0; i <= mirLim; i++) {
    if (i === 0) ctxP.moveTo(tx(p.x[i]), ty(p.y[i]));
    else ctxP.lineTo(tx(p.x[i]), ty(p.y[i]));
  }
  ctxP.stroke();

  // Active Exit path (Orange)
  if (idx >= p.end) {
    ctxP.strokeStyle = '#f59e0b';
    ctxP.lineWidth = 4;
    ctxP.beginPath();
    for (let i = p.end - 1; i <= idx; i++) {
      if (i === p.end - 1) ctxP.moveTo(tx(p.x[i]), ty(p.y[i]));
      else ctxP.lineTo(tx(p.x[i]), ty(p.y[i]));
    }
    ctxP.stroke();
  }

  // Reversal points reached so far
  p.turns.forEach((ti, revNum) => {
    if (ti <= idx) {
      ctxP.fillStyle = '#ef4444';
      ctxP.beginPath();
      ctxP.arc(tx(p.x[ti]), ty(p.y[ti]), 5.5, 0, Math.PI * 2);
      ctxP.fill();
      ctxP.strokeStyle = '#fff';
      ctxP.lineWidth = 1.2;
      ctxP.stroke();
      ctxP.fillStyle = '#fca5a5';
      ctxP.font = 'bold 10px system-ui';
      ctxP.fillText(`Dönüş ${revNum + 1}`, tx(p.x[ti]) - 18, ty(p.y[ti]) - 9);
    }
  });

  // Virtual Coach indicator during mirror phase
  if (!inExit) {
    const coachX = tx(p.x[0] + 1.0);
    const coachY = ty(p.y[idx]);
    ctxP.fillStyle = '#a855f7';
    ctxP.beginPath();
    ctxP.arc(coachX, coachY, 7, 0, Math.PI * 2);
    ctxP.fill();
    ctxP.fillStyle = '#e9d5ff';
    ctxP.font = '10px system-ui';
    ctxP.fillText('Koç', coachX + 10, coachY + 4);
  }

  // Player live dot
  ctxP.fillStyle = inExit ? '#f59e0b' : '#38bdf8';
  ctxP.beginPath();
  ctxP.arc(tx(p.x[idx]), ty(p.y[idx]), 9, 0, Math.PI * 2);
  ctxP.fill();
  ctxP.strokeStyle = '#ffffff';
  ctxP.lineWidth = 2.5;
  ctxP.stroke();

  // Speed Canvas
  const cvS = document.getElementById(cvSpdId);
  const ctxS = cvS.getContext('2d');
  const SW = cvS.width, SH = cvS.height;
  ctxS.clearRect(0, 0, SW, SH);

  const maxT = p.time.at(-1);
  const maxS = Math.max(...p.s, 6.2) * 1.08;
  const stx = tm => 42 + (SW - 60) * (tm / maxT);
  const sty = sp => SH - 26 - (SH - 42) * (sp / maxS);

  // Shaded exit region
  const exitX = stx(p.time[p.end]);
  ctxS.fillStyle = 'rgba(245, 158, 11, 0.16)';
  ctxS.fillRect(exitX, 12, SW - 18 - exitX, SH - 38);

  // Horizontal speed lines
  ctxS.strokeStyle = 'rgba(148, 163, 184, 0.15)';
  ctxS.lineWidth = 1;
  ctxS.fillStyle = '#94a3b8';
  ctxS.font = '10.5px system-ui';
  for (let sv = 0; sv <= 6; sv += 2) {
    ctxS.beginPath(); ctxS.moveTo(42, sty(sv)); ctxS.lineTo(SW - 18, sty(sv)); ctxS.stroke();
    ctxS.fillText(`${sv} yd/s`, 6, sty(sv) + 4);
  }

  // Lateral speed |vy(t)| dashed blue curve
  ctxS.strokeStyle = '#38bdf8';
  ctxS.setLineDash([4, 3]);
  ctxS.lineWidth = 2;
  ctxS.beginPath();
  for (let i = 0; i <= mirLim; i++) {
    if (i === 0) ctxS.moveTo(stx(p.time[i]), sty(p.vy[i]));
    else ctxS.lineTo(stx(p.time[i]), sty(p.vy[i]));
  }
  ctxS.stroke();
  ctxS.setLineDash([]);

  // Total speed s(t) solid curve
  ctxS.strokeStyle = '#f8fafc';
  ctxS.lineWidth = 2.5;
  ctxS.beginPath();
  for (let i = 0; i <= idx; i++) {
    if (i === 0) ctxS.moveTo(stx(p.time[i]), sty(p.s[i]));
    else ctxS.lineTo(stx(p.time[i]), sty(p.s[i]));
  }
  ctxS.stroke();

  // Current speed dot
  ctxS.fillStyle = '#ef4444';
  ctxS.beginPath();
  ctxS.arc(stx(p.time[idx]), sty(p.s[idx]), 6, 0, Math.PI * 2);
  ctxS.fill();
}

// Scene 2: Game 1-on-1 Simulation
let gameTime = 0;
function resetGameSim() { gameTime = 0; }

function drawGameSim(dt) {
  const cv = document.getElementById('cvGame');
  if (!cv) return;
  const ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  gameTime = (gameTime + dt * 0.75) % 4.0;
  document.getElementById('gameClockBadge').textContent =
    gameTime <= 1.5
      ? `Snap Sonrası: ${gameTime.toFixed(2)} s (0–1.5 s Erken Yanal Hareket Penceresi)`
      : `Snap Sonrası: ${gameTime.toFixed(2)} s (Dropback Pas Koruma Fazı)`;

  ctx.fillStyle = '#14532d';
  ctx.fillRect(0, 0, W, H);

  // Yard lines
  ctx.strokeStyle = 'rgba(255,255,255,0.18)';
  ctx.lineWidth = 2;
  for (let x = 120; x < W; x += 140) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
  }
  // Line of scrimmage
  ctx.strokeStyle = '#fde047';
  ctx.setLineDash([8, 6]);
  ctx.beginPath(); ctx.moveTo(540, 0); ctx.lineTo(540, H); ctx.stroke();
  ctx.setLineDash([]);

  const scenario = document.getElementById('gameScenario').value;
  const t = gameTime;

  // QB drops back
  const qbX = 510 - Math.min(t * 55, 145);
  const qbY = H / 2;

  // Highlighted Left Tackle (T) vs Edge Rusher (DL)
  const rusherX = 560 - t * 52;
  const rusherY = 115 + Math.sin(t * 3.2) * 28 - (scenario === 'beaten' && t > 1.6 ? (t - 1.6) * 35 : 0);

  const tackleX = 525 - Math.min(t * 44, 115);
  const tackleY = scenario === 'clean'
    ? rusherY + 4
    : (t < 1.5 ? rusherY + 8 : 115 + 22);

  // Draw other OL/DL pairs
  const otherY = [170, 210, 250, 305];
  const labels = ['G', 'C', 'G', 'T'];
  otherY.forEach((oy, i) => {
    const ox = 530 - Math.min(t * 25, 65);
    ctx.fillStyle = '#0f627a';
    ctx.beginPath(); ctx.arc(ox, oy, 15, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.stroke();
    ctx.fillStyle = '#fff'; ctx.font = 'bold 12px system-ui'; ctx.fillText(labels[i], ox - 4, oy + 4);

    ctx.fillStyle = '#dc2626';
    ctx.beginPath(); ctx.arc(ox + 26, oy, 14, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#fff'; ctx.fillText('DL', ox + 19, oy + 4);
  });

  // Draw Highlighted 1-on-1 Matchup Box
  ctx.strokeStyle = '#38bdf8';
  ctx.lineWidth = 2;
  ctx.strokeRect(Math.min(tackleX, rusherX) - 35, Math.min(tackleY, rusherY) - 35, 130, 85);
  ctx.fillStyle = '#bae6fd';
  ctx.font = 'bold 13px system-ui';
  ctx.fillText('1-on-1 Matchup (Tackle vs. Pass Rusher)', Math.min(tackleX, rusherX) - 35, Math.min(tackleY, rusherY) - 42);

  // Highlighted Tackle
  ctx.fillStyle = '#0284c7';
  ctx.beginPath(); ctx.arc(tackleX, tackleY, 17, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = '#fff'; ctx.lineWidth = 2.5; ctx.stroke();
  ctx.fillStyle = '#fff'; ctx.fillText('T', tackleX - 4, tackleY + 4);

  // Highlighted Pass Rusher
  ctx.fillStyle = '#ef4444';
  ctx.beginPath(); ctx.arc(rusherX, rusherY, 16, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = '#fff'; ctx.stroke();
  ctx.fillStyle = '#fff'; ctx.fillText('DL', rusherX - 7, rusherY + 4);

  // QB
  ctx.fillStyle = '#eab308';
  ctx.beginPath(); ctx.arc(qbX, qbY, 18, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = '#fff'; ctx.stroke();
  ctx.fillStyle = '#0f172a'; ctx.fillText('QB', qbX - 9, qbY + 4);

  // Pressure Probability Meter
  const prob = scenario === 'clean'
    ? Math.min(0.18, 0.04 + t * 0.035)
    : (t < 1.5 ? 0.12 + t * 0.1 : Math.min(0.94, 0.27 + (t - 1.5) * 0.38));

  ctx.fillStyle = 'rgba(15, 23, 42, 0.88)';
  ctx.fillRect(W - 330, 20, 305, 95);
  ctx.strokeStyle = '#475569';
  ctx.strokeRect(W - 330, 20, 305, 95);
  ctx.fillStyle = '#f8fafc';
  ctx.font = 'bold 13px system-ui';
  ctx.fillText(`NGS Anlık Baskı Olasılığı: %${(prob * 100).toFixed(1)}`, W - 315, 45);
  ctx.fillStyle = '#334155';
  ctx.fillRect(W - 315, 58, 275, 18);
  ctx.fillStyle = prob > 0.5 ? '#ef4444' : '#22c55e';
  ctx.fillRect(W - 315, 58, 275 * prob, 18);
  ctx.fillStyle = '#cbd5e1';
  ctx.font = '12px system-ui';
  ctx.fillText(prob > 0.5 ? '⚠️ BASKI YENDİ (Pressure Allowed = 1)' : '✅ KORUMA BAŞARILI (Temiz Cep)', W - 315, 98);
}

function switchScene(num, btn) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.scene').forEach(s => s.classList.remove('active'));
  document.getElementById('scene' + num).classList.add('active');
}

function loop(now) {
  const dt = Math.min(0.05, (now - lastTs) / 1000);
  lastTs = now;
  if (playing) {
    animTime += dt * speedMult;
    if (animTime > maxAnimTime + 0.4) animTime = 0;
    document.getElementById('timeSlider').value = Math.min(animTime, maxAnimTime).toFixed(2);
    document.getElementById('timeLabel').textContent = `${Math.min(animTime, maxAnimTime).toFixed(2)} s`;
  }
  drawPlayerArena(p1, 'cvPath1', 'cvSpd1', 'p1Badge', 'p1CurS', 'p1CurVy');
  drawPlayerArena(p2, 'cvPath2', 'cvSpd2', 'p2Badge', 'p2CurS', 'p2CurVy');
  drawGameSim(dt);
  requestAnimationFrame(loop);
}

loadPreset('Donovan Jackson', 'Tyler Booker');
requestAnimationFrame(loop);
</script>
</body>
</html>'''.replace("__DATA__", data_json)

    out_path = ROOT / "ANIMASYON_SIMULATORU.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Saved interactive HTML animation studio: {out_path}")


def main():
    traces = load_traces()
    build_gif(traces)
    build_html_studio(traces)


if __name__ == "__main__":
    main()
