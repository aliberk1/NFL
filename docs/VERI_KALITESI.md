# Veri doğruluğu ve kapsam

Uygulama beş yerel CSV kullanır: players, games, combine_results,
player_career_successes ve player_play. Tracking dosyaları bu veritabanına
yüklenmez. Kaynak, her dosyanın SHA-256 özeti, UTC yükleme zamanı, kapsanan
sezonlar ve birleşik veri sürümü data/curated/catalog.json içinde tutulur.
data/curated/quality_report.json aynı bilgilere ek olarak her kolondaki
eksik değer sayısını, tekrar anahtar gruplarını, anahtar eşleşmelerini ve
doğrulama hatalarını içerir. data/ yereldir; raporlar depoya eklenmez.

python -m pipelines.ingest zorunlu kolonları ve DuckDB tarafından okunan
tiplerini denetler. Şema beklentileri pipelines/ingest.py içindeki SCHEMA
tanımındadır. Oyuncu, maç, Combine ve kariyer kayıtları kendi anahtarlarıyla;
oyuncu-oyun kayıtları (game_id, play_id, nfl_id) ile tekil olmalıdır.
Kritik alanlar boş olamaz. player_play, combine_results ve
player_career_successes oyuncu anahtarları players ile; player_play
maç anahtarı games ile eşleşmelidir. Başarısız yükleme mevcut veritabanının
yerine geçmez.

Eksik metrik değeri null olarak kalır; sıfır sayılmaz. Örneğin sack
etiketi olmayan satırların toplamı null, etiketli sıfır değerlerinin
toplamı 0 olur. sack sayısal bir alandır; 0.5 gibi kesirli değerler
toplamda korunur. Oranların paydası olarak kullanılan etiketli oyun sayısı
ayrıca gösterilir.

Oyuncu aramasındaki **Kayıtlı takımlar** listesi tüm gözlenen
player_play satırlarından türetilir; güncel kadro veya güncel takım
bilgisi değildir. Sezon performansı her takım için ayrı satırda gösterilir.
Bir oyuncu sezon içinde takım değiştirmişse takımlardaki oranları basitçe
ortalama almak doğru değildir.

Bu veri tam takım kadrosunu veya bütün maçları temsil etmez. Bir oyuncunun
gözlenen maç ve etiketli oyun sayısı azsa oranları güçlü performans kanıtı
saymayın. Pozisyonlar farklı fırsatlara sahiptir: pressure_allowed
özellikle hücum hattı, rec_yards pas yakalayıcılar, rush_yards koşu
rolleri, sack savunma rolleri için yorumlanır. Farklı pozisyonlar arasında
tek metrikle genel yetenek sıralaması yapılmamalıdır. PRE, REG ve POST
maçları ayrı gruplardır. Kariyer toplamları zamansız anlık görüntülerdir.
