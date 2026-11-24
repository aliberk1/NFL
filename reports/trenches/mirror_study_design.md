# İkinci araştırma: Mirror testinin doğru fazını ölçmek

## Sorunun seçilmesi

OL/DL veri kapsamı ve üç yıldan ham rota örnekleri incelendi. Henüz Combine
özellikleri ile OL maç sonuçları arasında ilişki veya tahmin testi yapılmadı.
OL seçildi çünkü pressure_allowed açık 0/1 gözlem içeriyor, tek savunmacıyla
eşleşen pozisyonları ayırabiliyoruz ve mirror testindeki iki hareket fazı
koordinatlarda görülebiliyor. DL'deki quick_pressure alanı çoğunlukla yalnız
baskı oluştuğunda dolu; eksikleri doğrudan başarısızlık diye kodlamak uygun değil.

## Hipotez

Mirror testinin yanal hareket fazındaki hız ve dönüş sonrası toparlanma,
oyuncunun çaylak sezonunda bire bir pas korumasında izin verdiği baskıya dair
klasik ölçümlere ek bilgi taşıyabilir. Tam testteki en yüksek hızın çıkış
sprintinden gelmesi, faz ayırmadan çıkarılan özelliği görevden uzaklaştırabilir.

## Sonuçları görmeden sabitlenen tanımlar

- Oyuncular: T/G/C; rookie REG; iptal edilmeyen oyun; sahada T/G/C dizilimi.
- Fırsat: pressure_allowed dolu ve pass_rushers_encountered == 1.
- Birincil örneklem: oyuncu başına en az 100 uygun pas koruması ve geçerli mirror testi.
- Faz: ilk beş karenin medyan x konumundan 1.5 birim ileriye çıkışın en az
  0.3 saniye sürmesi ilk çıkış kabul edilir. Öncesi mirror fazıdır.
- Kalite: en az 3 saniyelik mirror, zaman tekrarları yok, kare aralığı <=0.21 s.
- Y konumu beş-kare Savitzky–Golay filtreyle yumuşatılır; türev yanal hızdır.
- Dönüş: yanal hız işaret değiştirir; önceki/sonraki 0.4 saniyede en az
  0.25 birim hareket vardır. Yakın adaylar 0.6 saniye içinde birleştirilir.
- Ana özellikler: mirror fazındaki mutlak yanal hızın %75 yüzdeliği ve
  dönüşten 0.3–0.6 saniye sonraki yanal hızın dönüşten 0.5–0.2 saniye önceki
  hıza oranının dönüşler üzerindeki medyanı. Ön hız >=0.5; en az iki dönüş.
- Deneme tekrarı varsa oyuncu medyanı. Tekrar yoksa tekrar güvenilirliği iddia edilmez.
- Negatif/karşılaştırma özelliği: bütün kaydın üç-kare medyan s değerinin %95 yüzdeliği.
- Klasik model: forty, ten_yd_split, combine_weight, arm_length ve oyuncu pozisyonu.
- Bağlam: sahadaki C/G/T, down, yards_to_go, offense_formation, dropback_duration
  ve karesi; eğitim oyunlarında lojistik regresyon. Oyuncu hedefi ortalama
  (gerçek baskı - beklenen baskı), yani koşullu baskı artığı.
- Bu nedensel yetenek ölçümü değildir; dropback süresi baskıdan da etkilenebilir.
- Oyuncu modelleri: ortalama; klasik; klasik + tüm-test hızı; klasik + iki mirror ölçümü.
- Ridge alpha=10; seçim/ayarlama yok. Ölçekleme/doldurma yalnız eğitimde.
- Birincil değerlendirme: 2023–2024 -> 2025. Ek ileri yıl kontrolü: 2023 -> 2024.
- Birincil metrik: oyuncu başına eşit ağırlıklı MAE. RMSE ve koşullu eşleştirilmiş
  oyuncu-bootstrap fark aralığı da raporlanır. Yıllar ayrı gösterilir.
- Önceden tanımlı duyarlılık: dropback süresi olmadan aynı bağlam modeli;
  bu ana analizin yerine geçirilmez.
- Ölçüm geometrisi: faz sınırı 1.0 ve 2.0 ile aynı özelliklerin sıralama
  kararlılığı kontrol edilir; maç sonucu kullanılarak sınır seçilmez.
- Deneme listesi ve bütün sonuçlar, önceki WR çalışmalarına eklenir.

## Durma/ilerleme ölçütü

2025'te veya farklı makul bağlam tanımında iyileşme tekrarlanmıyorsa özellik
ana futbol başarı metriği olarak önerilmez. Veri fazı sorunu yine teknik bulgu
olarak raporlanabilir. Sonuç pozitif çıksa bile aynı verideki keşif geçmişi ve
küçük oyuncu sayıları nedeniyle bağımsız doğrulama iddiası kurulmaz.
