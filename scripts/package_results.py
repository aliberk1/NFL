"""Assemble verified local deliverables, without including raw competition data."""
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    submission = ROOT / "submission"
    verified = ROOT / "verification/notebook_run"
    check = json.loads((ROOT / "verification/result.json").read_text(encoding="utf-8"))
    assert check["status"] == "passed" and check["notebook_errors"] == 0
    figures = submission / "figures"
    figures.mkdir(exist_ok=True)
    for name in ["combine_repeatability.png", "speed_transfer_results.png"]:
        shutil.copy2(verified / "reports/speed_study" / name, figures / name)
    # Refresh QA outputs with the more complete, independently verified extraction.
    for name in ["extraction_audit.json", "game_rejected.csv"]:
        shutil.copy2(verified / "reports/speed_study" / name, ROOT / "reports/speed_study" / name)
    shutil.copy2(verified / "data/processed/combine_speed_attempts.csv",
                 ROOT / "data/processed/combine_speed_attempts.csv")
    shutil.copy2(ROOT / "verification/result.json", submission / "verification.json")
    writeup = (submission / "writeup_en.md").read_text(encoding="utf-8")
    references = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", writeup)
    assert all((submission / reference).is_file() for reference in references)
    assert len(writeup.split()) <= 2000

    summary = json.loads((ROOT / "reports/speed_study/summary.json").read_text(encoding="utf-8"))
    rows = "".join(f"<tr><td>{r['test_year']}</td><td>{r['test_players']}</td>"
                   f"<td>{r['traditional_mae']:.4f}</td><td>{r['with_tracking_mae']:.4f}</td>"
                   f"<td>{'İyileşti' if r['movement_mae_improvement'] > 0 else 'Kötüleşti'}</td></tr>"
                   for r in summary["scores"])
    page = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>NFL 2027 — Analiz Sonucu</title>
<style>body{{font:17px/1.65 system-ui,sans-serif;background:#f5f7fa;color:#172638;margin:0}}
main{{max-width:1000px;margin:auto;padding:36px 24px}}h1,h2{{line-height:1.2}}h1{{font-size:38px}}
.lead{{font-size:22px}}.box{{background:white;border:1px solid #dce4ed;border-radius:12px;padding:24px;margin:22px 0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:16px}}
.metric{{font-size:32px;font-weight:700;color:#126b68}}small{{color:#53677d}}img{{max-width:100%;height:auto}}
table{{border-collapse:collapse;width:100%}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #dce4ed}}
a{{color:#126b68}}.status{{color:#126b68;font-weight:650}}code{{font-size:14px}}</style></head><body><main>
<small>NFL BIG DATA BOWL 2027 · YEREL ANALİZ VE TESLİM TASLAĞI</small>
<h1>Hız ilişkisi var.<br>Ek tahmin faydası henüz tutarlı değil.</h1>
<p class="lead">Combine'daki yüksek koşu hızı maçtaki rota hızıyla ilişkili çıktı.
Ancak klasik 40-yard süresi, boy ve kilo modeline eklenen sensör özellikleri iki test yılında aynı avantajı sağlamadı.</p>
<div class="grid"><div class="box"><div class="metric">58</div>analiz edilen pas yakalayıcı</div>
<div class="box"><div class="metric">10.944</div>uygun çaylak maç kaydı</div>
<div class="box"><div class="metric">22,65 milyon</div>taranan takip satırı</div></div>
<section class="box"><h2>Ölçümün tutarlılığı ile tahmin gücü farklı şeyler</h2>
<ul><li>İki Combine denemesi arasında yüksek hız korelasyonu: <b>0,89</b> (81 oyuncu).</li>
<li>Bizim erken hız ölçümümüzün tekrar korelasyonu: <b>0,15</b>.</li>
<li>Combine yüksek hızı ile maçtaki rota hızı korelasyonu: <b>0,38</b> (58 oyuncu).</li></ul>
<img src="submission/figures/combine_repeatability.png" alt="Yüksek hız ve erken hız ölçümlerinin tekrar denemeleri karşılaştırması">
<p>Erken hız ölçümü yaklaşık bir başlangıç anına dayanıyor; resmi hızlanma testi olarak yorumlanmamalı.</p></section>
<section class="box"><h2>Sonraki yılı tahmin etme testi</h2>
<table><thead><tr><th>Test yılı</th><th>Oyuncu</th><th>Klasik model</th><th>+ Sensör</th><th>MAE sonucu</th></tr></thead>
<tbody>{rows}</tbody></table><p>Hata düşükse model daha iyi. 2024'te yaklaşık %15 iyileşme,
2025'te yaklaşık %3 kötüleşme var. Her iki farkın belirsizlik aralığı sıfırı içeriyor.</p>
<img src="submission/figures/speed_transfer_results.png" alt="Combine-maç hız ilişkisi ve ileri yıl tahmin hataları">
<p><b>Sonuç:</b> Bu verilerle yeni bir oyuncu sıralaması veya klasik testlerden kesin üstün bir model önermiyoruz.</p></section>
<section class="box"><h2>Dosyalar hazır</h2><ul>
<li><a href="SONUC.md">Ayrıntılı Türkçe sonuç</a></li>
<li><a href="submission/writeup_en.md">İngilizce yarışma yazısı</a> · {len(writeup.split())} kelime</li>
<li><a href="submission/receiver_speed_translation.executed.ipynb">Çıktılarıyla notebook</a></li>
<li><a href="submission/receiver_speed_translation.ipynb">Temiz notebook</a></li>
<li><a href="submission/README_TR.md">Kaggle'a taşıma adımları</a></li>
<li><a href="reports/experiment_register.md">Olumlu ve olumsuz bütün denemeler</a></li>
<li><a href="NFL_2027_teslim_paketi.zip">Teslim paketi ZIP</a></li></ul>
<p class="status">Yerel doğrulama geçti: {check['executed_code_cells']} kod hücresi,
{len(check['comparison_checks'])} çıktı karşılaştırması, sıfır notebook hatası.</p>
<p>Kaggle'a yükleme yapılmadı. Çalışma keşifseldir; bir yarışma derecesi veya gelecekteki başarı garantisi değildir.</p></section>
</main></body></html>"""
    (ROOT / "SONUC.html").write_text(page, encoding="utf-8")
    files = [ROOT / p for p in ["SONUC.md", "SONUC.html", "requirements.txt", "requirements-notebook.txt"]]
    files += [p for directory in ["submission", "scripts", "reports"]
              for p in (ROOT / directory).rglob("*") if p.is_file() and "__pycache__" not in p.parts
              and p.name != "manifest.json"]
    manifest = {
        "status": "locally verified; not submitted to Kaggle",
        "writeup_words_whitespace": len(writeup.split()), "writeup_figures": len(references),
        "writeup_result_tables": 1, "verification": check,
        "inputs": [{"file": p.name, "bytes": p.stat().st_size}
                   for p in sorted((ROOT / "data/nfl-big-data-bowl-2027").glob("*.csv"))],
        "artifacts": [{"file": p.relative_to(ROOT).as_posix(),
                       "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)],
    }
    manifest_path = submission / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    archive = ROOT / "NFL_2027_teslim_paketi.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in files + [manifest_path]:
            z.write(p, p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert "submission/receiver_speed_translation.executed.ipynb" in z.namelist()
    print(json.dumps({"archive": str(archive), "files": len(files) + 1,
                      "bytes": archive.stat().st_size, "writeup_words": len(writeup.split()),
                      "image_links_valid": True, "zip_integrity": "passed"}, indent=2))


if __name__ == "__main__":
    main()
