# İkinci aşama: Benzer rota ve ileri yıl karşılaştırması

## Kısa sonuç

İlk denemedeki curl dönüş özelliklerinin maçta savunmacıdan uzaklaşmayı
öngörmede ek faydası bu aşamada da desteklenmedi. Altı karşılaştırmanın beşinde
hareket özellikleri eklendiğinde hata arttı. Birinde çok küçük bir düşüş oldu;
altısının da koşullu %95 bootstrap aralığı sıfırı içeriyor.

Bu sonuç, Combine hareketlerinin genel olarak değersiz olduğunu göstermez.
İncelenen özellikler, hedef tanımı ve sınırlı oyuncu örneklemi için geçerlidir.

## Tasarım

Analiz çalıştırılmadan önce üç kapsam ve örneklem eşikleri kodda belirlendi:

1. Tüm rotalar: oyuncu başına en az 30 uygun çaylak sezonu kaydı.
2. HITCH: en az 10 kayıt; Combine curl testine yaklaşık benzer rota.
3. Adam adama savunmada HITCH: en az 5 kayıt.

2024 testi yalnız 2023 oyuncularıyla; 2025 testi yalnız 2023–2024 oyuncularıyla
eğitildi. Bağlam düzeltmesi, eksik değer doldurma, ölçekleme ve model eğitimi
test yılını kullanmadı. Oyuncu kesişimi ve yıl sırası kodda doğrulandı.
Oyuncu-oyun anahtarlarında yinelenen kayıt bulunmadı.

Önceki aşamada bu yıllar incelendiği için bunlar yeni, bağımsız doğrulama verisi
değildir. Altı karşılaştırma keşifseldir; en iyi sonucu seçip başarı diye sunmuyoruz.

## Sonuçlar

MAE: oyuncu ortalamasındaki mutlak tahmin hatası; düşük daha iyi.

| Kapsam | Test yılı | Eğitim / test oyuncusu | Klasik model | + Hareket |
| --- | --- | ---: | ---: | ---: |
| Tüm rotalar | 2024 | 23 / 19 | 0.1849 | 0.2104 |
| Tüm rotalar | 2025 | 42 / 16 | 0.1169 | 0.1252 |
| HITCH | 2024 | 20 / 16 | 0.2788 | 0.2992 |
| HITCH | 2025 | 36 / 15 | 0.2878 | 0.2856 |
| HITCH, adam adama | 2024 | 12 / 13 | 0.2701 | 0.3923 |
| HITCH, adam adama | 2025 | 25 / 9 | 0.3042 | 0.3286 |

Klasik model: 40-yard süresi, boy, kilo. Hareket özellikleri: curl dönüşüne
yaklaşma hızı, dönüşte hız koruma oranı ve dönüş sonrası hız oranı.
Hedef ve bağlam düzeltmesi ilk pilotla aynı; hiperparametre ayarı yapılmadı.

## Ölçüm kararlılığına dair bulgu

Oyuncuların maç kayıtlarını kronolojik sırada tek/çift sıra numaralarına ayırıp,
iki gruptaki ham mesafe ortalamaları arasındaki oyuncular arası korelasyona baktık:

| Kapsam | Oyuncu | Korelasyon |
| --- | ---: | ---: |
| Tüm rotalar | 58 | 0.768 |
| HITCH | 51 | 0.137 |
| HITCH, adam adama | 34 | 0.200 |

Dar rota gruplarında ham hedefin kararlılığı düşük görünüyor. Bu kontrol yalnız
betimseldir: küçük örneklem, daralan oyuncu farklılıkları ve maç bağlamı bu
değeri etkileyebilir. Aynı maçın kayıtları iki grupta da bulunabilir; bağımsız
maçlar arası güvenilirlik veya tahmin performansı olarak yorumlanmamalıdır.

## Veri kalitesi

- 2023/2024/2025 için sırasıyla 34/30/35 curl denemesinde özellik üretildi.
- Giriş hızı medyanları yaklaşık 6.99/6.86/7.03; dönüşte hız oranı medyanları
  0.290/0.293/0.258. Yıllar arası farklılıkların nedeni henüz belirlenmedi.
- İlk pilotta yalnız ilk dokuz rota görsel incelendi; bütün yıllar için dönüş
  etiketlerinin denetlenmesi tamamlanmış değildir.
- Kaggle veri açıklaması araç üzerinden alınamadı; resmi birimler ve alan
  tanımları doğrulanana kadar sayısal hataları belirli bir mesafe birimiyle sunmuyoruz.

## Araştırma kararı

Bu curl ölçümünü şu aşamada yarışmanın ana bulgusu olarak seçmiyoruz.
Bir sonraki çalışma için daha doğrudan ölçülebilen soru:

**Combine'da ölçülen koşu/hızlanma özellikleri, çaylak maçlarındaki hareket
özelliklerine ne ölçüde taşınıyor ve klasik 40-yard süresine ek bilgi sağlıyor mu?**

Bu soru için oyun takip dosyalarından yalnız snap sonrası canlı oyun aralığını
ayıklamak, oyuncu başına yeterli pozisyon sayısını denetlemek ve aykırı tek kare
hızları yerine sağlam hız özetleri üretmek gerekir. Hızın maça taşınması ile
genel futbol başarısı birbirine eşit kabul edilmemelidir. Analiz henüz yapılmadı.

## Çıktılar

- `forward_year_comparison.png`: bütün karşılaştırmalar ve belirsizlik aralıkları.
- `forward_year_scores.csv`: model hataları ve örneklem sayıları.
- `forward_year_predictions.csv`: oyuncu bazlı tahminler.
- `route_coverage_counts.csv`: yıl, rota ve savunma türü kapsamı.
- `outcome_reliability.csv`: tek/çift kayıt kararlılık kontrolü.
- `feature_quality_by_year.csv`, `rejections_by_year.csv`: özellik kalite özetleri.
- `design.json`: analiz tasarımı ve sınırlar.

Yeniden çalıştırma: `python scripts/wr_route_analysis.py`.
Ön koşul: `python scripts/wr_pilot.py` çıktıları mevcut olmalı.
