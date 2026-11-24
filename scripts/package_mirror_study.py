"""Package the verified second research candidate without replacing the first."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT / "submission_mirror"
    checks = json.loads((ROOT / "verification/mirror_result.json").read_text(encoding="utf-8"))
    assert checks["status"] == "passed" and checks["notebook_errors"] == 0
    figures = out / "figures"
    figures.mkdir(exist_ok=True)
    for name in ["mirror_phase_story.png", "mirror_ranking_shift.png", "mirror_model_comparison.png", "movement_bridge_results.png"]:
        shutil.copy2(ROOT / "reports/trenches" / name, figures / name)
    shutil.copy2(ROOT / "reports/trenches/mirror_explorer.html", out / "mirror_explorer.html")
    shutil.copy2(ROOT / "verification/mirror_result.json", out / "verification.json")
    text = (out / "writeup_en.md").read_text(encoding="utf-8")
    image_links = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
    assert all((out / p).is_file() for p in image_links)
    assert len(text.split()) < 2000
    page = '''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NFL 2027 — Ana Yarışma Teslim Adayı (OL Combine Faz Doğrulaması)</title><style>body{font:17px/1.68 system-ui,-apple-system,sans-serif;background:#f4f6f8;color:#192b3d;margin:0}
main{max-width:1020px;margin:auto;padding:32px 24px}section{background:white;border:1px solid #dce4ed;border-radius:12px;padding:24px;margin:20px 0;box-shadow:0 1px 3px rgba(0,0,0,.03)}
h1,h2{line-height:1.25}a{color:#126b68}img{max-width:100%;height:auto;border-radius:8px;margin:10px 0}.status{font-weight:600;color:#126b68}.grid{display:flex;gap:24px;flex-wrap:wrap}
.big{font-size:32px;font-weight:700;color:#126b68}small{color:#526477}</style></head><body><main>
<small>NFL BIG DATA BOWL 2027 · ANA YARIŞMA TESLİM ADAYI (FLAGSHIP ENTRY)</small><h1>En Hızlı Kısım Çıkış Sprinti:<br>OL Combine Faz Ayrıştırması ve 4-Aşamalı Doğrulama Hunisi</h1>
<p class="status">Ana teslim adayı (submission_mirror): 3 OL drilinde 470 kayıt, 2-tekrar güvenilirlik sınırı, ikili + sürekli NGS baskı olasılığı modelleri ve iki dilli (TR/EN) etkileşimli inceleyici ile tam doğrulandı.</p>
<section><h2>1. Evrensel Ölçüm Tuzağı (470 / 470 Kayıtta %100 Çıkış Sprinti Baskınlığı)</h2>
<p>Yalnızca <b>Pass-Pro Mirror Drill</b> (113/113) değil, tüm OL ayak işi drillerinde — <b>5-Yard Wave Drill</b> (118/118) ve <b>Pass Rush Drop</b> (239/239) dahil toplam <b>470 kaydın tamamında (%100.0)</b> — en yüksek hız yanal koruma/ayak işi fazında değil, dril sonundaki düz koşu (çıkış sprinti) fazında oluşmaktadır.</p>
<p>Tüm kayıt hızına göre sıralama ile yanal ayna fazı hızına göre sıralama neredeyse diktir (Mirror <b>r = +0.005</b>, Wave <b>r = −0.022</b>, Drop <b>r = +0.147</b>). 2025 sınıfında üst çeyrekteki <b>dokuz oyuncudan yalnız biri ortaktır.</b></p>
<img src="reports/trenches/mirror_phase_story.png" alt="Testin yana hareket ve çıkış sprinti fazları">
<img src="reports/trenches/mirror_ranking_shift.png" alt="Sınıf içi sıralama değişimi ve 3 OL drilinde çıkış sprinti baskınlığı">
<p><a href="reports/trenches/mirror_explorer.html"><b>Etkileşimli TR/EN Oyuncu Faz İnceleyicisini Aç →</b></a></p></section>
<section><h2>2. Tekrar Güvenilirliği ve Maç Performansı Doğrulaması</h2><div class="grid"><div><div class="big">470</div>OL Combine kaydı</div><div><div class="big">50</div>çaylak OL (20.853 snap)</div><div><div class="big">400</div>tam yeniden eğitim</div></div>
<p><b>Neden tek tekrarlı dril metrikleri maç tahmininde sınırlı kalıyor?</b> İkişer kez koşulan <b>Pass Rush Drop</b> drilinde (118 OL çifti) çıkış sprinti hızı <b>r = +0.510</b> tekrar güvenilirliğine sahipken, koç/işaret yönlendirmeli yanal pas seti hızı yalnızca <b>r = +0.104</b> tekrar güvenilirliğine sahiptir (psikometrik zayıflama sınırı).</p>
<p>Hem ikili <code>pressure_allowed</code> (yarı-yarıya maç güvenilirliği r = 0.367) hem de sürekli NGS <code>peak_pressure_probability_allowed</code> (yarı-yarıya maç güvenilirliği <b>r = 0.696</b>) hedeflerinde, çıkış sprintiyle kirlenmiş tüm-kayıt hızı 2025 tahmin hatasını kötüleştirirken, faz ayrıştırmalı mirror özellikleri hatayı küçük miktarda düşürmekte fakat klasik Combine testlerine (40-yard, 10-yard split, kilo, kol boyu) göre istatistiksel olarak anlamlı bir üstünlük sağlamamaktadır (2025 tam yeniden eğitimli %95 GA: <b>[−0.264, +0.353] yüzde puan</b>).</p>
<img src="reports/trenches/mirror_model_comparison.png" alt="Üç hedef tanımında ileri-yıl pas koruma tahmin hataları"></section>
<section><h2>Dosyalar ve Teslim Paketleri</h2><ul><li><a href="submission_mirror/writeup_en.md">Ana İngilizce Yarışma Raporu (submission_mirror/writeup_en.md)</a></li>
<li><a href="submission_mirror/mirror_phase_validation.executed.ipynb">Çalıştırılmış ve Doğrulanmış Kaggle Notebook</a></li>
<li><a href="submission_mirror/mirror_explorer.html">İki Dilli (TR/EN) Etkileşimli Oyuncu Faz İnceleyicisi</a></li>
<li><a href="reports/trenches/README_TR.md">Ayrıntılı Türkçe Teknik Rapor</a></li>
<li><a href="reports/experiment_register.md">Tüm Pozisyonlar (WR/TE/OL/DL/DB) Deney Kayıt Defteri</a></li>
<li><a href="CALISMA_DURUMU.md">Genel Proje Durumu ve Metodolojik Özet</a></li>
<li><a href="NFL_2027_mirror_arastirma_paketi.zip">Tam Teslim Paketi (ZIP)</a></li></ul></section></main></body></html>'''
    (ROOT / "CALISMA_DURUMU.html").write_text(page, encoding="utf-8")
    excluded = {"ol_rookie_plays.csv", "dl_rookie_plays.csv", "ol_early_movement.csv"}
    files = [ROOT / p for p in ["CALISMA_DURUMU.md", "CALISMA_DURUMU.html", "requirements.txt", "requirements-notebook.txt",
                                "reports/experiment_register.md", "verification/mirror_result.json",
                                "submission/receiver_speed_translation.ipynb"]]
    for folder in ["submission_mirror", "reports/trenches", "scripts"]:
        files.extend(p for p in (ROOT / folder).rglob("*") if p.is_file() and p.name not in excluded
                     and p.name != "manifest.json" and "__pycache__" not in p.parts)
    manifest = {"status": "verified local research candidate; not a finalized or published competition entry",
                "writeup_words": len(text.split()), "writeup_images": len(image_links),
                "verification": checks,
                "files": [{"path": p.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                          for p in sorted(files)]}
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    archive = ROOT / "NFL_2027_mirror_arastirma_paketi.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for path in files + [manifest_path]:
            z.write(path, path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    print(json.dumps({"archive": str(archive), "bytes": archive.stat().st_size,
                      "files": len(files) + 1, "writeup_words": len(text.split()), "zip_integrity": "passed"}, indent=2))


if __name__ == "__main__":
    main()
