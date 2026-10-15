# Kaynak ve lisans bildirimi

Paketlenen yeni ham veri dosyaları:

- `raw/international.zip`: Mart Jürisoo, International football results from 1872 to present. Kaynak: https://github.com/martj42/international_results ; yayımlanan lisans CC0 1.0: https://github.com/martj42/international_results/blob/master/LICENSE . `results.csv` skorları uzatma dahil, penaltı atışları hariçtir. Kaynak README'si upstream Wikipedia/RSSSF gibi kaynakları belirtir; üçüncü taraf bütün upstream hakları ayrıca doğrulanmış sayılmaz.
- `raw/openfootball.json` ve `raw/openfootball-discovery.json`: OpenFootball football.json, https://github.com/openfootball/football.json ; CC0 1.0: https://github.com/openfootball/football.json/blob/master/LICENSE.md . Keşif yanıtı resmî GitHub tree API'sinden alınmıştır.
- `raw/worldcup.json`: OpenFootball worldcup.json, https://github.com/openfootball/worldcup.json ; CC0 1.0: https://github.com/openfootball/worldcup.json#license . Eski biçimdeki final skoru otomatik 90 dakika sayılmaz.

CC0 özeti ve tam metni: https://creativecommons.org/publicdomain/zero/1.0/ ve https://creativecommons.org/publicdomain/zero/1.0/legalcode . Özgün byte'lar değiştirilmeden paketlenmiştir. `snapshot-index.json` URL, SHA-256, headers ve gerçek alınma zamanını taşır. `reports/phase2/*/dataset.json` bu kaynaklardan filtrelenmiş/türetilmiş veri, model çıktıları ise bu projedeki hesaplamalardır.

Fjelstul'un 1.248 satırlık canlı yanıtı geliştirme ortamında doğrulandı; ham veri bu pakete eklenmedi. Bu GitHub veri tabanının yayımlanan lisansı CC-BY-SA 4.0: https://github.com/jfjelstul/worldcup#the-license . TheSportsDB'nin 5 kayıtlık yanıtı da paketlenmedi; ücretsiz geliştirme API'si ile erişildi. OpenLigaDB Aşama 1 cache'i tekrar ayrıştırıldı; ODbL koşulları Aşama 1 belgelerinde korunur. Yeni OpenLigaDB keşif özeti tam veri tabanı değildir; kaynak ve hash'i `discovery-summary.json` içindedir.

Yayımlayanın lisans bildirimi kaydedilir; bu kayıt bütün üçüncü taraf hakları için hukukî garanti değildir. Yeni kaynaklar için otomatik kullanım izni doğrulanmadan adapter etkinleştirilmez.
