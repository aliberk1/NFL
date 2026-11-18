# EVREN bağlantısı

Resmi kaynak: https://evren.ssyz.org.tr/llm/models
İncelenen katalog OpenAI uyumlu `/v1/chat/completions`, Bearer anahtar ve
function calling örnekleri yayımlar.

- Base URL: `https://evren-llmapi.ssyz.org.tr/v1`
- API anahtarları ekranı: `https://evren.ssyz.org.tr/api-keys`
- Katalog örneklerinde kullanılan araç çağırabilen model: `glm-5.3`.
  Hesaba atanmış modeller ayrıca doğrulanmalıdır.
- Sitede ücretsiz test/entegrasyon dönemi belirtilir; süre ve kredi politikası
  dinamik olduğundan hesabınızdaki güncel koşulları kontrol edin.
  Kalıcı/sınırsız ücretsiz kullanım veya kesintisizlik doğrulanmış değildir.

## PowerShell

Mevcut Streamlit sürecini Ctrl+C ile durdurun, aynı pencerede:

```powershell
cd D:\NFL
$env:NFL_LLM_BASE_URL = "https://evren-llmapi.ssyz.org.tr/v1"
$env:NFL_LLM_MODEL = "glm-5.3"
$secureKey = Read-Host "EVREN LLM API anahtari" -AsSecureString
$env:NFL_LLM_API_KEY = ([System.Net.NetworkCredential]::new("", $secureKey).Password).Trim()
.\.venv\Scripts\python.exe -m pipelines.check_llm
```

Gemini anahtarı EVREN'de çalışmaz. EVREN'in kendi LLM API anahtarını kullanın.
Model kontrolü başarılıysa:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app/ui.py --server.address 127.0.0.1 --server.port 8502
```

http://localhost:8502 üzerinde “Dataset içinde kaç oyuncu var? Kaynak tabloyu belirt.”
sorusunu sorun. Model listesi erişimi tek başına sohbet ve araç çağırma testinin yerini tutmaz.
Gerçek sağlayıcı testi kullanıcı anahtarıyla henüz yapılmadı.

Uygulama 502/503/504 hatalarında 2 ve 4 saniye bekleyerek en fazla iki ek deneme yapar.
401/403/404/429 hatalarında otomatik tekrar veya başka modele geçiş yapmaz.
