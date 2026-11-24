# Ekip çalışma düzeni

## Sıralı yol haritası

| Sıra | Görev | Ön koşul |
| --- | --- | --- |
| 1 | [Veri doğruluğu ve kapsam](https://github.com/aliberk1/NFL/issues/1) | Başlamaya hazır |
| 2 | [Oyuncu profili ve karşılaştırma](https://github.com/aliberk1/NFL/issues/2) | #1 |
| 3 | [Araştırma entegrasyonu](https://github.com/aliberk1/NFL/issues/3) | #2 |
| 4 | [Güvenilir yapay zekâ sohbeti](https://github.com/aliberk1/NFL/issues/4) | #3 |
| 5 | [Test, performans ve hata takibi](https://github.com/aliberk1/NFL/issues/5) | #4 |
| 6 | [Docker ve paylaşılabilir demo](https://github.com/aliberk1/NFL/issues/6) | #5 |
| 7 | [GitHub sunumu ve ürün sürümü](https://github.com/aliberk1/NFL/issues/7) | #6 |
| 8 | [Benzer oyuncu ve model araştırması](https://github.com/aliberk1/NFL/issues/8) | #7 |

[Alınabilir görevler](https://github.com/aliberk1/NFL/issues?q=is%3Aissue%20is%3Aopen%20label%3Astatus%3Aready) · [Devam eden işler](https://github.com/aliberk1/NFL/issues?q=is%3Aissue%20is%3Aopen%20label%3Astatus%3Ain-progress)

Testler her görevin teslim şartıdır; beşinci aşama testlere başlama değil, kapsamı ve performans kontrollerini genişletme aşamasıdır.

## Görev seçme ve devralma

1. GitHub Issues içinde `status:ready` etiketli bir görev seçin.
2. Assignees alanından kendinizi atayın. Yetkiniz yoksa görev altına “Bu görevi almak istiyorum” yazın; depo sahibi sizi davet edip atayabilir.
3. Görev otomatik olarak `status:in-progress` olur. Bir görev için bir ana sorumlu belirleyin.
4. `task/<issue-numarasi>-kisa-ad` isimli dal açın.
5. Kabul kriterlerini tamamlayıp testleri çalıştırın.
6. Pull request açın; açıklamaya `Closes #123` biçiminde görev numarası ekleyin.
7. Başka bir ekip üyesinin incelemesinden sonra PR birleştirilir. GitHub ilgili görevi kapatır ve sonraki görevin kilidi açılır.

Görev devri için tamamlananları, kalan işleri ve dal/PR bağlantısını yorum olarak bırakın; Assignees alanını yeni sorumluyla güncelleyin.

## Durumlar

| Etiket | Anlamı |
| --- | --- |
| `status:blocked` | Önceki görev tamamlanmadan bitirilemez |
| `status:ready` | Ön koşullar tamam; bir ekip üyesi alabilir |
| `status:in-progress` | Ön koşullar tamam; sorumlu atanmış |
| `status:done` | Görev kapatılmış |

## Bağımlılık kilidi

Görev açıklamasındaki `<!-- depends-on: 123 -->` satırı otomasyon içindir. Birden fazla ön koşul virgülle yazılır. Başlangıç görevinde liste boştur.

- `roadmap` etiketli görevlerin durumları otomatik güncellenir.
- Ön koşul hem kapalı hem de **Completed** olarak işaretlenmiş olmalıdır. **Not planned** sonraki görevi açmaz.
- Ön koşulları tamamlanmamış görev kapatılırsa otomasyon yeniden açar.
- Önceki görev yeniden açılırsa ona bağlı görevler tekrar kilitlenir.
- PR için `dependency-gate` ön koşulları, `tests` uygulama testlerini kontrol eder.
- Ön koşul kapandıktan sonra açık PR'daki eski başarısız kontrolü **Re-run all jobs** ile yeniden çalıştırın.
- Etiketler takılırsa Actions → Issue dependencies → Run workflow kullanılabilir.

Bu mekanizma işin kalitesini tek başına doğrulamaz. Kabul kriterlerini inceleyen kişi kontrol eder. Hazırlık ve tartışma yapılabilir; sonraki aşamanın teslimi ön koşullara bağlıdır. Yetkili yöneticiler kuralları değiştirebilir.

## Depo sahibinin sorumluluğu

- Arkadaşları Settings → Collaborators bölümünden davet etmek.
- Her göreve bir ana sorumlu ve PR'a farklı bir inceleyen atamak.
- `main` dalında PR, bir inceleyen onayı ve `dependency-gate` / `tests` kontrollerini zorunlu tutmak.
- Anahtarı, ham veriyi veya yerel ortam dosyalarını commit etmemek.

## Tamamlanma tanımı

Kod, ilgili testler, gerekiyorsa ekran görüntüsü ve belge güncellemesi PR'da bulunmalı; görevdeki kabul kriterleri karşılanmalı ve inceleme tamamlanmalıdır. Sadece kod yazılması görevin tamamlandığı anlamına gelmez.
