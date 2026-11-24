# Hız aktarımı araştırması — sonuç hesaplanmadan belirlenen tasarım

Önceki curl/separation denemeleri ek fayda göstermedi. Yeni soru, testteki koşu
özelliklerinin maç içindeki rota koşu hızına taşınıp taşınmadığıdır. Bu bir
oyuncunun genel başarısı veya savunmacıyı geçebilmesiyle eşdeğer değildir.

## Sabit kapsam

- Yalnız WR; her oyuncunun draft yılına karşılık gelen normal sezonu.
- İptal edilmeyen, rota etiketi bulunan oyunlar.
- Ana maç ölçümü: snap sonrası, pas atılana kadar (en çok ilk 4 saniye),
  üç-kare hareketli medyan hızın %95 yüzdeliği. En az 2 saniye, 20 kare;
  pozisyon başına snap ve pass_forward olayları zorunlu.
- Ana örneklem: en az 30 uygun oyun ve 40-yard tracking kaydı.
- Maç bağlamı: rota, savunma türü, ölçüm süresi ve karesi, snap hızı,
  başlangıç savunmacı mesafesi. Bu bağlam modeli yalnız eğitim oyuncularında
  öğrenilir; oyuncu hedefi bağlam artıklarının ortalamasıdır.
- Combine özellikleri: üç-kare medyan hızın %95 yüzdeliği ve hızın ilk kez
  1'i geçtiği andan bir saniye sonraki hız. Eşik hız birimindedir; resmi
  sözlük alınana kadar birim adı kullanılmaz. Denemeler oyuncu başına medyanlanır.
- Klasik karşılaştırma: 40-yard süresi, boy ve kilo.
- Modeller: ortalama referansı; klasik ölçümler; klasik + iki tracking özelliği.
- Tüm modeller Ridge alpha=10; ayarlama veya özellik araması yok.
- 2023 -> 2024 ve 2023+2024 -> 2025 değerlendirmesi. Önceki çalışmalar
  nedeniyle bunlar keşif sonuçlarıdır; tamamen yeni doğrulama seti değildir.
- Ana metrik: oyuncu başına eşit ağırlıklı MAE. Ek: RMSE ve oyuncu düzeyinde
  eşleştirilmiş bootstrap fark aralığı. Tüm yıllar raporlanır.
- Aynı oyunlardan tek/çift kayıt kararlılığı betimsel olarak raporlanır.
- Kontroller: yinelenen anahtar/zaman, zaman aralığı, eksik olay, yetersiz
  pencere, tracking hızının koordinat değişimiyle uyumu, yıllara göre kapsam.

Sonuçlara bakarak eşik değiştirilirse bu ayrı ve açıkça adlandırılmış bir
duyarlılık analizi olmalıdır. Ana tasarımın yerine geçirilmez.
