# Koç soruları: beklenen kanıt ve yanıt sınırları

Bu belge, [`KOC_SORULARI.md`](KOC_SORULARI.md) içindeki on sorunun her biri için
hangi kanıtın yanıtı desteklemesi gerektiğini ve bugünkü uygulamanın veremediği
cevaplarda nasıl davranacağını kaydeder. Beklenen cevaplar sayısal sonuç değil,
kanıt ve yorum sözleşmesidir: kullanılan yerel DuckDB bu çalışma ortamında
bulunmadığından burada gerçek oyuncu sıralaması veya sezon sonucu üretilmemiştir.

## Ortak yanıt sözleşmesi

- Sayı yalnızca mevcut araç sonucunda bulunan değerden gelir. Araç verisiyle
  eşleşmeyen sayısal iddia kullanıcıya gösterilmez; yanıt ölçülebilir kanıtın
  bulunmadığını söyler.
- Araç sonucundan oyuncu, sezon ve maç türü çıkarılabiliyorsa yanıtın altında
  otomatik kanıt satırı gösterilir. Kaynak tablo adları aynı satırda bulunur.
- Normal sezon (`REG`), sezon öncesi (`PRE`) ve play-off (`POST`) birbirine
  karıştırılmaz. Eksik değer sıfır sayılmaz.
- Araçların sağlamadığı ölçüm veya alt grup için vekil sonuç uydurulmaz; eksik
  alan ve gereken veri açıkça belirtilir.
- Sayısal iddialar `numeric_claims_supported` ile son araç çıktısına karşı
  denetlenir. Denetimden geçmeyen yanıt sayı vermeyen güvenli bir yanıtla
  değiştirilir.

## Soru başına kanıt planı

| Soru | Gerekli kanıt kümesi | Bugünkü araçlarla beklenen yanıt |
| --- | --- | --- |
| 1. OL yardım bloklaması | `player_performance`: oyuncu, sezon/tür, `pressure_allowed_rate`, etiketli kayıt paydası; ayrıca down ve mesafe alanları | Sezon/tür bazında genel kayıt incelenebilir. Down/mesafe alt grupları sohbet aracında yok; üçüncü hak ve uzun mesafe sıralaması istenirse veri alanının eksik olduğu söylenir. |
| 2. Alıcı rotası ve coverage | `route_ran`, man/zone, hedef ve yakalama sonuçları; rota koşusu ve hedef paydaları | Mevcut sohbet araçlarında rota ve coverage tablosu yok. Bir rota veya coverage üstünlüğü iddia edilmez. |
| 3. Üçüncü hak dönüşümü | Down, `yards_to_go`, rota, oyuncu, kazanılan yard ve ceza iptali | Gerekli alanlar yok. `yards_gained >= yards_to_go` resmi first-down olarak sunulmaz. |
| 4. Rakip pass-rusher | Geçerli pass-rush fırsatları, `time_to_pressure`, blitz ve sack | Savunma baskı zamanı / fırsat tablosu yok. Sack/maç tek başına hızlı baskı sıralaması değildir. |
| 5. Red zone | Hücum yönüne göre rakip kale mesafesi, possession, formation/route ve oyun EPA'sı | Mevcut oyuncu araçları red-zone alt grubu üretmiyor. Oyuncu satırlarından oyun EPA'sı tekrar toplanmaz. |
| 6. YAC | Tamamlanmış yakalama, YAC ve beklenen YAC; rota ve örneklem | Sohbet aracı bu hedefleri sunmuyor. Fark veya rota sıralaması tahmin edilmez. |
| 7. Combine'dan maça hareket | Manifestle doğrulanmış araştırma çıktıları; pozisyon, dril fazı ve maç hareketi | Araştırma sekmesi betimsel OL/WR sonuçlarını gösterir. Sohbet aracı tracking özelliklerini sorgulamaz; dril çıkış hızı oyun içi yetenek diye yorumlanmaz. |
| 8. Oyuncu gelişimi | Sezon bazında fırsat/snap ve pozisyona uygun oran | Sohbet aracı bu fırsat paydalarını sunmuyor. Kariyer toplamı yıllık gözlem gibi kullanılmaz. |
| 9. Aynı rol karşılaştırması | Aynı pozisyon ve draft sınıfındaki oyuncular; aynı sezon/tür, ölçüm ve payda | `player_performance` karşılaştırması aynı pozisyon/draft bağlamında yapılabilir. Rol, sağlık ve rakip eşleşmesi bilinmiyorsa üstünlük genellenmez. |
| 10. Haftalık üç öncelik | Önceki uygun ölçümlerin her biri için kaynak, payda, belirsizlik ve izleme ölçütü | Yeterli, karşılaştırılabilir araç kanıtı yoksa üç öncelik uydurulmaz. Yalnızca desteklenen ölçümler için denenecek hipotez önerilir. |

## Deterministik regresyon örneği

Sahte sağlayıcı testi `tests/test_app.py` içinde şu senaryoyu sabitler:

- Soru: `A Player` için 2023 normal sezon performansı.
- Kanıt: `player_performance` aracının verdiği oyuncu, sezon, `REG` türü ve
  `players`, `games`, `player_play` kaynakları.
- Sağlayıcı yanıtı kanıtta olmayan `99 sack` sayısını ileri sürerse, bu sayı
  çıktıya geçmez. Yanıt güvenli biçimde sayı vermeyi reddeder ve aynı kanıtın
  oyuncu/sezon/tür/kaynak satırını gösterir.

Bu test gerçek NFL sonucu veya sağlayıcı doğrulaması değildir; yanıt kapısını,
kapsam bilgisini ve kaynak sunumunu ağ kullanmadan denetler.
