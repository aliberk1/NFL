# WR ilk deneme analizi

## Sonuç

Bu ilk denemede curl rotasından çıkarılan hareket özellikleri, klasik Combine
ölçümlerine ek tahmin faydası göstermedi. Bu sonuç bütün hareket ölçümlerinin
faydasız olduğunu göstermez; yalnızca aşağıdaki dar tanımlı deneme için geçerlidir.

| Model | Oyuncu başına mutlak hata (MAE; düşük daha iyi) |
| --- | ---: |
| Eğitim oyuncularının ortalaması | 0.2103 |
| 40-yard süresi + boy + kilo | 0.1683 |
| Klasik ölçümler + curl hareket özellikleri | 0.1754 |

Hareket özelliklerinin hata iyileştirmesi -0.0071; oyuncu bazlı eşleştirilmiş
bootstrap %95 aralığı [-0.0169, 0.0024]. Aralık sıfırı içeriyor. Bu aralık,
sabitlenmiş modellerin tahminleri içindir; bütün eğitim belirsizliğini kapsamaz.

## Veri ve yöntem

- Curl kaydı bulunan 102 WR; 109 denemenin 99'unda ilk geri dönüş tespit edildi.
- Hareket özellikleri hesaplanabilen 97 oyuncu.
- Çaylak normal sezonunda en az 30 uygun kaydı olan 58 oyuncu, 12.798 kayıt.
- İptal edilen oyunlar ve eksik rota/mesafe kayıtları dışarıda bırakıldı.
- Özellikler: dönüşe yaklaşma hızı, dönüş sırasındaki minimum hızın yaklaşma
  hızına oranı, dönüşten 0.4–0.8 saniye sonraki hızın yaklaşma hızına oranı.
- Hedef: pasın atıldığı andaki savunmacı mesafesinin rota, savunma tipi,
  başlangıç mesafesi (cushion), down ve yards-to-go ile açıklanamayan kısmının
  oyuncu ortalaması. Bu bir yetenek veya nedensellik ölçütü değildir.
- Her turda bir draft yılı tamamen dışarıda bırakıldı. Bağlam modeli, eksik
  değer doldurma ve ölçekleme yalnız eğitim bölümünde öğrenildi.
- Ridge alpha=10 önceden sabitlendi; bu pilotta hiperparametre araması yapılmadı.
- Yıl bazlı ayırma oyuncu sızıntısını önler; geçmişten geleceğe tahmin testi
  değildir, çünkü bazı turlarda sonraki yıllar eğitimde kullanılır.

## Kalite kontrolü ve sonraki çalışma

İlk dokuz oyuncunun grafiklerinde işaretlenen dönüş noktaları görsel olarak
incelendi. Tüm yılları ve reddedilen denemeleri kapsayan kontrol henüz yapılmadı.
Önceki basit maksimum ilerleme yaklaşımı top yakalama sonrası koşuyu dönüşle
karıştırdığı için, ilk kalıcı geri dönüşü kullanan yöntemle düzeltildi.

Sonraki adım: resmi veri sözlüğündeki birimleri ve kayıt tanımlarını doğrulamak;
dönüş tespitini yıllar genelinde incelemek; Combine curl hareketini maçtaki
benzer rotalar ve adam adama savunmayla daha doğrudan eşleştirmek. Yeni analizler
keşifsel olarak etiketlenmeli; tekrar tekrar aynı test yıllarına göre özellik
seçerek elde edilen iyileşme bağımsız doğrulama sayılmamalı.

## Dosyalar

- `turn_detection.png`: ilk dokuz rota ve tespit edilen dönüş noktaları.
- `model_comparison.png`: model hata karşılaştırması.
- `summary.json`: sayısal sonuçlar ve örneklem sayıları.
- `player_features.csv`: oyuncu düzeyindeki girdi özellikleri.
- `held_out_predictions.csv`: eğitim dışında tutulan oyuncuların tahminleri.
- `combine_attempt_features.csv`: deneme düzeyindeki hareket ölçümleri.
- `rejected_attempts.csv`: ölçüm üretilemeyen denemeler ve nedenleri.

Yeniden çalıştırma: proje kökünde `python scripts/wr_pilot.py`.
Gerekli paketler: pandas, numpy, scikit-learn, matplotlib.
