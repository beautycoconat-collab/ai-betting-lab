# Aşama 0.1 — bulut doğrulama hazırlığı

**Bağlantı sonrası güncelleme:** 001–005 gerçek Supabase Free test projesinde uygulandı; hosted SQL güvenliği ve anonim API sınırı geçti. 005 yönetilen postgres rolünün worker üyeliğini tamamlar. Gerçek JWT oturumu, çakışan native bağlantılar ve GitHub Actions henüz doğrulanmadı. Güncel kanıt TEST_REPORT.md'nin ilk bölümünde; aşağıdaki metin ilk hazırlık sürümünün kurulum rehberidir.

Bu sürüm yerel olarak test edilmiş bulut doğrulama altyapısıdır. Gerçek Supabase/native PostgreSQL testleri **henüz çalıştırılmadı**. Bir Supabase projesi oluşturulmadı, ücretli hizmet etkinleştirilmedi, sanal pilot açılmadı. GitHub Actions dosyası hazırlandı; uzak repoya gönderilmedi veya çalıştırılmadı.

## Değişiklikler

001/002/003 değişmedi. Ek 004 migration, SECURITY DEFINER fonksiyonlarında pg_temp arama konumunu sona sabitler; anon/authenticated/service_role için lab şemasının doğrudan erişimini ve varsayılan ayrıcalıkları kapatır. Service role yerine dar kapsamlı SQL worker üyelikleri kullanılmalıdır. Yönetici ve rol sahiplerinin ayrıcalıkları bu korumayı teknik olarak değiştirebilir.

cloudcheck/ ortam değişkenlerinden bağlantı alır, hedef host/proje bağını kontrol eder, hosted bağlantıda sertifika ve hostname doğrulamasını zorunlu kılar. Transaction pooler kabul edilmez: doğrudan veya port 5432 session pooler gerekir. Migration öncesi lab şeması ve public uygulama tabloları bulunursa durur. Hiçbir veritabanını veya şemayı DROP etmez. Kısmi uygulama sonrası otomatik reset/retry yoktur; raporda son başarılı migration bulunur.

SECURITY DEFINER izinleri, rol nitelikleri, doğrudan kritik yazma izinleri, RLS ve sahte rol kullanımı test edilir. RLS testi ACL'den ayrı yapılır: transaction içinde geçici SELECT/UPDATE verilir, satır görünürlüğü ve yazma sınanır, bütün geçici izinler rollback edilir. SET ROLE testleri ayrı worker LOGIN kimliğiyle bağlantının yerine sayılmaz.

Hosted Auth testi önceden oluşturulmuş sıradan bir test kullanıcısının geçerli JWT'siyle /auth/v1/user çağrısını doğrular. Sonra anon ve authenticated kimliklerinin kritik REST PATCH denemelerini sınar. lab şeması Data API'de açık olmamalıdır; PGRST106 reddi API şema sınırını kanıtlar, tek başına RLS kanıtı değildir. SQL RLS testi ayrı raporlanır. Geçersiz JWT/API anahtarı başarılı güvenlik testi sayılmaz.

İki ayrı bağlantıyla job claim, 12 ayrı bağlantıyla günlük bütçe tetikleyicisi testi hazırlanmıştır. Bütçe testi yalnız izole test projesinde yönetici üzerinden sentetik satırlar ekler; place_paper_bet çağırmaz, pilot açmaz, sanal cüzdan bakiyesini değiştirmez. Bu test tam kupon finansal sonuçlandırma testi değildir. Eski 2 native test dosyası korunmuştur; pilot açmama şartı nedeniyle yeni CI bunların yerine yeni runner'ı kullanır.

## Yerel komutlar

```bash
python -m pip install -r requirements-cloud.txt
python -m unittest discover -s tests -v
python -m unittest discover -s tests_phase2 -v
python -m unittest discover -s tests_foundation -v
python -m unittest discover -s tests_cloud -v
npm ci --prefix supabase/tests --ignore-scripts --no-audit --no-fund
node supabase/tests/validate.mjs
node supabase/tests/validate-phase2.mjs
node supabase/tests/validate-foundation.mjs
node supabase/tests/validate-cloud.mjs
```

## GitHub Actions ve güvenli bağlantı

1. Kodu kendi özel GitHub reponuza aktarın. `.github/workflows/cloud-validation.yml` yalnız workflow_dispatch ile çalışır; PR veya cron üzerinden sır kullanmaz.
2. Ücretsiz Actions bütçesini hesabınızdan kontrol edip repository variable FREE_BUDGET_CONFIRMED=true ayarlayın. Bu bir kullanıcı kontrolüdür; otomatik fatura ölçümü değildir. GitHub hesabında ücretli aşımı kapatın. İşler süre ve eşzamanlılık sınırı taşır, fakat bunlar hesabın ücretsiz dakikalarını kendiliğinden doğrulamaz.
3. Önce hosted=false ile native işi çalıştırın. GitHub geçici runner üzerinde localhost'a bağlanan PostgreSQL 17 servis konteyneri kullanılır. Trust authentication yalnız bu geçici loopback test servisine aittir; buluta uygulanmaz.
4. Mevcut ücretsiz hakkınız içinde ayrı, boş Supabase test projesi hazırlayın. Ücretsiz yer yoksa ücretli proje açmayın. Kişisel/üretim verisi kullanmayın. Bu paket otomatik proje yaratmaz.
5. GitHub Environment adını supabase-test koyun; mümkün olan dal/kullanıcı kısıtlarını ayarlayın. Ortam secrets değerlerini aşağıdaki isimlerle güvenli ayarlar ekranından ekleyin. Sohbete, ZIP'e, kaynak koduna veya issue'ya yapıştırmayın.

