# Teslim dosyaları

## Önce sonucu oku

Proje kökündeki `SONUC.md` Türkçe özettir. İngilizce yarışma yazısı
`writeup_en.md` içindedir. Sonuç: ölçülebilir bir hız ilişkisi var; klasik
testlere tutarlı ek tahmin faydası gösterilemedi.

## Kaggle'a taşıma

1. Yarışmada bir Notebook oluştur ve `receiver_speed_translation.ipynb`
   dosyasını içe aktar. Yarışma verisini notebook'a ekle.
2. CPU ile **Run All** çalıştır. Notebook dosya konumlarını otomatik bulur;
   bütün hesaplamaları ham CSV'lerden yapar ve internet gerektirmez.
3. Notebook çıktılarındaki sayıları yerel sonuçlarla karşılaştır; kaydedilmiş
   sürümü yarışmanın istediği görünürlükte yayımla.
4. Writeup alanına `writeup_en.md` içeriğini aktar. Markdown'daki yerel görsel
   yolları web bağlantısı değildir: `figures/` içindeki iki resmi Kaggle editörüne
   yükleyip karşılık gelen yerlere ekle. Sonuç tablosunu da koru.
5. Çalıştırılmış notebook bağlantısını writeup'a ekle; ekip/kategori bilgilerini
   doldur ve güncel yarışma ekranındaki teslim koşullarını kontrol ederek Submit yap.

Yazı yaklaşık 1.200 kelime, iki görsel ve bir sonuç tablosundan oluşur. Bu
sayım taslak içindir; Kaggle editörüne taşıdıktan sonra son biçimi kontrol et.
Notebook yerelde doğrulanmıştır; Kaggle üzerinde bu oturumda çalıştırılmamıştır.

## Yerelde yeniden çalıştırma

Proje kökünde:

```powershell
python scripts/extract_speed_data.py
python scripts/analyze_speed_transfer.py
python scripts/speed_robustness.py
```

Notebook'u üretme ve bağımsız çalıştırma:

```powershell
.\.venv\Scripts\python.exe scripts/build_submission_notebook.py
.\.venv\Scripts\python.exe scripts/verify_submission.py
```

Notebook yerelde açılırsa `data/nfl-big-data-bowl-2027` dizinini arar. Farklı
konum için `NFL_DATA_DIR` ortam değişkeni CSV klasörünü göstermelidir.
`NFL_WORK_DIR` çıktı klasörünü değiştirebilir. Kaggle'da bunlar gerekli değildir.

## Dosya ayrımı

- `.ipynb`: temiz, çalıştırılabilir kaynak notebook.
- `.executed.ipynb`: yerel doğrulama çıktıları ve gömülü grafikler bulunan sürüm.
- `writeup_en.md`: İngilizce anlatım.
- `figures/`: yazı görselleri.
- `verification.json`: paketleme sırasında kopyalanan doğrulama özeti.

Kaggle herkese açık bağlantısı bu pakette bulunmaz; henüz yükleme yapılmadı.
