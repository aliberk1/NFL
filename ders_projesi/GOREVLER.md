# Ekip görevleri: ders projesinin devamı

Bu belge, `YAPILANLAR.md`'de anlatılan ilk aşamadan sonra yapılacak işleri tanımlar. Her görev
tek başına okunabilir: amaç, arka plan, adım adım yapılacaklar, teknik ayrıntılar, kabul
kriterleri ve dikkat edilecek noktalar yazılıdır. Başlamadan önce `YAPILANLAR.md` ve `TASARIM.md`
okunmalıdır.

## Herkes için ortak kurallar

1. **Veri:** yalnızca NFL Big Data Bowl 2027 yarışma verisi. Dış veri kullanılmaz. Ham veri
   `data/nfl-big-data-bowl-2027/` altına konur; `data/` `.gitignore`'dadır, **asla commit edilmez**.
2. **Ortam:** `python3 -m venv .venv-ml && .venv-ml/bin/pip install -r requirements-ml.txt`.
   Komutlar repo kökünden `.venv-ml/bin/python -m ders_projesi.<betik>` biçiminde çalıştırılır.
3. **Ön kayıt:** yeni bir deney (model, hedef, hipotez) **sonuçlara bakmadan önce** `TASARIM.md`'nin
   sonuna tarihli bir bölüm olarak yazılır. Sonuç görüldükten sonra hipotez, eşik, metrik veya
   model seçme kuralı değiştirilmez; değişirse gerekçesiyle ayrı bir "sonradan değişiklik" notu eklenir.
4. **Sızıntı yok:** her ön işleme adımı (doldurma, ölçekleme, kodlama, özellik seçimi) yalnız eğitim
   katmanında öğrenilir. Test verisi, model seçiminde veya eşik ayarında kullanılmaz.
5. **Ortak arayüz:** yeni modeller `modeller.py`'deki `fit(ctx, idx)` / `predict(ctx, idx)` arayüzünü
   uygular; değerlendirme `degerlendirme.py`'deki fonksiyonlarla yapılır (yeniden yazılmaz).
6. **Rapor:** her betik kendi `ciktilar/<görev>/RAPOR.md` dosyasını ve grafiklerini üretir; rapordaki
   sayılar elle yazılmaz. Grafikler `grafikler.py`'deki sabit renk sırasını kullanır.
7. **Git:** her görev kendi branch'inde (`task/<no>-<kısa-ad>`), `task/ders-projesi-tahmin-modelleri`
   branch'inden açılır; bitince ona pull request açılır. `ciktilar/cache/` commit edilmez.
   PR açıklamasında hangi görevin kapatıldığı yazılır; depodaki PR kontrolü (dependency gate)
   açıklamadaki görev bağımlılıklarını okur.
8. **CI:** `.github/workflows/pull-request.yml` her PR'de Python 3.11 ile `ruff` ve `pytest` çalıştırır.
   CI'da ham veri yoktur; yazılan testler gerçek veriye ihtiyaç duymamalıdır.

## Görev listesi

