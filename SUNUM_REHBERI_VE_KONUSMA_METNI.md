# Hocalara Sunum Rehberi ve Birebir Konuşma Metni

Bu belge, projeksiyon veya ekranda **[`SUNUM_HOCALARA.html`](file:///d:/NFL/SUNUM_HOCALARA.html)** slayt sunumunu açtığında her slaytta **kelimesi kelimesine ne anlatacağını** ve **hocaların sorabileceği zor sorulara nasıl cevap vereceğini** içerir.

> **Sunumu Nasıl Açacaksın?**
> 1. Bilgisayarında [`d:\NFL\SUNUM_HOCALARA.html`](file:///d:/NFL/SUNUM_HOCALARA.html) dosyasına çift tıkla (Chrome / Edge / Firefox'ta internet gerekmeden açılır).
> 2. Klavyeden **`F`** tuşuna basarak tam ekran yapabilirsin.
> 3. Klavyeden **`N`** tuşuna basarak sağdaki **"Konuşmacı Notları"** panelini açıp kapatabilirsin (projeksiyona yansıtırken `N` ile gizleyip bu metinden takip edebilirsin).
> 4. Klavyeden **`→` (Sağ Ok)** veya **`Boşluk (Space)`** tuşuyla bir sonraki slayta geçebilirsin.

---

## Slayt 1: Kapak — "En Hızlı Kısım Çıkış Sprinti" (Süre: ~45 saniye)

**Hocalara Söyleyeceğin Metin:**
> "Sayın hocalarım, bugün **NFL Big Data Bowl 2027** yarışması kapsamında yürüttüğümüz çalışmayı sunacağım. Yarışmanın ana teması, Amerikan futbolunda draft öncesi seçmelerde (**NFL Scouting Combine**) sporcuların üzerindeki `10 Hz` sensör çiplerinden alınan takip verilerinin, sporcuların NFL'deki gerçek maç performanslarına ne ölçüde aktarıldığını modellemekti.
> Biz çalışmamızda 510 oyuncuyu, 43 Combine drilini ve 22.6 milyon satırdan fazla maç takip verisini taradık ve literatürde çok kritik bir **ölçüm tuzağı (phase contamination)** keşfettik: Hücum hattı oyuncularının yanal çevikliğini ölçmek için yapılan 3 Combine drilindeki **470 kaydın 470'inde (%100)** en yüksek hız hedef hareket sırasında değil, dril sonundaki düz çıkış sprintinde oluşuyor."

---

## Slayt 2: Problem Tanımı ve 4-Aşamalı Doğrulama Hunisi (Süre: ~1 dakika)

**Hocalara Söyleyeceğin Metin:**
> "Bir sensör kaydı düdükten duruşa kadar her şeyi kaydeder. Eğer bir veri bilimci dril dosyasının tamamı üzerinden maksimum veya 95. yüzdelik hız alırsa, amaçlanan futbol hareketini mi ölçüyor yoksa dril bitişindeki düz koşuyu mu?
> Biz bu problemi çözmek için **4-Aşamalı Doğrulama Hunisi** adını verdiğimiz bir metodoloji geliştirdik:
> 1. **Faz İzolasyonu:** Sinyal işleme ile hedef hareketi çıkış sprintinden ayırmak.
> 2. **Tekrar Güvenilirliği (Repeatability):** Aynı oyuncunun tekrarlı denemeleri arasındaki tutarlılığı ($r_{XX}$) ölçmek.
> 3. **Maç İçi Erken Hareket Transferi:** Drildeki hareketin maçın ilk 1.5 saniyesindeki aynı eksenli harekete taşınıp taşınmadığını kontrol etmek.
> 4. **İleri-Yıl Maç Tahmini (Out-of-Time Prediction):** Gelecek draft sınıflarında klasik ölçümlerin üzerine istatistiksel olarak anlamlı ek katkı sağlayıp sağlamadığını sınamak."

---

## Slayt 3: Veri Mimarisi ve Sızıntısız Kohort Seçimi (Süre: ~1 dakika)

**Hocalara Söyleyeceğin Metin:**
> "Deneysel tasarımımızda veri sızıntısını (data leakage) ve kıdem yanlılığını (exposure bias) önlemek için iki katı kural uyguladık:
> Birincisi, 2023, 2024 ve 2025 draft sınıflarındaki tüm oyuncuları **yalnızca çaylak (1. yıl) normal sezonlarında** değerlendirdik; böylece eski sınıfların daha fazla maç tecrübesine sahip olmasından doğacak yanlılığı sıfırladık.
> İkincisi, iki ayrı pozisyon grubu üzerinde çalıştık: Ana çalışmamızda **Offensive Line (C, G, T)** pozisyonunda **470 Combine kaydını** ve 50 çaylak oyuncunun **20.853 bire bir pas koruma pozisyonunu** modelledik. Karşılaştırmalı ikinci çalışmamızda ise **58 çaylak Wide Receiver** oyuncusunun **10.944 pas rotası** üzerinde `40-yard dash` hız aktarımını inceledik."

---

## Slayt 4: Sinyal İşleme ve Kinematik Faz Ayrıştırması (Süre: ~1.5 dakika)

**Hocalara Söyleyeceğin Metin:**
> "Bu slayt sinyal işleme yöntemimizi gösteriyor. `Pass-Pro Mirror` drilinde oyuncu önce koçu ayna gibi takip ederek yanal ($y$ ekseninde) kayma hareketi yapar, dril sonunda ise ileri doğru ($+x$ yönünde) bir çıkış sprinti atar.
> Biz önce 5-kare ikinci dereceden **Savitzky–Golay filtresi** ile $y(t)$ konumunu yumuşatıp zamana göre türev alarak yanal hızı ($v_y(t)$) elde ettik. Ardından başlangıçtaki ilk 5 karenin medyan $x_0$ konumundan **+1.5 yard** ileriye en az `0.4 saniye` boyunca kalıcı ayrılmayı çıkış sprinti başlangıcı olarak tanımladık.
> Sağdaki grafiklerde 2023, 2024 ve 2025 sınıflarından örnek oyuncuların saha izlerini görüyorsunuz: Mavi çizgiler yanal ayna fazını, kırmızı noktalar tespit ettiğimiz yön değişimlerini, turuncu kısım ise çıkış sprintini gösteriyor. **Kabul edilen 113 kaydın 113'ünde de (%100) zirve hız turuncu çıkış sprintinde oluşuyor.** Üstelik çıkış sınırını `1.0` veya `2.0 yard` yaptığımızda oyuncu sıralamaları `Spearman r = 0.992` ve `0.998` ile neredeyse hiç değişmiyor."

---

## Slayt 5: 3 OL Drilinde Evrensel Çıkış Baskınlığı ve Sıralama Kırılması (Süre: ~1.5 dakika)

**Hocalara Söyleyeceğin Metin:**
> "Bu bulgunun sadece tek bir drile özgü olmadığını kanıtlamak için Offensive Line oyuncularının girdiği diğer iki ayak işi drilini — `5-Yard Wave Shuffle` (118 kayıt) ve `Pass Rush Drop` (239 kayıt) — da fazlarına ayırdık.
> Sonuç evrenseldir: **Toplam 470 kaydın 470'inde (%100.0)** zirve hız çıkış sprintinde oluşmaktadır.
> Sol panelde gördüğünüz gibi, oyuncuları tüm kaydın hızına göre sıralamak ile izole edilmiş yanal ayna hızına göre sıralamak arasındaki korelasyon **Spearman $r = +0.005$**, yani birbirine tamamen diktir!
> 2025 sınıfında üst çeyreğe giren 9 oyuncudan **yalnızca 1 tanesi** her iki sıralamada ortaktır. Örneğin ilk tur seçimi **Donovan Jackson** tüm kayıt hızında `2.9.` yüzdelikteyken, çıkış sprinti temizlendiğinde yanal hızda `94.1.` yüzdeliğe (**+91.2 puan**) fırlamaktadır; **Darnell Wright** ise `97.3.` yüzdelikten `8.1.` yüzdeliğe (**−89.2 puan**) düşmektedir."

---

## Slayt 6: Tekrar Güvenilirliği ve Psikometrik Zayıflama Sınırı (Süre: ~1.5 dakika)

**Hocalara Söyleyeceğin Metin:**
> "Burada çok önemli bir teorik soruyu yanıtlıyoruz: Fazı doğru ayırdıktan sonra bile, tek tekrarlı dril ölçümleri neden maç performansını tahmin ederken sınırlı kalıyor?
> Klasik psikometrik ölçüm teorisindeki **zayıflama (attenuation) teoremine** göre, iki değişken arasındaki gözlenen korelasyon, her iki ölçümün kendi tekrar güvenilirliklerinin çarpımının karekökünü aşamaz: $|r_{XY}| \le \sqrt{r_{XX} \cdot r_{YY}}$.
> `Pass Rush Drop` drilinde **118 oyuncunun ikişer denemesi** var. Bu iki denemeyi karşılaştırdığımızda:
> - Oyuncunun kendi temposunda koştuğu **çıkış sprinti hızı** denemeden denemeye **`r = +0.510`** ile tekrarlanırken,
> - Karşısındaki koçun el/vücut işaretine göre yaptığı **yanal pas seti hızı** yalnızca **`r = +0.104`** tekrar güvenilirliğine sahip!
> Çünkü koç her oyuncuya aynı hızda ve ritimde işaret vermiyor. Ayrıca maçtaki ikili baskı etiketinin yarı-yarıya (split-half) güvenilirliği `r = 0.367` iken, sürekli NGS baskı olasılığı kullanıldığında bu güvenilirlik **`r = 0.696`**'ya çıkıyor."

---

## Slayt 7: İki Aşamalı (Two-Stage) Sızıntısız Modelleme Mimarisi (Süre: ~1 dakika)

**Hocalara Söyleyeceğin Metin:**
> "Maç tahmininde iki aşamalı ve sıfır veri sızıntılı bir mimari kurduk:
> **1. Aşamada (Oyun Bağlam Modeli):** Yalnızca eğitim yıllarındaki maçları kullanarak oyuncunun diziliş pozisyonu (`C/G/T`), hücum formasyonu, hak (`down`), mesafe (`yards_to_go`) ve oyun kurucunun topu elinde tutma süresi (`dropback_duration`) için beklenen baskı olasılığını tahmin ettik ve her oyuncu için **Gözlenen eksi Beklenen (Observed − Expected)** baskı ortalamasını çıkardık.
> **2. Aşamada (Oyuncu Modeli):** Sabit $\alpha = 10$ cezalı Ridge regresyonu ile **2023 sınıfıyla eğitip 2024 sınıfını**, **2023–2024 ile eğitip 2025 sınıfını** tahmin ettik. Hiçbir oyuncu eğitim ve test kümesinde ortak yer almadı; eksik değer ataması (median imputation) ve ölçekleme (StandardScaler) yalnızca eğitim verisi üzerinde fit edildi."

---

## Slayt 8: Bire Bir Pas Koruması Tahmin Sonuçları (Süre: ~1.5 dakika)

**Hocalara Söyleyeceğin Metin:**
> "Üç farklı hedef tanımında (Birincil süre düzeltmeli ikili baskı, süre düzeltmesiz ikili baskı ve sürekli NGS zirve baskı olasılığı) elde ettiğimiz ileri-yıl test sonuçları üç net bulgu veriyor:
> 1. **Çıkış sprintiyle kirlenmiş tüm-kayıt hızını (`whole_drill_speed`) modele eklemek, 2025 yılında her üç hedef tanımında da tahmin hatasını (MAE) kötüleştiriyor** (örneğin birincil modelde hata `2.502`'den `2.652` yüzde puana çıkıyor).
> 2. **Faz ayrıştırmalı mirror özelliklerimiz (`lateral_speed_p75` ve `reversal_recovery`)** ise 2025'te hem birincil ikili baskıda (`2.502 → 2.482 yp`) hem de daha yüksek güvenilirlikli sürekli NGS baskı olasılığında (`2.189 → 2.157 yp`, RMSE `2.639 → 2.532 yp`) hatayı doğru yönde düşürüyor.
> 3. **Bilimsel Dürüstlük ve Belirsizlik:** Hem eğitim hem test oyuncularını sınıf içinde yeniden örnekleyip her iki aşamadaki modelleri **400 kez baştan eğittiğimizde (full-refit bootstrap)**, 2025 yılındaki iyileşmenin %95 güven aralığı **`[−0.264, +0.353]` yüzde puan** olarak sıfırı kesiyor. Dolayısıyla faz ayrıştırması gürültüyü temizlese de, tek tekrarlı dril verisinin klasik Combine testlerine (`40-yard`, `10-yard split`, `kilo`, `kol boyu`) kıyasla tek başına kesin bir üstünlük sağlamadığını dürüstçe raporluyoruz."

---

## Slayt 9: Ara Hareket Kontrolü (0–1.5 s) ve 7 Fiziksel Değişmezlik Testi (Süre: ~1 dakika)

**Hocalara Söyleyeceğin Metin:**
> "Baskı sonucu rakip oyuncu ve takım şemasından etkilendiği için, bir de ara yapı geçerliliği (construct validation) testi yaptık: Combine'daki yanal hız, maçın ilk `1.5 saniyesindeki` yanal hıza doğrudan taşınıyor mu?
> `20.110` geçerli oyunda aynı Savitzky–Golay türevini hesapladık. Oyuncuların maç içi erken yanal hızı maçtan maça çok kararlı (**split-half `r = 0.797`**), ancak Combine yanal hızıyla korelasyonu zayıf (`ham r = 0.053`, `yıl ve pozisyon içi r = 0.120`). Çünkü gerçek maçta bir hücum hattı oyuncusu drildeki gibi maksimum hızla yana koşmaz; rakibin hamlesine göre kontrollü adım atar.
> Sağ tarafta ise sinyal işleme kodumuzun koordinat öteleme, yansıtma, zaman kaydırma ve satır karıştırma altında $10^{-9}$ hassasiyetle tam değişmez (invariant) olduğunu kanıtlayan 7 sentetik birim testimizi görüyorsunuz."

---

## Slayt 10: Karşılaştırmalı İkinci Çalışma — Wide Receiver Rota Hızı (Süre: ~1 dakika)

**Hocalara Söyleyeceğin Metin:**
> "Offensive Line çalışmamızın yanında, **Wide Receiver (pas yakalayıcı)** pozisyonu için de tam kapsamlı bir ikinci çalışma yürüttük. 81 WR oyuncusunun ikişer `40-yard dash` denemesini ve 58 çaylak WR'nin `10.944` pas rotasını inceledik.
> İki pozisyon arasındaki karşılaştırma metodolojimizi çok güzel tamamlıyor:
> - WR `40-yard` zirve hızı çok yüksek tekrar güvenilirliğine (**`r = 0.893`**) ve maç rota hızıyla anlamlı korelasyona (**`r = 0.382`**) sahip. Ancak klasik `40-yard` kronometre süresiyle **`r = −0.852`** oranında örtüştüğü için aynı bilgiyi tekrar ediyor (2024'te MAE'yi %15.1 düşürürken 2025'te düşürmüyor).
> - OL `Mirror` yanal hızı ise klasik testlerden bağımsız yeni bir eksen ölçüyor, fakat koç yönlendirmeli olduğu için tekrar güvenilirliği düşük (`r = 0.104`) kalıyor."

---

## Slayt 11: Yazılım Çıktıları ve Etkileşimli Karar Destek Aracı (Süre: ~1 dakika)

**Hocalara Söyleyeceğin Metin:**
> "Çalışmamızın tüm çıktıları tamamen yeniden üretilebilir (reproducible) bir yazılım paketi olarak hazırlandı.
> 113 Offensive Lineman'ın tamamını draft yılı, pozisyon ve sıralama farkına göre filtreleyen, saha izlerini ve hız fazlarını canlı çizen iki dilli (`TR / EN`) bir web uygulaması ([`mirror_explorer.html`](file:///d:/NFL/submission_mirror/mirror_explorer.html)) geliştirdik.
> Ayrıca Kaggle Notebook'umuz ham CSV dosyalarından izole bir ortamda sıfırdan çalıştırılarak üretilen 8 tablonun tamamının birebir eşleştiği doğrulandı."
> *(İstersen bu slaytta ekrandaki bağlantıya tıklayıp `mirror_explorer.html` sayfasını 15 saniye canlı gösterebilirsin!)*

---

## Slayt 12: Sonuç, Öneriler ve Soru-Cevap (Süre: ~1 dakika)

**Hocalara Söyleyeceğin Metin:**
> "Sonuç olarak NFL kulüplerine ve Combine organizasyonuna üç somut öneri sunuyoruz:
> 1. **Dosya adına değil, hareket fazına göre ölçüm yapın:** OL drillerinde `1.5–2.2 yard` çıkış sprintini ayırmadan hız yüzdeliği hesaplamayın.
> 2. **Dril işaretlerini standartlaştırın ve en az 2 tekrar alın:** İnsan/koç işareti yerine standart ışık veya ekran sinyali kullanmak tekrar güvenilirliğini `r = 0.104` seviyesinden yukarı taşıyacaktır.
> 3. **4-Aşamalı Doğrulama Hunisini zorunlu tutun.**
> Dinlediğiniz için çok teşekkür ederim, sorularınızı memnuniyetle yanıtlayabilirim."

---

## Hocaların Sorabileceği Zor Sorular ve Hazır Cevap Anahtarı

1. **Soru:** *"Neden derin öğrenme (LSTM / Transformer) veya XGBoost/LightGBM kullanmadınız da Lojistik Regresyon ve Ridge Regresyonu kullandınız?"*
   - **Cevabın:** "Çok haklı bir soru hocam. Oyun düzeyinde 20.853 satırımız olsa da, tahmin hedefimiz **oyuncu düzeyinde** geleceği tahmin etmek ve tüm filtreleri geçen çaylak Offensive Lineman sayısı **50 oyuncu** (eğitimde 17–33, testte 16–17 oyuncu). $n=50$ örneklem boyutunda XGBoost veya derin ağlar yüksek varyans nedeniyle gürültüyü ezberler (overfitting). Sabit $\alpha=10$ cezalı Ridge regresyonu hem çoklu doğrusal bağlantıyı (multicollinearity) dengeler hem de hiperparametre aramasından kaynaklanacak test sızıntısını (hyperparameter snooping) tamamen engeller."

2. **Soru:** *"Savitzky–Golay filtresini neden seçtiniz ve parametreleri (pencere=5, derece=2) neye göre belirlendi?"*
   - **Cevabın:** "Sensör verisi `10 Hz` (saniyede 10 kare) olduğu için ham sonlu farklar ($\Delta y / \Delta t$) konum gürültüsünü türevde büyütür. Hareketli ortalama (moving average) ise yön değişimi (reversal) anlarındaki keskin hız tepeciklerini düzleştirip yok eder. **5-kare (`0.5 s`) 2. dereceden Savitzky–Golay filtresi**, yerel parabolik uyum yaptığı için dönüş anlarındaki faz gecikmesini sıfırlar ve ivme/hız tepeciklerini koruyarak türev alır."

3. **Soru:** *"Çıkış sprinti sınırını neden 1.5 yard seçtiniz? Bu eşik keyfi değil mi?"*
   - **Cevabın:** "Bu eşiğin keyfi olup olmadığını test etmek için `1.0 yard` ve `2.0 yard` sınırlarıyla duyarlılık (sensitivity) analizi yaptık. Oyuncuların yanal hız sıralamaları `1.0 yard` sınırında **Spearman $r = 0.992$**, `2.0 yard` sınırında ise **$r = 0.998$** korelasyonla aynı kaldı. Ayrıca 113 oyuncunun tamamının saha izlerini çok sayfalı PDF olarak dışarı aktarıp görsel olarak da doğruladık."

4. **Soru:** *"Modelinizin 2025'te sağladığı iyileşmenin güven aralığı sıfırı içeriyor (`[-0.264, +0.353]`). O halde bu çalışma olumsuz (null) bir sonuç mu?"*
   - **Cevabın:** "Çalışmamız iki kısımdan oluşuyor hocam: **Birincisi kesin ve pozitif bir ölçüm keşfidir** — 470 OL kaydının %100'ünde zirve hızın çıkış sprintinde olduğunu ve tüm-kayıt hızının sıralamaları tamamen bozduğunu (`r = 0.005`) ilk kez nicel olarak kanıtlıyoruz. **İkincisi ise metodolojik doğrulamadır:** Çıkış sprintiyle kirlenmiş hız modeli 2025'te hatayı kötüleştirirken, bizim izole ettiğimiz faz özellikleri hatayı düşürüyor; fakat koç yönlendirmeli drilin tekrar güvenilirliği düşük (`r = 0.104`) olduğu için bu fark istatistiksel olarak dar kalıyor. Bunu p-hacking ile gizlemek yerine 400 tam yeniden eğitimli bootstrap ve psikometrik zayıflama teoremiyle açıklamak çalışmamızın en güçlü akademik yönüdür."