| Secret | Değerin anlamı |
|---|---|
| LAB_TEST_DSN | Yalnız boş test projesinin admin PostgreSQL bağlantısı |
| LAB_EXPECTED_DB_HOST | Aynı bağlantının tam sunucu adı |
| LAB_TEST_PROJECT_REF | Yalnız test projesi ref değeri |
| LAB_SUPABASE_ANON_KEY | Test projesinin anon/publishable anahtarı |
| LAB_AUTH_JWT | Sıradan test kullanıcısının henüz süresi dolmamış access token'ı |
| LAB_CA_PEM | Supabase Connect ekranından alınan uygun kök CA sertifikası |

6. hosted=true ile çalıştırın. Önce native işin geçmesi gerekir. CA geçici dosyaya yazılır ve işlem çıkışında silinir. Raw DB/Auth hata mesajları rapora yazılmaz. Artifact yalnız filtrelenmiş JSON raporudur, saklama 3 gündür.
7. Hosted iş ilk migration uygulamasından sonra mevcut lab şemasını tekrar bulursa durur. Bu bir üretim migration aracı değildir. Tekrar deneme için test projesini bilinçli olarak hazırlayın; otomatik temizleme yoktur. Test satırları sentetiktir ve test projesinde kalır.

Yerel hosted çalıştırma için aynı değişkenleri güvenli ortamdan sağlayın; LAB_CA_PEM yerine LAB_SSLROOTCERT dosya yolu kullanın. LAB_DISPOSABLE_TEST_PROJECT=1 zorunludur:

```bash
python -m cloudcheck.runner --mode hosted --out reports/phase01/hosted.json
```

Bağlantı yoksa rapor blocked, çıkış kodu 2 olur. Gerçek test hatasında failed/1; bütün hazırlanmış probe'lar geçerse passed/0. Passed yalnız runner kapsamını ifade eder, bütün üretim kabulünü değil.

## Gerçek kullanım ve kapasite koruması

```bash
python -m cloudcheck.monitor --out reports/phase01/capacity.json
```

Bu komut read-only transaction içinde pg_database_size, bağlantı sayısı ve varsa storage.objects boyut metadatasını okur. Yerel ZIP boyutunu bulut kullanımı saymaz. Eksik/bozuk storage metadata unknown kalır. Proje SQL'i organizasyonun planını ve toplam egress kullanımını kanıtlamaz: bu alanlar null bırakılır. Organizasyon bazında gerçek fatura/kota API adaptörü henüz yoktur. Bu nedenle otomatik veri toplama kapısı varsayılan **defer** kalır; ölçüm eksikliği sıfır kullanım sayılmaz.

capacity.guarded_call taze/tam ölçüm olmadığında işlemi çağırmaz. Varsayılan operasyonel eşikler DB 400 MB, storage 800 MB, egress 4 GB, bağlantı oranı %75; bunlar resmi kota veya bütçe garantisi değil, muhafazakâr uygulama ayarlarıdır. Ölçüm 15 dakikadan eskiyse veya gelecekteyse reddedilir. Hiçbir ücretli plan değişikliği API'si kullanılmaz.

Önemli sınır: guard mevcut legacy collector'ları global olarak ele geçirmez; gelecek otonom worker giriş noktası bu guard üzerinden bağlanmalıdır. Organizasyon planı/egress ölçümü ve worker entegrasyonu tamamlanmadan otonom toplama etkinleştirilmemelidir. Bu sürüm gerçek hesabın maliyetini ölçtüğünü iddia etmez.

## Resmî teknik kaynaklar — 15 Ekim 2026 kontrolü

- https://supabase.com/docs/guides/database/connecting-to-postgres — bağlantı türleri ve session pooler.
- https://supabase.com/docs/guides/platform/ssl-enforcement — verify-full ve CA.
- https://supabase.com/docs/guides/database/functions — SECURITY DEFINER çağrı yetkileri.
- https://www.postgresql.org/docs/current/sql-createfunction.html — güvenilir search_path ve pg_temp.
- https://supabase.com/docs/guides/platform/billing-on-supabase — organizasyon bazlı faturalama.
- https://supabase.com/docs/guides/observability/metrics — performans metriği ile fatura kullanımının farklı kapsamı.

## Açık kabul kapıları

Native runner'ın gerçek sunucuda tamamlanması; hosted 001–004 sıralı uygulama; gerçek Auth JWT ile API probe'ları; ayrı LOGIN worker üyelikleri; organizasyon bazlı plan/egress ölçümü; CI'nin gerçek GitHub çalıştırma kaydı. Bunlar tamamlanmadan Aşama 0.1 bulut doğrulaması bitmiş değildir.
