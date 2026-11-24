# Mirror -> maç hareketi: sonuç ölçülmeden kaydedilen takip analizi

Mirror -> baskı ana testi tamamlandı. 2025'te özellikler eklenince MAE yalnız
0.019 yüzde puan azaldı; güven aralığı sıfırı içerdi. Süre düzeltmesi kaldırılınca
işaret tersine döndü. Bu sonuç baskı tahmininde ek fayda iddiasını desteklemiyor.

Şimdi zincirin ara halkasını sınayacağız: testteki yanal hareket ölçümü, maçta
gerçekten yanal hareketle ilişkili mi? Bu takip sorusu, baskı sonuçları görüldükten
sonra seçilmiştir; önceki ana testin yerine geçmez.

## Sabit tanımlar

- Aynı 50 OL oyuncusu, aynı çaylak REG bire bir pas koruması fırsatları.
- Oyun takip verisinde tek ball_snap; snap'ten sonraki ilk 1.5 saniye tam olmalı.
- Snap +1.5 s öncesinde pas atışı veya terminal oyun olayı varsa kayıt dışarıda.
- Zaman tekrarları yok, kare boşluğu <=0.21 s, en az 16 kare.
- Y koordinatını 5-kare Savitzky–Golay ile yumuşatıp zamana göre türev al.
- Ana hedef: bu sabit pencerenin mutlak yanal hız %75 yüzdeliği. Oyuncu başına
  en az 50 geçerli oyun. Hız burada görev icrasıdır; “daha hızlı daha iyi” denmez.
- Eğitim bağlam modeli: sahadaki C/G/T, hücum formasyonu, down, yards_to_go,
  snap anındaki hız; Ridge alpha=10. Oyuncu hedefi ortalama bağlam artığı.
- Oyuncu modelleri: aynı klasik set; klasik + whole-drill speed;
  klasik + lateral_speed_p75. Reversal_recovery bu ara hedefe eklenmez.
- Değerlendirme: 2023->2024, 2023–24->2025. MAE/RMSE; eşit oyuncu ağırlığı.
- Sabit modeller, eğitim içi ölçekleme; eşleştirilmiş oyuncu-bootstrap CI.
- Ham ve yıl/pozisyon ortalamalarından arındırılmış ilişkiler betimsel olarak
  gösterilir. Sonuca bakarak alternatif pencereler veya gruplar taranmaz.
- Ölçümün maçlar arası kararlılığı: tek/çift sıradaki maçlar, her yarıda >=20 oyun.

Bu ara analizin pozitif olması baskı tahmininin pozitif olduğu anlamına gelmez.
Negatifse de raporlanır. Nihai anlatı aynı hipotez zincirinin bütün aşamalarını gösterir.
