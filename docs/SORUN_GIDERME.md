# Kurulum sorun giderme

| Belirti | Neden | Çözüm |
| --- | --- | --- |
| `No module named duckdb` / `streamlit` | Bağımlılıklar başka bir Python'a kurulu | Komutları `.\.venv\Scripts\python.exe -m ...` biçiminde çalıştırın |
| `Eksik kaynak: ...csv` | Yarışma CSV'leri yerinde değil | Beş dosyayı `data/nfl-big-data-bowl-2027/` içine koyun veya kurgusal demoyu kullanın |
| `Veri doğrulaması başarısız` | Şema, anahtar veya boş değer hatası | `data/curated/quality_report.json` dosyasındaki `errors` alanına bakın; eski veritabanı korunur |
| Yalnızca Araştırma sekmesi görünüyor | DuckDB oluşturulmamış | `python -m pipelines.ingest` veya demo adımlarını çalıştırın |
| `... demo veritabanı değil; üzerine yazılmadı` | `NFL_DB_PATH` gerçek veriyi gösteriyor | Demo için ayrı bir yol verin: `data/demo/nfl.duckdb` |
| Gerçek veri yerine demo açılıyor | `NFL_DB_PATH` o terminalde tanımlı | `Remove-Item Env:NFL_DB_PATH`, sonra uygulamayı yeniden başlatın |
| DuckDB "file is being used" | Uygulama açıkken yeniden yükleme | Streamlit/API'yi durdurup yeniden deneyin |
| Port 8501 kullanımda | Başka bir Streamlit açık | `--server.port 8502` ekleyin |
| Sohbet yapılandırılmamış | Anahtar veya model tanımlı değil | Ortam değişkenlerini aynı terminalde tanımlayın; Docker dışında `.env` otomatik okunmaz |
| Sağlayıcı `max_tokens` alanını reddediyor | Model diğer alan adını bekliyor | `NFL_LLM_MAX_TOKENS_FIELD=max_completion_tokens` |
| `Çok sık soru` / `Günlük ... sınırı` | Kullanım sınırı | Bekleyin veya [sınır ayarlarına](DEMO_VE_YAYIN.md#sohbet-gizli-anahtarlar-ve-sınırlar) bakın |
| `SHA-256 özetiyle eşleşmiyor` | Araştırma dosyası manifestten farklı | Yerel değişikliği geri alın veya temiz klon kullanın |
| `docker: command not found` | Docker kurulu değil | Docker Desktop kurun veya Docker'sız demoyu kullanın |
| Konteyner `unhealthy` | Veritabanı veya HTTP hatası | `docker compose logs --tail 50` |
| Canlı demo ilk açılışta bekliyor | Ücretsiz sunucu uyumuş | Yaklaşık bir dakika bekleyin |

Sorun bildirirken çalıştırılan komutu, hata metnini, Python ve işletim sistemi sürümünü ekleyin.
API anahtarı veya ham veri paylaşmayın.
