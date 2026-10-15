# Kaynak uygunluk araştırması

İnceleme tarihi: 14 Ekim 2026. Ücretsiz erişim, açık veri lisansı ve kullanım amacı birbirinden ayrı değerlendirildi. Aşağıdaki kararlar bu özel, sanal para araştırma prototipi içindir. Gelecekte açık yayın/ticari kullanım için yeniden değerlendirme gerekir.

| Kaynak | Veri ve kapsam | Ücretsiz erişim / kota | Kullanım koşulu | Karar ve gerçek erişim |
|---|---|---|---|---|
| OpenLigaDB | Topluluk fikstür/sonuç; prototip Bundesliga 2024/25 | Anahtarsız API; sayısal provider sınırı doğrulanmadı; iç bütçe 4/24 saat | Resmî API ana sayfası ODbL 1.0 bildiriyor; attribution ve türev DB paylaşım koşulları korunmalı | Etkin; gerçek HTTP 200, 306 kayıt. Ayrıntılı lisans sayfası yalnız cookie kabuğu döndü; ana sayfa lisans beyanına dayanıyor. Kamusal türev DB dağıtımı henüz yok |
| OpenFootball football.json | Seçili liglerin fikstür/sonuç JSON'u; otomatik upstream güncelliği garanti değil | Anahtarsız GitHub raw; sayısal ücretsiz raw kota garantisi yok; iç bütçe 4/24 saat | Depo CC0 1.0 / public domain bildiriyor | Etkin; gerçek HTTP 200, 306 kayıt. Saat dilimi ve native match ID eksiklikleri açık tutuldu |
| Football-Data.org | Free kapsamda 12 yarışma, gecikmeli sonuç/fikstür, puan tablosu | Ücretsiz hesap/token; 10 çağrı/dakika | Atıf zorunlu, uygulama başına key, iptalden sonra sitede veriye referans kısıtı, logolar ayrı haklar | Aday; token yok, authenticated endpoint test edilmedi. Ücretsiz plan uzun tarihçe veya odds sağlayacak varsayılmadı |
| The Odds API | Güncel maç öncesi oranlar; spor/bookmaker/market kapsamı endpoint'e bağlı | Free 500 kredi/ay; historical odds ücretsiz değil | 31 Ağustos 2026 koşulları saklama, analiz/model eğitimi ve dashboard'a izin veriyor; ham veri hizmeti olarak yeniden dağıtım yasak | Önerilen sonraki odds adapteri; ücretsiz key ve billing window doğrulaması gerekli; çağrı yapılmadı |
| API-Football | Fikstür/istatistik/predictions/odds; erişim ve sezon kapsamı planla doğrulanmalı | Resmî fiyat tablosu free 100 istek/gün | API koşulları üçüncü taraf veri yayımlama lisansı vermediğini belirtiyor; birden fazla free hesapla limit artırmak yasak | Beklemede; token, kapsam ve haklar ayrıca doğrulanacak |
| StatsBomb Open Data | Seçili geçmiş yarışmalar; olay ve bazı xG/360 verisi | Açık depo; güncel tüm liglerin canlı servisi değil | README araştırma/atıf koşulları var; tam LICENSE.pdf bu oturumda okunamadı | Adapter etkin değil; tam lisans ve amaç uyumu onaylanmadan kullanılmayacak |
| Football-Data.co.uk | Geniş tarihsel sonuç/istatistik/oran CSV | Dosyalar ücretsiz; bu tek başına otomatik kullanım izni değil | Güncel data.php özel bireysel kullanım diyor; otomatik bot/scraper/AI veri eğitimi ürünlerini dışlıyor | Engelli; bu proje için yazılı izin olmadan indirme/adapter yok |
| Diğer tahmin siteleri / sosyal tahminler | Olasılık veya seçimler | Doğrulanmadı | Otomatik erişim, arşiv ve yeniden kullanım izni belirsiz | Keşif kuyruğu; başarı puanı yok, scraping yok |

OpenLigaDB ve OpenFootball'un aynı maçı aynı skorla vermesi iki bağımsız veri üreticisi olduklarını kanıtlamaz. Ortak upstream ilişkileri ayrıca incelenir.

## Resmî referanslar

- OpenLigaDB API ve lisans beyanı: https://api.openligadb.de/index.html ; https://www.openligadb.de/ ; https://www.openligadb.de/lizenz
- API örnekleri: https://github.com/OpenLigaDB/OpenLigaDB-Samples
- ODbL 1.0 yükümlülükleri: https://opendatacommons.org/licenses/odbl/1-0/
- OpenFootball depo, lisans ve güncelleme açıklaması: https://github.com/openfootball/football.json ; https://github.com/openfootball/football.json/blob/master/LICENSE.md
- Football-Data.org ücret/kota: https://www.football-data.org/pricing ; https://docs.football-data.org/general/v4/policies.html
- Football-Data.org sözleşme: https://www.football-data.org/client/register
- The Odds API ücretsiz plan: https://the-odds-api.com/
- The Odds API sözleşme: https://the-odds-api.com/terms-and-conditions.html
- The Odds API kota hesaplaması: https://the-odds-api.com/liveapi/guides/v4/
- API-Football: https://www.api-football.com/ ; https://www.api-football.com/terms
- StatsBomb: https://github.com/hudl/open-data ; https://github.com/hudl/open-data/blob/master/LICENSE.pdf
- Football-Data.co.uk güncel kısıt: https://www.football-data.co.uk/data.php
- Supabase: https://supabase.com/pricing
- Vercel Hobby: https://vercel.com/docs/plans/hobby
- GitHub kullanım/bütçe: https://docs.github.com/en/billing/reference/product-usage-included ; https://docs.github.com/en/billing/how-tos/set-up-budgets

## Oran bütçesi taslağı

The Odds API'de her HTTP çağrısını bir kredi sanmayın: market ve region sayısı maliyeti etkiler. Tek lig/tek region/tek market ve günde 8 birim maliyetli çağrı hedefi 7 günde 56 kredi eder; bu bir hesaplama taslağıdır, mevcut hesabın hakkı değildir. `x-requests-remaining`, `x-requests-used`, `x-requests-last` başlıkları, hesap sıfırlanma zamanı, paylaşılan key tüketimi ve güvenlik rezervi okunmadan üretim çağrısı açılmayacak. Ücretsiz tarihsel odds yoksa mevcut andan ileri snapshot biriktirilir.

## Atıf ve veri dağıtımı

OpenLigaDB verisinden üretilen yayınlarda kaynak ve ODbL bağlantısı gösterilir. ODbL kapsamındaki uyarlanmış veritabanının halka açılması, aynı lisansla erişim sağlama gibi yükümlülükler doğurabilir. Bu teslim yalnız kod, araştırma ve toplama kanıtı/aggregate sayılar içerir; tam kaynak verisi paketlenmez. Yerel indirme ile kamuya yeniden dağıtım farklı işlemlerdir. Logo URL'lerinin payload'da bulunması görsel kullanım yetkisi değildir.
