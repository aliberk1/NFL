# NFL: Oyuncuların gelecekteki başarısını veriden tahmin etmek

Yalnızca NFL Big Data Bowl 2027 yarışma verisi kullanılır (dış veri yok). Bu klasör yarışma
teslim kodundan (`submission*/`, `scripts/`) ve Streamlit uygulamasından (`app/`) bağımsızdır.

- **Ne yapıldı (tam teknik döküm):** [YAPILANLAR.md](YAPILANLAR.md)
- **Ekip için açık görevler:** [GOREVLER.md](GOREVLER.md)
- **Ön kayıt (hipotezler, sonuçlardan önce yazıldı):** [TASARIM.md](TASARIM.md)

## Kurulum

Ham veri `data/nfl-big-data-bowl-2027/` altında olmalı (`.gitignore` gereği depoda yok).

```bash
python3 -m venv .venv-ml
.venv-ml/bin/pip install -r requirements-ml.txt
```

## Çalıştırma (repo kökünden)

| Komut | Görev | Süre (M4, MPS) |
|---|---|---|
| `.venv-ml/bin/python -m nfl.gorev_a` | A: draft öncesi → kalıcı starter (24 model, 4 hedef tanımı) | ~24 dk |
| `.venv-ml/bin/python -m nfl.gorev_a --quick --cnn-epochs 2` | A: hızlı duman testi | ~4 dk |
| `.venv-ml/bin/python -m nfl.ileri_tahmin` | 3 sezonluk gelecek tahmini (2024–2025 sınıfları) | ~3 dk |
| `.venv-ml/bin/python -m nfl.gorev_a2` | A2: sezon başına snap (regresyon) | ~2 dk |
| `.venv-ml/bin/python -m nfl.gorev_b1` | B1: çaylak sezonu → sonraki sezon | ~3 dk |
| `.venv-ml/bin/python -m nfl.gorev_c1` | C1: hareket kaydından rota tanıma (1D-CNN) | ~9 dk |

Her görev `nfl/ciktilar/<görev>/` altına `RAPOR.md`, CSV tabloları ve PNG grafikler yazar.
`ciktilar/cache/` ara dosyaları (dizi önbellekleri) depoya alınmaz; ilk çalıştırmada yeniden üretilir.

## Dosyalar

| Dosya | İçerik |
|---|---|
| `veri.py` | Ham CSV okuma, oyuncu tablosu, hedef değişkenler |
| `ozellikler.py` | Combine özellikleri, combine takip özetleri, CNN için ham diziler |
| `sezon.py` | Oyuncu-sezon özellikleri (`player_play` + maç takip verisi) |
| `modeller.py` | sklearn sınıflandırıcı/regresörler, set-of-sequences 1D-CNN (PyTorch) |
| `degerlendirme.py` | Tekrarlı CV, metrikler, Friedman, Nadeau-Bengio t-testi, Holm, bootstrap |
| `grafikler.py` | Rapor grafikleri (sabit renk sırası) |
| `gorev_a.py`, `ileri_tahmin.py`, `gorev_a2.py`, `gorev_b1.py`, `gorev_c1.py` | Görev betikleri |
