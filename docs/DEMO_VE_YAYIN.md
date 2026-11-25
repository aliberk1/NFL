# Docker, demo ve yayın rehberi

## Tek komutla başlatma

Docker (Compose v2) kurulu bir bilgisayarda, depo klasöründe:

```sh
docker compose up --build -d --wait
```

- Arayüz: http://127.0.0.1:8501
- API: http://127.0.0.1:8000/docs (yalnızca bu bilgisayardan erişilir)

Ham yarışma verisi veya LLM anahtarı gerekmez. Durdurmak için `docker compose down`.
`-v` eklemek veri hacmini ve içindeki yedekleri siler.

## Demo verisi

`pipelines/demo_data.py` 48 kurgusal oyuncu ve 16 kurgusal maç üretir. Oyuncu adları
"Kurgusal Oyuncu NN", takımlar "DEMO-A" … "DEMO-D" biçimindedir. Değerler sabit tohumlu
rastgele üretilir; NFL veya yarışma verisinden örneklenmez ya da ona uydurulmaz. Sonuçları
futbol bilgisi olarak yorumlamayın. Arayüz, API yanıtları ve sohbet kaynak satırı verinin
kurgusal olduğunu belirtir. Demo olmayan bir veritabanının üzerine yazılmaz.

Docker'sız denemek için (PowerShell):

```powershell
$env:NFL_DB_PATH = "data/demo/nfl.duckdb"
python -m pipelines.demo_data
python -m streamlit run app/ui.py
```

## Sohbet, gizli anahtarlar ve sınırlar

Anahtar yoksa sohbet kapalıdır ve maliyet oluşmaz. Yerelde anahtarı kabuk ortamında veya Git'in
yok saydığı `.env` dosyasında tanımlayın; barındırmada sağlayıcının secret ekranını kullanın.
Anahtar imaja, depoya ve loglara yazılmaz.

| Değişken | Varsayılan | Kapsam |
| --- | ---: | --- |
| `NFL_CHAT_PER_MINUTE` | 5 | Bir arayüz oturumu veya API istemci adresi, 60 sn |
| `NFL_CHAT_GLOBAL_PER_MINUTE` | 20 | Herkes, 60 sn |
| `NFL_CHAT_DAILY_LIMIT` | 200 | Herkes, UTC günü |
| `NFL_LLM_DAILY_TOKEN_LIMIT` | 500000 | Herkes, UTC günü |
| `NFL_LLM_MAX_OUTPUT_TOKENS` | 4000 | Tek sağlayıcı çağrısı |

Model `max_tokens` alanını kabul etmiyorsa `NFL_LLM_MAX_TOKENS_FIELD=max_completion_tokens`
kullanın. Token bütçesi çağrıdan önce ayrılır ve sağlayıcının bildirdiği kullanımla düzeltilir;
bildirim yoksa ayrılan miktar harcanmış sayılır. Sayaç okunamazsa veya ayar geçersizse sohbet
kapanır.

Sınırlar: Yeni tarayıcı oturumu oturum sayacını sıfırlar; asıl koruma genel sınırlardır. Kalıcı
diski olmayan barındırmada sayaç yeniden başlatmada sıfırlanır. Anahtarı açık demoya eklemeden
önce **sağlayıcı panelinde de harcama üst sınırı** tanımlayın.

## HTTPS yayını (Render)

1. Render → New → Blueprint ekranında bu depoyu ve yayınlanacak dalı seçin; `render.yaml` okunur.
2. Sohbet istenmiyorsa üç LLM değişkenini boş bırakın.
3. Oluşan `https://…onrender.com` adresinde demo uyarısını ve oyuncu ekranını kontrol edin.
4. GitHub → Settings → Secrets and variables → Actions → Variables altında `DEMO_URL` ekleyin.

Ücretsiz planda servis 15 dakika trafik almazsa uyur, uyanması yaklaşık bir dakika sürer ve
dosya sistemi kalıcı değildir. Demo verisi her başlangıçta yeniden üretilir.

## Sağlık kontrolü ve hata takibi

