# NFL Dataset Analiz Asistanı

Yalnızca mevcut NFL datasetini sorgulayan, kaynaklı Türkçe analiz üreten uygulama.
Mevcut araştırma dosyalarına ek olarak geliştirilir.

## Başlatma (PowerShell, D:\NFL)

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-app.txt
.\.venv\Scripts\python.exe -m pipelines.ingest
.\.venv\Scripts\python.exe -m streamlit run app/ui.py --server.address 127.0.0.1
```

İsteğe bağlı API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.api:app --host 127.0.0.1 --port 8000
```

API belgeleri: http://127.0.0.1:8000/docs

## Sohbet bağlantısı

Ücretsiz bulut seçeneği ve Gemini kurulum adımları: [LLM kurulumu](docs/LLM_KURULUMU.md).
Alternatif sağlayıcı: [EVREN kurulumu](docs/EVREN_KURULUMU.md).
Koç odaklı geliştirme/kabul hedefleri: [10 koç sorusu](docs/KOC_SORULARI.md).

Arayüzü başlatacağınız terminalde OpenAI-uyumlu, araç çağırabilen sağlayıcıyı ayarlayın:

```powershell
$env:NFL_LLM_API_KEY = "anahtarınız"
$env:NFL_LLM_MODEL = "sağlayıcınızdaki-model-kimliği"
$env:NFL_LLM_BASE_URL = "https://api.openai.com/v1"
```

Anahtarı Git'e veya sohbete koymayın. `.env.example` açıklama içindir; `.env` otomatik okunmaz.
LLM bağlantısı yokken oyuncu karşılaştırma ve kapsam ekranları çalışır.
Harici LLM kullanıldığında soru ve seçilen araç sonuçları sağlayıcıya gönderilir.
Spor verisi kaynağı yalnızca yerel datasettir.

## Mevcut kapsam

- Beş CSV DuckDB'ye yüklenir; anahtar tekilliği ve oyuncu/maç bağlantıları doğrulanır.
- Oyuncu arama, profil, sezonsal karşılaştırma ve takım kayıt kapsamı.
- Araç çağrılarıyla kaynaklı sohbet ve incelemeye açık veri kanıtları.
- Tracking dosyaları henüz yüklenmez; eğitimli tahmin modeli henüz yoktur.
- Takım kapsam özetleri takım gücü veya kazanma olasılığı değildir.
- Kariyer toplamları zaman damgasızdır; geçmişe dönük model girdisi olarak kullanılamaz.

## Sonraki aşamalar

1. Tracking özelliklerini mevcut araştırma kodlarından doğrulayarak ekle.
2. Pozisyon bazlı benzer oyuncu modeli ve açıklanabilir uzaklık ölçüleri.
3. Yeterli sezon kapsaması olan hedeflerde zamansal performans tahmini.
4. Gerçek kullanıcı soru kümesiyle kaynak doğruluğu ve araç seçim değerlendirmesi.

## Kontroller

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Ham veri, sanal ortam, anahtarlar ve arşivler Git dışında tutulur.