| # | Görev | Tür | Ne zaman başlanabilir? |
|---|---|---|---|
| G1 | Ders projesi için otomatik test paketi | Yazılım | Hemen |
| G2 | Tek komutla tüm hattı çalıştırma ve Python 3.11 ortamı | Yazılım | G1 bittikten sonra (testlerle doğrulanır) |
| G3 | Streamlit uygulamasına "Tahmin" sekmesi | Yazılım | Hemen |
| G4 | Hiperparametre araması ile dayanıklılık (iç içe CV) | Makine öğrenmesi | Hemen |
| G5 | C1 genişletme: dizi modelleri karşılaştırması ve hata analizi | Derin öğrenme | Hemen |
| G6 | C2: pas korumada baskı yeme tahmini (yeni görev) | Derin öğrenme | Hemen (G5'in eğitim döngüsü yeniden kullanılabilir) |
| G7 | B1 genişletme: pozisyon bazında ve ikinci sezon analizi | Makine öğrenmesi | Hemen |
| G8 | Final raporu ve sunum güncellemesi | Rapor | En son: diğer görevlerin sonuçları geldikçe |

**Görev alma:** Görevler kişiye atanmamıştır; isteyen istediği görevi alır. Aynı görevin iki kişi
tarafından yapılmaması için görevi alan kişi ekibe haber verir (veya GitHub Issue'ya kendini atar).
Tek zorunlu sıralama: **G2, G1'den sonra**; **G8 en son**. Diğer görevler paralel yürütülebilir.

---

## G1. Ders projesi için otomatik test paketi

**Amaç:** `ders_projesi/` kodunun doğru çalıştığını ham veri olmadan, CI'da otomatik doğrulamak.

**Arka plan:** Şu an ders projesinin hiç testi yok. Depodaki mevcut testler (`tests/`) yalnız
uygulamayı (`app/`, `pipelines/`) kapsıyor. CI ham veriye erişemez; bu yüzden testler küçük,
**sentetik** (kurgusal) veriyle çalışmalı. `pipelines/demo_data.py` benzer bir yaklaşımla kurgusal
uygulama verisi üretir; ondan fikir alınabilir ama ders projesi ek dosyalara
(`combine_tracking.csv`, `game_tracking_<yıl>.csv`) ihtiyaç duyar.

**Yapılacaklar:**
1. `tests/ders_projesi/conftest.py` içinde bir pytest fixture'ı yaz: `tmp_path` altında 9 CSV'nin
   hepsini aynı sütun adlarıyla, küçük boyutta üretsin (ör. 3 draft sınıfı × 20 oyuncu; her oyuncuya
   2–3 combine denemesi, 10 Hz, 40–60 kare; her sezon 4 maç × 20 oyun; route etiketli oyunlarda
   `ball_snap` olayı). Sabit `numpy.random.default_rng(seed)` kullan.
2. Fixture, `ders_projesi.veri.DATA`, `ders_projesi.veri.OUT` ve `ders_projesi.ozellikler.CACHE`
   yollarını `monkeypatch` ile geçici klasöre yönlendirsin (gerçek `ciktilar/` asla yazılmamalı).
3. Yazılacak testler (en az):
   - `veri.load_players`: `start_rate` hesabı (elle hesaplanmış küçük örnekle), `y_starter` eşik
     davranışı (tam 0.5 pozitif), draft edilmeyen oyuncuda `pick_filled == 262`.
   - `ozellikler.tracking_summary`: her oyuncu için tek satır; z-skorlarının drill içinde ortalaması ≈ 0.
   - `ozellikler.build_sequences`: dizi şekli `[deneme, 200, 4]`, maskenin geçerli kare sayısına eşit
     olması, önbellek dosyasının ikinci çağrıda kullanılması.
   - **Sızıntı testi:** `SkModel.fit` sonrası pipeline'daki `SimpleImputer.statistics_` değerlerinin
     yalnız eğitim indekslerinden hesaplanan medyana eşit olması.
   - `degerlendirme.corrected_ttest`: aynı iki dizi için `t = 0, p = 1`; elle hesaplanan bir örnekle sayısal eşitlik.
   - `degerlendirme.holm`: bilinen p değerleri için literatürdeki düzeltilmiş değerler.
   - `degerlendirme.cv_splits`: her tekrarda her örnek tam bir kez testte.
   - `modeller.CNNModel`: 2 epoch ile `fit/predict` çalışır, çıktılar [0, 1] aralığında ve uzunluk doğru.
     CI'da GPU yoktur; `DEVICE` CPU'ya düşmelidir (kod bunu zaten yapıyor, test bunu doğrulasın).
   - `gorev_c1.handcrafted`: düz ileri koşan sentetik bir yolda `final_dir ≈ 0`, `max_dx > 0`.
   - Duman testi: `gorev_a2.main()` sentetik veriyle hatasız biter ve `RAPOR.md` üretir.
4. `pytest -q` yerelde ve CI'da geçmeli. Toplam süre CI'da 2 dakikayı geçmemeli (küçük veri, az epoch).
5. CI'daki `ruff check` satırına `ders_projesi` ve yeni test klasörü eklensin; çıkan uyarılar düzeltilsin.

**Kabul kriterleri:** tüm yeni testler geçer; testler gerçek veri olmadan çalışır; hiçbir test
`ders_projesi/ciktilar/` altına yazmaz; CI yeşil.

**Dikkat:** CI Python 3.11 kullanır, yerel ortam 3.9'dur. `torch` CI'da kurulu değildir
(`requirements-dev.txt`'e bakın); ya CPU sürümü `requirements-dev.txt`'e eklenmeli ya da CNN testleri
`pytest.importorskip("torch")` ile korunmalıdır. Hangisinin seçildiği PR'de yazılmalı.

---

## G2. Tek komutla tüm hattı çalıştırma ve Python 3.11 ortamı

**Amaç:** Projeyi sıfırdan kuran birinin tek komutla bütün sonuçları yeniden üretebilmesi.

**Yapılacaklar:**
1. `ders_projesi/hepsi.py` (veya `Makefile`): sırayla `gorev_a`, `ileri_tahmin`, `gorev_a2`,
   `gorev_b1`, `gorev_c1` çalıştırsın; her adımın süresini ve başarısını `ciktilar/calisma_ozeti.json`'a yazsın;
   bir adım hata verirse durup hangi adım olduğunu söylesin. `--quick` seçeneği tüm görevlerin hızlı
   sürümünü çalıştırsın (az tekrar, 2 CNN epoch).
2. Python 3.11 ile yeni bir ortam kurulsun; `requirements-ml.txt` sürümleri 3.11'de çözülüyorsa
   güncellensin (numpy 2.x, scikit-learn 1.7, torch 2.8). Bütün görevler 3.11'de çalıştırılıp
   sonuçların 3.9 sonuçlarıyla aynı olduğu (sklearn modellerinde birebir; CNN'de ±0,01 içinde) doğrulansın;
   fark tablosu PR'ye eklensin.
3. 3.11'de `tests/test_similarity.py` dahil tüm uygulama testlerinin geçtiği doğrulansın
   (3.9'daki tek başarısızlık `zip(strict=True)` kaynaklıdır).
4. README'deki kurulum bölümü güncellensin (macOS/Linux ve Windows komutları).

**Kabul kriterleri:** temiz bir klonda iki komut (`pip install`, `python -m ders_projesi.hepsi`)
tüm `RAPOR.md` dosyalarını üretir; 3.9 ve 3.11 sonuç karşılaştırması belgelenmiştir.

**Dikkat:** CNN sonuçları donanıma (MPS / CUDA / CPU) göre küçük farklar gösterebilir; bu normaldir
ama raporda belirtilmelidir. `torch.use_deterministic_algorithms` denenebilir.

---

## G3. Streamlit uygulamasına "Tahmin" sekmesi

**Amaç:** Modellerin tahminlerini uygulamada gösterilebilir hâle getirmek (sunumda canlı demo).

**Arka plan:** Uygulama (`app/ui.py`) dört sekmeye sahip: Oyuncu analizi, Araştırma, Sohbet, Veri
kapsamı. Tahmin modelleri uygulamaya bağlı değil; sohbet "gelecek tahmini yapamam" diye cevap veriyor.
Uygulama, araştırma çıktılarını SHA-256 manifestleriyle doğrulayarak okur (`app/analytics.py`,
Araştırma sekmesi örneği) — aynı desen izlenmeli.

**Yapılacaklar:**
1. Uygulama içinde **model eğitilmez**; yalnız ders projesinin ürettiği CSV'ler okunur:
   - `ciktilar/gorev_a/y_starter/oof_tahminler.csv` (510 oyuncu, model başına OOF olasılık),
   - `ciktilar/ileri_tahmin/gelecek_tahminleri.csv` (2024–2025 sınıfları, 3 sezon tahmini),
   - `ciktilar/gorev_b1/tahmin_2026.csv` (2025 sınıfı, 2026 tahmini).
   Bu dosyalar için bir manifest (`dosya yolu → SHA-256`) üretilsin ve uygulama okurken doğrulasın.
2. `app/analytics.py`'ye salt okunur bir `player_forecast(nfl_id)` fonksiyonu ekle: oyuncunun
   draft bilgisi, model olasılıkları, gerçekleşen sonuç (varsa) ve "sonuç ne zaman belli olacak" alanı.
3. `app/ui.py`'ye "Tahmin" sekmesi: oyuncu arama → seçili oyuncu için kart:
   - Draft öncesi modeller (Draft / Combine / Hepsi) ve olasılıkları,
   - Gerçek sonuç (2023 sınıfı için kesin; 2024–2025 için "şimdiye kadar" + "henüz belli değil"),
   - Model doğrulama skoru (ör. "Bu model 2023 sınıfında AUC 0,92") ve kısa açıklama,
   - Uyarı metni: tahminin olasılık olduğu, kesinlik olmadığı.
4. İsteğe bağlı: sohbet asistanına aynı fonksiyonu bir araç (tool) olarak ekle (`app/assistant.py`'deki
   araç tanımları deseniyle); sayı denetimi mekanizması korunmalı.
5. `tests/test_ui.py` ve `tests/test_app.py` desenleriyle testler: dosya yokken sekme hata vermeden
   bilgi mesajı gösterir; manifest uyuşmazlığında veri gösterilmez; örnek oyuncu için doğru değerler.

**Kabul kriterleri:** sekme gerçek veriyle ve tahmin dosyaları yokken çalışır; testler geçer;
ekran görüntüsü PR'ye eklenir.

**Dikkat:** Kurgusal demo modu (`pipelines/demo_data.py`) gerçek tahmin göstermemeli; demo modunda
sekme gizlenmeli veya "demo verisinde tahmin yok" yazmalı.

---

## G4. Hiperparametre araması ile dayanıklılık (iç içe CV)

**Amaç:** "Model ayarları aranmadı" sınırını kaldırmak: ayarlanmış modellerle de ana bulgunun
(draft sırası en iyisi, Combine katkı yapmaz) geçerli olup olmadığını test etmek.

**Yapılacaklar:**
1. Önce `TASARIM.md`'ye ön kayıt: hipotez "Ayar araması sonrası da Combine+Takip+Draft, Draft'ı
   anlamlı biçimde geçmez (Holm p ≥ 0,05)".
2. İç içe çapraz doğrulama (nested CV): dış döngü mevcut 5×5 bölmeler (`cv_splits` ile aynı tohum);
   iç döngü 3-katlı `GridSearchCV` veya `RandomizedSearchCV` (`scoring="roc_auc"`), yalnız dış
   eğitim katmanında.
3. Arama uzayları (öneri): LogReg `C ∈ {0.01, 0.1, 0.3, 1, 3, 10}`; RandomForest
   `max_depth ∈ {3, 5, None}`, `min_samples_leaf ∈ {1, 3, 10}`, `max_features ∈ {sqrt, 0.5}`;
   GradBoost `learning_rate ∈ {0.03, 0.1}`, `max_depth ∈ {2, 3, 5}`, `max_iter ∈ {100, 300}`;
   SVM `C ∈ {0.3, 1, 3}`, `gamma ∈ {scale, 0.01, 0.1}`.
4. `ders_projesi/gorev_a_ayar.py` olarak ayrı betik; Görev A'nın ana hedefi ve 4 özellik seti.
   CNN dahil edilmez (maliyet); gerekçe raporda.
5. Rapor: ayarlı ve ayarsız AUC'lerin yan yana tablosu; seçilen ayarların katmanlar arası dağılımı;
   Draft referansına karşı düzeltilmiş t-testi + Holm.

**Kabul kriterleri:** test verisi hiçbir zaman ayar seçiminde kullanılmamış (kodla gösterilir);
hipotez sonucu raporda açıkça yazılı.

**Dikkat:** İç içe CV pahalıdır; `n_jobs=-1` ve `RandomizedSearchCV(n_iter=20)` ile süre sınırlanabilir.

---

## G5. C1 genişletme: dizi modelleri karşılaştırması ve hata analizi

**Amaç:** Rota tanımada 1D-CNN'i başka derin öğrenme mimarileriyle karşılaştırmak ve hataların
nedenlerini anlamak.

**Arka plan:** C1'de 1D-CNN makro-F1 0,735 ile en iyi model. En zor sınıflar SLANT (0,72; CROSS ve
HITCH ile karışıyor), SCREEN (0,68; FLAT ile karışıyor) ve DİĞER (0,00; 2025'te yalnız 74 örnek).
Veri hazırlığı `gorev_c1.build_sequences` içinde; önbellek `ciktilar/cache/route_sequences.npz`.

**Yapılacaklar:**
1. Ön kayıt (`TASARIM.md`): karşılaştırılacak modeller, ana metrik (makro-F1), test (gruplu 5-katlı +
   2025 zaman testi, McNemar).
2. Yeni modeller (PyTorch, `RouteCNN` ile aynı eğitim döngüsü ve erken durdurma):
   - **GRU** (2 katman, 64 gizli birim, maskeli son durum),
   - **LSTM** (aynı boyut),
   - **Temporal Convolutional Network** veya daha derin CNN (residual bloklar),
   - isteğe bağlı küçük **Transformer encoder** (2 katman, 4 başlık, konum kodlaması).
3. **Veri artırma (augmentation)** denemesi (yalnız eğitimde): küçük gürültü, ±%10 zaman ölçekleme.
   Yanal aynalama **yapılmamalı** (iç/dış anlamını bozar).
4. **Girdi uzunluğu analizi:** 1,0 / 2,0 / 3,5 sn pencerelerle CNN; rota ne kadar erken tanınabiliyor?
   (Bu, sahada "rota kaç saniyede belli oluyor" sorusuna cevap verir.)
5. **Hata analizi:** en çok karışan 3 sınıf çifti için yanlış sınıflanan örneklerin yol grafikleri;
   `lined_up_position` (WR / SLOT_WR / TE) bazında F1; DİĞER sınıfı için ayrı karar (çıkarmak mı,
   birleştirmek mi) — bu karar ön kayıtta yazılmalı.
6. Sonuçlar `ciktilar/gorev_c1_genisletme/` altına.

**Kabul kriterleri:** tüm modeller aynı bölmelerde; en iyi model için McNemar sonucu; pencere
uzunluğu grafiği; hata analizi bölümü.

**Dikkat:** İç/dış yönü top konumu olmadan saha merkezine göre yaklaşık belirleniyor; hata analizinde
bu yaklaşımın IN/OUT karışmasına etkisi ayrıca incelenmeli (oyuncunun başlangıç `y`'si saha merkezine
yakın olan örneklerde F1 düşüyor mu?).

---

## G6. C2: Pas korumada baskı yeme tahmini (yeni görev)

**Amaç:** Pas korumadaki bir oyuncunun (çoğunlukla OL), oyunun ilk anlarındaki hareketinden o oyunda
baskı yiyip yemeyeceğini tahmin etmek; oyun düzeyinde derin öğrenmeyi ikinci bir problemde sınamak.

**Veri (doğrulandı):** `player_play.pressure_allowed` 60.803 oyunda dolu, 189 oyuncu, pozitif oran
%8,2 (4.974 oyun). Sürekli alternatif hedef: `peak_pressure_probability_allowed` (58.028 oyun).

**Yapılacaklar:**
1. Ön kayıt (`TASARIM.md`): hedef, pencere, metrikler (nadir sınıf olduğu için **PR-AUC ana metrik**,
   ROC-AUC ek), hipotez.
2. Girdi: `ball_snap` anından itibaren ilk 1,0–1,5 sn (10–15 kare) — **pencere, baskının gerçekleştiği
   andan önce bitmeli**; aksi hâlde model sonucu "görür" (hedef sızıntısı). `time_to_pressure_allowed`
   dağılımına bakılarak pencere seçilmeli ve gerekçelendirilmeli.
3. Önemli sınır: maç takip verisinde yalnız bu 510 oyuncu var; savunmacı (pass rusher) görünmez.
   Bu, raporda baştan yazılmalı ve beklentiler buna göre kurulmalı.
4. Modeller: taban (pozisyon + oyun bağlamı ile LogReg: `down`, `yards_to_go`, `offense_formation`,
   `dropback_duration` hariç — o oyun sonrasında belli olur), el ile çıkarılmış hareket özellikleri
   ile GradBoost, 1D-CNN. Bölme: oyuncuya göre gruplu 5-katlı + 2023–24 → 2025 zaman testi.
5. Oyun tahminlerinden oyuncu düzeyine toplama: oyuncunun sezonluk ortalama tahmini baskı oranı,
   gerçek baskı oranıyla ve bir sonraki sezonun baskı oranıyla ilişkisi (Spearman).

**Kabul kriterleri:** sızıntı kontrolü raporda açıkça gösterilmiş (pencere sonu < baskı anı);
PR-AUC taban çizgisi (%8,2) ile karşılaştırma.

---

## G7. B1 genişletme: pozisyon bazında ve ikinci sezon analizi

**Amaç:** B1'de çaylak sezonunun katkısı küçük ve anlamsız çıktı (+0,028 AUC, p = 0,076). Bu katkının
belirli pozisyonlarda veya sonraki sezonlarda daha belirgin olup olmadığını incelemek.

**Yapılacaklar:**
1. Ön kayıt (`TASARIM.md`).
2. **Pozisyon bazında:** OL, DB, WR, DL için ayrı ayrı (en az ~15 pozitif olan gruplar) Draft vs
   Draft+Çaylak AUC; az örnek nedeniyle bootstrap GA ile raporlanmalı, Holm düzeltmesi pozisyonlar arası.
3. **Pozisyona özgü çaylak özellikleri:** OL için baskı yeme oranı ve `peak_pressure_probability_allowed`
   ortalaması; WR/TE için `separation_at_pass_forward` ortalaması ve rota başına hedeflenme; DL için
   `player_get_off` ortalaması ve `time_to_pressure`. Sütunlar `player_play.csv`'de mevcut (doğrulandı).
4. **İkinci sezon → üçüncü sezon:** 2023 sınıfı için 2024 verisiyle 2025'i tahmin; çaylak → ikinci
   sezon sonucuyla karşılaştır (bilgi zamanla artıyor mu?).
5. `sezon.py`'deki `play_season_stats` genişletilsin; mevcut sütunlar ve B1 sonuçları değişmemeli
   (regresyon testi: B1 yeniden çalıştırıldığında aynı AUC).

**Kabul kriterleri:** pozisyon tablosu GA'larla; ikinci sezon analizi; B1 sonuçları değişmemiş.

---

## G8. Final raporu ve sunum güncellemesi

**Amaç:** Bütün görevleri tek, tutarlı bir dönem raporunda ve sunumda birleştirmek.

**Yapılacaklar:**
1. `ders_projesi/FINAL_RAPOR.md` (sonra PDF'e çevrilebilir). Önerilen yapı:
   Özet · Giriş ve problem · Veri ve bütünlük denetimi · Yöntem (özellikler, modeller, doğrulama,
   istatistik) · Görev A · Gelecek tahmini · A2 · B1 · C1 · (G4–G7 sonuçları) · Tartışma · Sınırlar ·
   Yazılım mimarisi ve testler · Kaynakça · Ekler (ön kayıt metni).
2. Her sayı ilgili `ciktilar/*/RAPOR.md` veya CSV'den alınır ve dipnotla kaynağı belirtilir.
   Elle yuvarlama tutarlı olmalı (AUC 3 basamak, p değerleri 2 anlamlı basamak).
3. Kaynakça en az şunları içermeli: Nadeau & Bengio (2003) düzeltilmiş t-testi; Holm (1979);
   Friedman testi (Demšar, 2006, *JMLR*); McNemar (1947); Efron & Tibshirani bootstrap; 1D-CNN için
   temel bir kaynak. Kaynaklar okunarak doğrulanmalı, künyeler kontrol edilmeli.
4. Sunum: mevcut 14 slaytlık hoca sunumuna (sahibi paylaşmalı) A2, B1, C1 ve yeni görevlerin
   sonuç slaytları eklenir; "Yol haritası" slaytı güncellenir. Her slaytta tek fikir; sayılar raporla aynı.
5. Bulguların dili: "anlamlı değil" ile "etkisi yok" ayrımı korunmalı (B1 buna örnek: yön pozitif,
   önceden belirlenen ölçüte göre anlamsız).

**Kabul kriterleri:** rapordaki her sayı bir çıktı dosyasına izlenebilir; ön kayıt ile sonuç her
hipotez için yan yana; sunum ve rapor sayıları birebir aynı.