- Konteyner kontrolü hem HTTP ucunu hem veritabanı sorgusunu sınar: `docker compose ps`
- API: `/health` sürecin, `/ready` veritabanının durumunu verir (hata: 503).
- Hatalar zamanlı, anahtar içermeyen JSON satırlarıdır: `docker compose logs -f` veya Render Logs.
- `Demo health` iş akışı `DEMO_URL` adresini altı saatte bir HTTPS üzerinden sınar; başarısız
  çalıştırma Actions'ta görünür ve GitHub bildirim ayarına göre e-posta gönderir.

## Yedekleme ve geri yükleme

```sh
docker compose run --rm --no-deps -e NFL_DEMO_MODE=0 ui python -m pipelines.backup create /data/backups/YEDEK.zip
docker compose cp ui:/data/backups/YEDEK.zip .
```

Yedek SHA-256 özetleriyle ve veritabanı açılarak doğrulanır. Dosyayı sunucu dışında da saklayın.
Geri yüklemeden önce uygulamayı durdurun; bozuk yedek mevcut verinin yerine geçmez:

```sh
docker compose stop
docker compose run --rm --no-deps -e NFL_DEMO_MODE=0 ui python -m pipelines.backup restore /data/backups/YEDEK.zip
docker compose up -d --wait
```

## Sürüm güncelleme ve geri dönüş

Her sürüme ayrı etiket verin ve önce yedek alın:

```sh
NFL_IMAGE_TAG=v0.2.0 docker compose up --build -d --wait   # güncelle
NFL_IMAGE_TAG=v0.1.0 docker compose up -d --no-build --wait # önceki imaja dön
```

PowerShell'de önce `$env:NFL_IMAGE_TAG = "v0.2.0"` yazıp komutu ön eksiz çalıştırın. Render'da
Manual Deploy ile güncelleyin, Events → Rollback ile önceki dağıtıma dönün.

`sh docker/drill.sh` tek komutlu başlangıcı, yedeklemeyi, bilerek bozulan veritabanından geri
yüklemeyi, güncellemeyi ve geri dönüşü ayrı bir Compose projesinde dener. Her PR'da GitHub
Actions `container` işi olarak çalışır.

## Veri ve görsel paylaşım koşulları

| İçerik | Açık demoda | Gerekçe |
| --- | --- | --- |
| Kurgusal demo verisi | Var | Depodaki kodla üretilir |
| Yarışma CSV'leri | Yok | `.dockerignore` izin listesi dışında |
| Araştırma çıktıları, oyuncu izleri, GIF/PNG görseller | Yok | Yarışma verisinden türetilmiştir; demoda paylaşılmaz |
| NFL logosu veya takım görseli | Yok | Uygulamada kullanılmaz |

Kaynak: [Resmî yarışma kuralları](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/rules),
25 Kasım 2026'da okundu (Data Access and Use, Data Security, Code Sharing maddeleri). Bu bölüm hukuki görüş değildir.

| Kural | Demodaki karşılığı |
| --- | --- |
| Veri lisansı CC BY-NC 4.0; yalnızca ticari olmayan kullanım | Yarışma verisi yok |
| Yarışma verisi, yarışmaya katılmayanlara aktarılamaz, yayınlanamaz | Yarışma verisi ve türevleri imaja girmez |
| Yarışma kodu herkese açık paylaşılıyorsa Kaggle forumu veya notebook'unda da paylaşılmalıdır | Demoyu değil, depoyu ilgilendirir |

Sonuç: **Demo yalnızca kurgusal veri yayınladığı için koşullarla uyumludur.**

Açık konu (demo kapsamı dışında): Depoda Issue 6'dan önce eklenmiş, gerçek oyuncu düzeyinde
araştırma dosyaları vardır (`submission_mirror/mirror_explorer.html`, `reports/` CSV'leri ve bunlardan
üretilen görseller). Bunların ve herkese açık kodun kurallara uygunluğunu ekip ayrıca
değerlendirmelidir; bu belge onlar için onay değildir.
