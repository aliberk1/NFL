# Ölçüm ve yorum doğruluğu

## Düzeltilen örnek

“Maç sayısı oyuncu–oyun kaydıdır” yanlıştır.
`games`, gruptaki benzersiz game_id sayısıdır; `player_play_rows` satır sayısıdır.
Will Anderson, REG:

| Sezon | Maç | Oyuncu–oyun satırı | Sack etiketi toplamı | Sack/maç |
|---|---:|---:|---:|---:|
| 2023 | 15 | 629 | 7 | 0,47 |
| 2024 | 14 | 561 | 10 | 0,71 |
| 2025 | 17 | 694 | 11 | 0,65 |

Doğru sonuç: “Gözlenen maç başına sack değeri en yüksek sezon 2024.”
Desteklenmeyen sonuç: “Genel olarak en güçlü sezon 2024.”
Bu ölçüm pass-rush fırsatı başına verim veya genel yetenek puanı değildir.

## Uygulama

- Veri araçları ölçüm tanımı, payda, kapsam ve yorum sınırları döndürür.
- Sack/maç oranı SQL'de hesaplanır, dil modeline bırakılmaz.
- Normal sezon doğrudan REG parametresiyle filtrelenebilir.
- Eksik sack ve pressure etiketleri sıfır yapılmaz; etiketli kayıt sayıları verilir.
- LLM talimatları genel üstünlük ve gözlemsel veriden neden çıkarma hatalarını hedefler.

## Kontroller

Otomatik testler: aynı maçtaki çoklu satırlar, REG/POST ayrımı, null değerler,
oran paydası ve geçersiz sezon türü.
Gerçek veri sorgusunda yukarıdaki değerler doğrulanmıştır.

Canlı LLM kabul denemeleri:
1. “Will Anderson'ın normal sezon maç ve sack sayılarını yıllara göre karşılaştır.”
2. “2024 kesinlikle en iyi sezonu mu? Hangi ölçüme göre?”
3. “15 maç demek 15 snap mi?”
4. “Baskı verme oranı boşsa hiç baskı üretmemiş mi?”

Beklenti: doğru birim, ölçüme bağlı yorum, eksik veriyi sıfır saymama.
Talimatlar tüm serbest metin hatalarını otomatik olarak yakalama garantisi değildir.
Bu değişiklik sonrası canlı sağlayıcı ile kabul denemesi henüz yapılmadı.
