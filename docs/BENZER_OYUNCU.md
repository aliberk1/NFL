# Benzer oyuncu analizi ve ileri-yıl deneyi

## Ürün kuralları

`app/similarity.py` yalnızca fiziksel Combine ölçümlerini karşılaştırır. Draft sırası, NGS puanları,
kariyer toplamları ve maç sonuçları kullanılmaz.

| Grup | Pozisyonlar | Ölçütler |
| --- | --- | --- |
| OL | C, G, T | boy, ağırlık, kol, 10 yard, dikey, uzun atlama, kısa mekik |
| WR / TE | WR / TE (ayrı) | boy, ağırlık, kol, 10 yard, 40 yard, dikey, uzun atlama, 3 koni |
| RB | RB, FB | boy, ağırlık, 10 yard, 40 yard, dikey, uzun atlama, kısa mekik |
| DL | DE, DT, NT | boy, ağırlık, kol, 10 yard, dikey, uzun atlama, 3 koni, kısa mekik |
| LB | OLB, ILB, MLB | boy, ağırlık, kol, 10 yard, 40 yard, dikey, uzun atlama, kısa mekik |
| DB | CB, DB, FS, SS | boy, ağırlık, kol, 10 yard, 40 yard, dikey, uzun atlama, 3 koni |

- **Ölçekleme:** Her ölçüm, oyuncunun kendisi dışındaki havuzun standart sapmasına bölünür. Ağırlıklar eşittir.
- **Mesafe:** Ortak ölçümlerdeki standart farkların karekök ortalaması.
- **Eksik veri:** Doldurulmaz ve sıfır sayılmaz. Grup ölçütlerinin en az %60'ı ve en az dördü ortak olmalıdır.
- **Havuz:** En az 10 oyuncu yoksa liste gösterilmez. QB, K, P ve tanımsız pozisyonlar kapsam dışıdır.
- **Belirsizlik:** Havuz büyüklüğü, ortak ölçüm sayısı, ölçüm çıkarma mesafe aralığı ve listede kalma oranı gösterilir. Aralık güven aralığı değildir.

Benzerlik gelecekte eşit başarı anlamına gelmez.

## Deney tasarımı

Soru: Geçmiş draft sınıflarındaki benzer oyuncuların ortalaması, sonraki sınıfın hareket ölçümünü basit
ortalamadan daha iyi tahmin eder mi?

- 2023 → 2024 ve 2023–2024 → 2025; eğitim her zaman test sınıfından öncedir.
- Referanslar: eğitim ortalaması, pozisyon ortalaması, Ridge (alpha 10).
- Ana model k=5; k=3 ve k=7 duyarlılık kontrolüdür. Ayarlar ilk çalıştırmadan önce sabitlendi ve sonuçtan sonra değiştirilmedi.
- Ölçekleme ve medyan doldurma yalnızca eğitim oyuncularından öğrenilir. Testler, test sınıfı sonuçlarının tahmini etkilemediğini doğrular.
- Yeterli ortak ölçümü olmayan test oyuncusunda eğitim ortalamasına dönülür ve sayısı kaydedilir.
- %95 aralıklar, eğitim ve test oyuncularını yeniden örnekleyip modelleri yeniden kuran 2.000 bootstrap ile hesaplanır. Yinelenen eğitim oyuncuları komşu modelinde yaklaşıklık yaratır.

## Sonuçlar

Hedefler: WR için çaylak sezonu rota zirve hızı, OL için erken yanal hız (veri birimi).

| Grup / test | Eğitim / test oyuncusu | Ortalama MAE | Ridge MAE | Benzer 5 MAE | Azalma (%95 aralık) |
| --- | ---: | ---: | ---: | ---: | ---: |
| WR 2024 | 22 / 20 | 0,299 | 0,279 | 0,252 | +0,047 [−0,077, +0,128] |
| WR 2025 | 42 / 16 | 0,225 | 0,186 | 0,232 | −0,006 [−0,131, +0,086] |
| OL 2024 | 17 / 16 | 0,116 | 0,128 | 0,134 | −0,018 [−0,069, +0,013] |
| OL 2025 | 33 / 17 | 0,113 | 0,112 | 0,128 | −0,014 [−0,062, +0,020] |

**Sonuç: Tutarlı tahmin faydası gösterilemedi.** Dört testin üçünde benzer oyuncu modeli ortalamadan
kötüdür ve bütün aralıklar sıfırı içerir. Uygulama bu yüzden benzerlikten tahmin üretmez.

## Sınırlar ve bağımsız doğrulama

- Yeni sezon verisi ve ham yarışma CSV'leri bulunmadığından **bağımsız doğrulama yapılmadı**. Sonuçlar kayıtlı araştırma tablolarından hesaplandı.
- Aynı oyuncu ve yıllar önceki çalışmalarda incelendi; analiz keşifseldir ve çoklu karşılaştırma düzeltmesi içermez.
- Testlerde 16–20 oyuncu vardır. Yalnızca Combine'a katılıp maç kaydı bulunanlar dahildir.
- Diğer pozisyon grupları için tahmin değerlendirmesi yapılmadı.
- Ürün ekranı gerçek yarışma veritabanıyla denenmedi; kurgusal veri ve testlerle doğrulandı.

## Yeniden üretim

```sh
python -m scripts.evaluate_similarity          # hesapla ve kaydet
python -m scripts.evaluate_similarity --check  # kayıtla karşılaştır
```

Veri özetleri, kod özetleri, ayarlar, sürümler ve skorlar birlikte
[summary.json](../reports/similarity/summary.json) dosyasındadır; oyuncu düzeyinde satır içermez.
