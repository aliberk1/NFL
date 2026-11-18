# NFL asistanı — geliştirme durumu

## Tamamlanan ilk sürüm

- Yerel Git deposu, veri ve anahtarları dışlayan ignore kuralları.
- DuckDB yükleyici, tekillik ve yabancı anahtar doğrulamaları.
- 510 oyuncu, 1.002 maç, 314.197 oyuncu–oyun kaydı.
- Oyuncu arama, profil, sezon ve sezon türü bazında karşılaştırma.
- Takım kayıt kapsamı; tamamı temsil edilmeyen kadrolar için kapsam açıklaması.
- Streamlit ekranı, FastAPI, OpenAI-uyumlu araç çağırma bağlantısı.
- Parametreli sorgu, eksik veri, sezon ayrımı, API doğrulama ve sahte sağlayıcıyla araç döngüsü testleri.

## Kullanıcıdan gerekenler

1. **GitHub tamamlandı:** `https://github.com/aliberk1/NFL.git`.
   `main` dalı uzak depoya gönderildi.
2. **LLM:** Araç çağırmayı destekleyen sağlayıcı ve model seçin.
   API anahtarını paylaşmak yerine README'deki ortam değişkenlerini yerelde tanımlayın.
   Harici servis kullanmak istemiyorsanız yerel model için donanım ve servis kurulumu ayrıca değerlendirilir.
3. **Kabul soruları hazır:** `docs/KOC_SORULARI.md` içinde koç odaklı 10 soru,
   gerekli veriler ve cevap kalite ölçütleri belirlendi.

## Henüz doğrulanmamış / sonraki işler

- Gerçek LLM bağlantısıyla uçtan uca sohbet.
- Tracking özellikleri, benzer oyuncu modeli ve zamansal tahmin.
- Sayısal cevapların model çıktısıyla otomatik tutarlılık denetimi.

Mevcut sürümde eğitilmiş tahmin modeli yoktur; sohbet talimatları bunu açıkça belirtir.
Bu ilk sürüm, veri inceleme ve kaynaklı analiz temelidir.
