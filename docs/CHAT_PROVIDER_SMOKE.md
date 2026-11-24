# Gerçek sohbet sağlayıcısı denemesi

`python scripts/smoke_chat_provider.py` yerel DuckDB'den normal sezon kaydı
bulunan tek bir oyuncu seçer ve yapılandırılmış gerçek sağlayıcıya bir sohbet
isteği gönderir. İstek en az bir araç çağrısı, gerçek veritabanı sonucu,
oyuncu/sezon/maç türü kapsam satırı ve kaynak tabloları içermelidir. Betik API
anahtarını veya tam sağlayıcı URL'sini yazdırmaz. Anahtar/model ya da veritabanı
yoksa istek göndermeden açıkça durur.

## Çalıştırma

PowerShell'de uygulama için kullandığınız ortam değişkenlerini tanımlayın ve
gerçek sağlayıcıya veri gönderilmesine izin verdiğinizden emin olun:

```powershell
$env:NFL_LLM_API_KEY = "..."
$env:NFL_LLM_MODEL = "..."
# İsteğe bağlı: OpenAI uyumlu özel uç nokta
$env:NFL_LLM_BASE_URL = "https://api.openai.com/v1"
python -m pipelines.ingest
python scripts/smoke_chat_provider.py
```

Bu çalışma alanında `NFL_LLM_API_KEY`, `NFL_LLM_MODEL` ve yerel `data/`
veritabanı bulunmadığından gerçek sağlayıcı denemesi **çalıştırılmadı**. Bunun
yerine sahte sağlayıcı regresyon testleri gerçek HTTP kullanmadan araç turunu,
kanıt kapsamını, desteklenmeyen sayıların engellenmesini ve zaman aşımı
davranışını sınar. Canlı deneme sonucunu aşağıdaki kayıt alanlarıyla ekleyin.

## Deneme kaydı

| Tarih (UTC) | Model kimliği | Sonuç | Araçlar ve kaynaklar | Anahtar kaydedildi mi? |
| --- | --- | --- | --- | --- |
| Çalışma alanı incelemesi | — | Çalıştırılmadı: sağlayıcı ayarları ve yerel DB yok | — | Hayır |

Canlı deneme yapıldığında yalnızca sağlayıcı/model kimliğini, bitiş durumunu,
araç adlarını, kaynak tabloları ve hata sınıfını kaydedin; API anahtarı,
Authorization başlığı veya tam istek gövdesini kaydetmeyin.

## Hata ve sınır davranışı

- Bağlantı/yanıt okuma en çok 30/120 saniye sürer; zaman aşımı API'de HTTP 504
  olarak döner.
- HTTP 502, 503 ve 504 en çok iki kez artan beklemeyle yeniden denenir. Kimlik
  doğrulama, model, kota ve diğer 4xx hataları yeniden denenmez.
- Araç çağrıları en çok 6 tur ve toplam 8 çağrıyla sınırlıdır.
- Sağlayıcı yanıtındaki sayılar son araç verisiyle eşleşmiyorsa sayı içeren
  yanıt gösterilmez; kullanıcıya doğrulanamayan sayıları vermediğimiz söylenir.
- Bir isim birden fazla oyuncuyla eşleşirse seçim istenir. İstenen analiz araç
  alanlarında yoksa başka bir metriği vekil kullanmak yerine veri sınırı belirtilir.
