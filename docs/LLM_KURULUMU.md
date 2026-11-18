# Bulut LLM seçimi

18 Kasım 2026 tarihinde resmi dokümantasyon kontrol edilmiştir.

## Öneri: Gemini Developer API ücretsiz katmanı

Google AI Studio hesabından API anahtarı oluşturulur. Model Google sunucularında çalışır.
Gemini sohbet aboneliğini uygulamaya bağlamak yerine ayrı Developer API kullanılır.
Ücretsiz katman sınırlıdır; hesap, bölge, proje ve model bazındaki geçerli kota AI Studio'da kontrol edilmelidir.
Bir asistan sorusu birden fazla API çağrısı tüketebilir.

Güncel fiyat sayfasında Gemini 3.8 Flash ve Gemini 3.5 Flash-Lite için ücretsiz giriş/çıkış listelenmektedir.
Başlangıç tercihi: `gemini-3.8-flash`; hafif sorgular için değerlendirilecek alternatif: `gemini-3.5-flash-lite`.
Ücretsiz katmanda içerik Google ürünlerini iyileştirmede kullanılabilir.

PowerShell'de, uygulamayı başlatmadan önce:

```powershell
$env:NFL_LLM_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
$env:NFL_LLM_MODEL = "gemini-3.8-flash"
$secureKey = Read-Host "Gemini API anahtarı" -AsSecureString
$env:NFL_LLM_API_KEY = [System.Net.NetworkCredential]::new("", $secureKey).Password
.\.venv\Scripts\python.exe -m streamlit run app/ui.py --server.address 127.0.0.1 --server.port 8502
```

8502 portu önceki anahtarsız 8501 oturumuyla çakışmaz. Ortam değişkenleri yeni başlayan sürece aktarılır.
Anahtar dosyaya, Git'e veya sohbete yazılmaz.
Modelin hesabınızda erişilebilirliği ve ücretsiz proje kotası doğrulanmalıdır.
Sistem otomatik ücretli model geçişi yapmaz. Faturalandırması etkin projelerde kullanım ücretli olabilir.
Mevcut bağlantı OpenAI-uyumlu araç çağırmayı destekler; gerçek Gemini entegrasyon testi anahtar sağlanınca yapılacaktır.

## ChatGPT aboneliği

Normal OpenAI API kullanımı ChatGPT Plus aboneliğine dahil değildir.
Güncel resmi belgelerde desteklenen uygulamalar için “Sign in with ChatGPT” ile plan kotası paylaşımı vardır.
Bu imkan desteklenen entegrasyonlar, hesap uygunluğu ve uygulama kaydı koşullarına bağlıdır;
bu projede henüz kurulmamıştır ve herhangi bir API anahtarı yerine otomatik kullanılamaz.
İleride resmi geliştirici entegrasyonu ayrıca değerlendirilebilir.

## Kaynaklar
- https://ai.google.dev/gemini-api/docs/pricing
- https://ai.google.dev/gemini-api/docs/openai
- https://aistudio.google.com/apikey
- https://help.openai.com/en/articles/6950777-what-is-chatgpt-plus
- https://help.openai.com/en/articles/20001542
