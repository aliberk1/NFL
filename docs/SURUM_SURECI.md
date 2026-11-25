# Geliştirme ve sürüm süreci

## Geliştirme

Görev alma, dal adı ve inceleme kuralları: [Ekip çalışma düzeni](EKIP_CALISMA_DUZENI.md).

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
ruff check --select E4,E7,E9,F app pipelines tests scripts/measure_player_directory.py
```

PR'larda `dependency-gate`, `tests` ve Docker tatbikatını çalıştıran `container` işleri çalışır.
`requirements-app.txt` değişirse imaj kilidini yenileyin:

```sh
uv pip compile --universal --python-version 3.11 --generate-hashes --no-header requirements-app.txt -o requirements-app.lock
```

## Sürüm yayınlama

1. `CHANGELOG.md` ve `app/api.py` içindeki sürümü güncelleyin.
2. `main` üzerinde CI'ın geçtiğini ve canlı demonun açıldığını doğrulayın.
3. Aşağıdaki temiz kurulumu başka bir ekip üyesi denesin.
4. Lisans ve veri paylaşım kararlarını kontrol edin.
5. `vX.Y.Z` etiketiyle GitHub Release yayınlayın; notlara değişiklikleri ve bilinen sınırları ekleyin.

## Temiz kurulum kontrolü

Geliştirme ortamı olmayan bir klasörde, Python 3.11 ve PowerShell ile:

```powershell
git clone https://github.com/aliberk1/NFL.git nfl-temiz
cd nfl-temiz
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
$env:NFL_DB_PATH = "data/demo/nfl.duckdb"
.\.venv\Scripts\python.exe -m pipelines.demo_data
.\.venv\Scripts\python.exe -m streamlit run app/ui.py --server.address 127.0.0.1
```

Beklenen: testler geçer, demo uyarısı görünür, 48 oyuncu listelenir ve seçilen oyuncunun profili açılır.

| Tarih | Deneyen | Commit | Sistem | Sonuç |
| --- | --- | --- | --- | --- |
| — | Başka bir ekip üyesi | — | — | Bekliyor |
