# Koç odaklı kabul soruları

Bu liste geliştirme ve değerlendirme hedefidir; mevcut MVP bu analizlerin tamamını henüz yapamaz.
Takım, oyuncu ve sezonlar veri kataloğundan seçilir. Takım kapsamı eksikse cevap yalnızca temsil edilen oyunculara aittir.
REG, PRE ve POST ayrı değerlendirilir. Öneriler gözlemsel bulgulardan türetilen deneme önerileridir, kanıtlanmış nedensel etkiler değildir.

## 1. Pas korumasında kime yardım vermeliyim?
**Soru:** “Takımımızın verideki OL oyuncularından hangileri üçüncü hak ve uzun mesafede en çok baskı veriyor? Yardım bloklaması için kimi önce incelemeliyim?”
- Ölçüm: pressure_allowed oranı ve etiketli snap paydası; sack_allowed; down, yards_to_go, lined_up_position.
- Karar: Film incelemesi ve yardım koruması denemesinde öncelik sırası.
- Kabul: En az iki mesafe grubu, yeterli/yetersiz örneklem ayrımı; doğrudan bire bir rakip eşleşmesi uydurulmaması.

## 2. Alıcının rota kullanımını nasıl değiştirebilirim?
**Soru:** “Seçtiğim alıcı hangi rotalarda adam ve alan savunmasına karşı daha verimli? Hangi rotaları antrenmanda öne çıkarmalıyız?”
- Ölçüm: route_ran, team_coverage_man_zone, target, rec_yards, separation_at_pass_forward.
- Karar: Rota ve savunma türü bazında çalışma öncelikleri.
- Kabul: Rota koşusu ile hedef alınan pas paydalarının ayrılması; ayrışma metriğinin yalnızca dolu kayıtlarda hesaplanması.

## 3. Üçüncü hakta hangi pas seçeneklerini incelemeliyiz?
**Soru:** “Üçüncü hakta 3–6 yard gerektiğinde, verideki hangi alıcı ve rota seçenekleri daha sık yeni hak kazandırmış?”
- Ölçüm: down, yards_to_go, route_ran, target, yards_gained, play_nullified_by_penalty.
- Karar: Kritik haklar için incelenecek rota–oyuncu seçenekleri.
- Kabul: Ceza ile iptal edilen oyunlar ayrılır; yards_gained >= yards_to_go yalnızca yard temelli dönüşüm vekilidir, resmi first-down etiketi değildir.

## 4. Rakibin pas baskısına nasıl hazırlanmalıyız?
**Soru:** “Rakibin dataset içindeki pass-rusher oyuncularından kimler en hızlı baskıyı üretiyor? Pas koruma çalışmasında önceliğimiz kim olmalı?”
- Ölçüm: time_to_pressure, quick_pressure, blitzing, sack, player_get_off ve geçerli fırsat tanımı.
- Karar: Hızlı pas ve yardım koruması için film inceleme öncelikleri.
- Kabul: Sack sayısı tek başına sıralama değildir; baskı süresi yalnızca baskı oluşan kayıtlara koşulluysa açıkça belirtilir.

## 5. Kırmızı bölgede hangi seçenekler öne çıkıyor?
**Soru:** “Rakibin son 20 yardında, takımımızın temsil edilen oyuncuları hangi diziliş ve rota seçeneklerinde daha iyi sonuç almış?”
- Ölçüm: yardline_side, yardline_number, possession_team, offense_formation, route_ran, expected_points_added.
- Karar: Red-zone antrenmanında incelenecek seçenekler.
- Kabul: Hücum yönüne göre rakip kale mesafesi doğru hesaplanır; oyun EPA'sı oyuncu satırlarından tekrar toplanmaz; oyuncuya nedensel katkı olarak atanmaz.

## 6. Yakaladıktan sonraki yardı kim daha iyi üretiyor?
**Soru:** “Alıcılarımızdan kimler beklenenin üzerinde yakalama sonrası yard üretiyor ve bunu hangi rotalarda yapıyor?”
- Ölçüm: yards_after_catch - expected_yards_after_catch, route_ran, rec_yards.
- Karar: YAC odaklı oyun tasarımları için oyuncu adayları.
- Kabul: Yalnızca gerçekleşmiş yakalamalar ve iki ölçümün de mevcut olduğu kayıtlar; örneklem ve aykırı oyun etkisi gösterilir.

## 7. Atletik kapasitesi maç kullanımına yansımayan kim?
**Soru:** “Combine'da hızlı olan hangi oyuncular maçta aynı hareket kapasitesini göstermiyor? Hangi oyuncunun rolünü veya hareket tekniğini inceleyelim?”
- Ölçüm: combine_results, combine_tracking, game_tracking; pozisyon ve hareket türüne göre normalize edilmiş özellikler.
- Karar: Bireysel hareket ve teknik inceleme listesi.
- Kabul: Dril çıkış sprinti ayrı tutulur; düşük maç hızı isteksizlik veya yeteneksizlik diye yorumlanmaz.
- Durum: Tracking özellikleri gerektirir.

## 8. Genç oyunculardan kim gerçekten gelişiyor?
**Soru:** “İki sezonda da kaydı bulunan oyuncularımızdan kimlerin fırsat başına performansı gelişmiş, kimlerin yalnızca oynama süresi artmış?”
- Ölçüm: Oyuncu–sezon snap/fırsat sayıları ve pozisyona uygun oranlar.
- Karar: Bireysel gelişim ve rotasyon inceleme öncelikleri.
- Kabul: Hacim ile verimlilik ayrılır; pozisyon, sezon türü ve rol değişimi belirtilir; zaman damgasız kariyer toplamları yıllık veri gibi kullanılmaz.

## 9. Aynı rol için hangi oyuncuyu denemeliyiz?
**Soru:** “A ve B oyuncusunu aynı pozisyon ve benzer oyun koşullarında karşılaştır. Hangi koşullarda hangisini denememiz daha mantıklı?”
- Ölçüm: Pozisyona göre koruma, rota veya baskı verileri; hak, mesafe ve diziliş.
- Karar: Rol bazlı rotasyon denemesi.
- Kabul: Küçük gruplarda kesin üstünlük iddiası yok; sağlık, sözleşme ve antrenman performansı bilinmiyor diye belirtilir.

## 10. Bu haftanın üç antrenman önceliği ne olmalı?
**Soru:** “Seçtiğim takım ve sezon için verideki en önemli üç gelişim alanını belirle. Her biri için kanıt, denenebilir çalışma önerisi ve takip metriği ver.”
- Ölçüm: Önceki araçların sonuçlarının sentezi.
- Karar: Önceliklendirilmiş haftalık çalışma planı.
- Kabul: Her öneride ölçüm, payda, kaynak, belirsizlik ve takip metriği; temelsiz kazanma yüzdesi veya garanti yok.

## Her cevapta beklenen biçim
1. Kısa sonuç.
2. Sayısal kanıt: sezon/tür, kayıt sayısı, payda, karşılaştırma grubu.
3. Koç için denenebilir aksiyon.
4. Takip edilecek ölçüm.
5. Kapsam ve belirsizlik; gerekliyse cevap için eksik veri.

## Değerlendirme
- Sayıların araç sonuçlarıyla bire bir uyuşması.
- Doğru payda, sezon türü ve oyun tekilleştirmesi.
- Örneklem yetersizliğinde sıralama/tahmin zorlanmaması.
- Kaynak gösterilmesi; gözlem ile önerinin ayrılması.
- Önerinin koçun uygulayabileceği ve sonradan ölçebileceği kadar somut olması.
