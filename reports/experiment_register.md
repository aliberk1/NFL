# Deneme kaydı

Bu kayıt olumlu ve olumsuz analizleri birlikte tutar. Sonuç görüldükten sonra
yapılan tanım değişiklikleri yeni doğrulama gibi sunulmaz.

| Sıra | Soru / değişiklik | Kapsam | Sonuç | Statü |
| --- | --- | --- | --- | --- |
| 1 | Curl dönüş özellikleri, klasik ölçümlere ek olarak maçta ayrışmayı açıklar mı? | 58 WR, 12.798 çaylak normal sezonu kaydı; dışarıda bırakılan draft yılı | MAE 0.1683 -> 0.1754; ek fayda görülmedi | Keşif |
| 2 | Aynı soruyu benzer HITCH rotaları ve adam adama savunmada sınamak | 3 kapsam × 2 ileri yıl testi | 6 karşılaştırmanın 5'inde MAE arttı; tüm fark aralıkları sıfırı içerdi | Keşif; 1. sonuçtan sonra |
| 3 | Combine 40-yard tracking özellikleri maçtaki rota hızına taşınıyor mu? | 58 WR, 10.944 uygun oyun; 2023->2024 ve 2023–24->2025 | Ham ilişki r=0.382; ek model MAE 2024'te iyileşti, 2025'te kötüleşti | Bu sorunun sonuçları hesaplanmadan tasarım yazıldı; genel olarak keşif |
| 4 | Hız ölçümlerinin tekrar kararlılığı / yıl içi ilişki | 81 WR iki Combine denemesi; 58 WR maç bağlantısı | Peak tekrar r=0.893; erken hız r=0.153; yıl ortalaması çıkarılmış maç ilişkisi r=0.365 | 3. sonuçtan sonra tanısal analiz |
| 5 | Düşük kararlılıklı erken hız özelliği çıkarılırsa? | 3. analizle aynı örneklem ve yıl ayrımı | Peak-only MAE 2024 0.1770; 2025 0.1415; tutarlı ek iyileşme yok | Açıkça post-hoc; ana sonucu değiştirmedi |
| 6 | OL mirror fazı ile çıkış sprintini ayırmak; faz ölçümleri bire bir baskı sonucuna ek bilgi taşıyor mu? | 113 geçerli Combine kaydı; 50 OL, 20.853 çaylak pas koruması | Bütün kabul edilen kayıtlarda hız zirvesi çıkışta; 2025 MAE 2.502 -> 2.482 pp; belirsizlik sıfırı içeriyor ve süre duyarlılığında işaret değişiyor | Özellik-sonuç eşleştirmesinden önce tasarım yazıldı; keşif |
| 7 | Mirror yana hareketi maçın ilk 1.5 saniyesindeki yana harekete taşınıyor mu? | 6. çalışma oyuncuları, 20.110 oyun | Ham r=0.053; yeni özellik iki test yılında da MAE'yi iyileştirmedi | 6. sonuçtan sonra takip sorusu; sonucu görmeden pencere/model sabitlendi |
| 8 | Mirror belirsizliğine eğitim oyuncusu seçimini de katmak | 2025 ana testi, 400 tam yeniden eğitimli bootstrap | MAE iyileşme aralığı −0.264 ile +0.353 pp | Sağlamlık kontrolü; ana sonucu değiştirmedi |
| 9 | Tüm OL Combine ayak işi drillerinde (Mirror, 5-Yard Wave, Pass Rush Drop) çıkış sprinti baskınlığı ve 2-denemeli tekrar güvenilirliği | 470 kabul edilen OL kaydı (113 Mirror, 118 Wave, 239 Drop; 118 çift tekrarlı Drop) | 470 kaydın tamamında (%100.0) zirve hız çıkış sprintinde; faz vs. tüm kayıt Spearman r: +0.005 (Mirror), −0.022 (Wave), +0.147 (Drop); Drop 2-tekrar güvenilirliği çıkışta r=+0.510 iken yanal pas setinde r=+0.104 | Ölçüm genellemesi ve psikometrik zayıflama (attenuation) tanısı |
| 10 | İkili `pressure_allowed` yerine sürekli NGS `peak_pressure_probability_allowed` hedefiyle duyarlılık testi | 50 OL, 20.853 bire bir pas koruması; 2023->2024 ve 2023–24->2025 | Yarı-yarıya maç güvenilirliği r=0.367'den r=0.696'ya yükseldi; 2025 MAE klasik 2.189 -> tüm-kayıt 2.215 (kötüleşti) -> mirror fazı 2.157 pp (+0.032 pp iyileşme, %95 GA [−0.139, +0.195]) | Duyarlılık kontrolü; faz ayrımının gürültüyü temizlediğini doğruladı, ek tahmin kazancı yine sıfırı içerdi |

## Yöntem düzeltmeleri

- İlk curl detektörü tüm kayıttaki maksimum ilerlemeyi kullanıyordu. Kayıtlar
  top yakalama sonrası yeniden koşmayı da içerdiğinden bütün denemeleri reddetti.
  Maç sonucu hesaplanmadan, ilk kalıcı geri dönüşü tespit edecek şekilde düzeltildi.
- Hız çıkarımındaki kayıt hesabına tracking dosyasında bulunmayan 38 uygun
  oyuncu-oyun kaydı ayrıca eklendi. Kabul edilen oyunlar ve model sonuçları değişmedi.
- Erken hız özelliği için başlangıçta zaten eşik üstünde olan 7 deneme kalite
  kaydına alındı. Ana tasarımın örneklemi sonuç sonrası değiştirilmedi.

## Yorum sınırı

Burada birbirinden bağımsız beş doğrulama yoktur. Analizler aynı oyuncuları,
yılları ve bazı ortak hedefleri kullanır. Güven aralıkları çoklu denemeye göre
düzeltilmemiştir. En iyi yıl veya ölçüm seçilerek kesin başarı iddiası üretilmemiştir.

## Dış kaynakların kullanımı

Birincil hız analizi sonuçları hesaplandıktan sonra kamuya açık çalışmaların
özetlerini içeren aşağıdaki kaynak incelendi:
https://hackers.pocketplay.win/en/kaggle/nfl-big-data-bowl-2027/

Bu kaynak, başlangıç zamanlaması ve tekrarlanabilirlik hakkında önceki
çalışmalar olduğunu gösteriyor. Bu yöntemsel fikirler ilk kez burada keşfedilmiş
gibi sunulmaz. Dışarıdan veri, tahmin, oyuncu özelliği veya notebook kodu alınmadı.
