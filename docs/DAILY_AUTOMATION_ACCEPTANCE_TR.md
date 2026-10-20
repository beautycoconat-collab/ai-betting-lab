# Günlük araştırma — güvenli devreye alma kontrolü

Bu paket gerçek bir **yerel günlük çalıştırma koordinatörü** ekler. `dashboard.automation_cli`, mevcut `dashboard.daily.run` tahmin zincirini ve `experts.result_scheduler.ResultScheduler` sonuç doğrulamasını kullanır. `dashboard.daily` halen yalnızca **Bundesliga (bl1)** için doğrulanmış tahmin üretir; diğer ligleri kapsıyor gibi gösterilmez. Kendi başına yeni maç tahmini algoritması icat etmez.

## Çalıştırma

Mevcut GitHub `feature/expert-engines` deposunun kökünde, paket dosyalarını **yol yapısını koruyarak** birleştirin. `dashboard/daily.py` için yalnızca `python scripts/apply_daily_health_patch.py` entegrasyonunu uygulayın. Ardından:

```sh
python -m unittest discover -s tests_dashboard -v
python -m dashboard.automation_cli --database data/dashboard-live.sqlite --out public/data/dashboard.json
# Onaylı kaynak ve kalıcı kota DB hazırsa manuel olarak:
python -m dashboard.automation_cli --database data/dashboard-live.sqlite --collect
```

İlk çalıştırma `partial` dönebilir; kaynak erişimi, fixture veya geçmiş veri eksikliği `done` sayılmaz. Çıktı `forward_performance` alanında sadece kilitli, doğrulanmış maç öncesi tahminlerin 7/30/90/180 günlük Brier/Log Loss/kalibrasyon/kapsama ölçümlerini gösterir. Gerçek oranlar yoksa ROI ve CLV `null` kalır.

## Üretim zamanlayıcısı **kapalı**

`.github/workflows/daily-research-preview.yml` **yalnızca manuel** çalışır ve hem `LAB_RESEARCH_ACCEPTED` hem `LAB_DURABLE_QUOTA_VERIFIED` değişkenlerini gerektirir. Actions runner'da SQLite dosyası yoksa başarısız olur. GitHub Actions cache kalıcı kota kayıtları için güvenilir bir veri tabanı değildir. Hosted JWT/RLS/worker izinleri gerçek Supabase üzerinde doğrulanmadan, dayanıklı veri deposu ve kullanıcı onayı olmadan cron açılmamalıdır.

## Bilinen eksikler / kabul testleri

- Güncel repo sürümüyle tüm entegrasyon testleri ve gerçek sağlayıcı erişimi bu ortamda doğrulanmadı.
- `daily.run` halen `bl1` ile sınırlıdır. Daha geniş lig desteği için ayrı model/lig veri kabulü gerekir.
- `ResultScheduler` yalnızca **önceden kilitlenmiş** ve hakem kanıtlı tahminleri sonuçlandırır; dashboard'un koşullu tahminleri kendiliğinden kilitli sayılmaz.
- Hosted JWT/RLS, en az yetkili worker, kalıcı kota defteri, dağıtık kilit, otomatik Vercel yayını doğrulanmadı. Üretim cron kapalı.
- Tek günlük run ledger eşzamanlı ve başarılı tekrar çalıştırmayı engeller; `partial` kayıtlar en erken 30 dakika sonra en çok 3 denemeye kadar yeniden denenebilir. Bu yerel yeniden deneme kuralı dağıtık hosted lease recovery yerine geçmez.
- `scripts/apply_daily_health_patch.py` mevcut dosyanın belirli sabit işaretlerini bekler; değişmişse güvenli şekilde durur.
- Migration 001–005 değiştirilmedi, yeni migration eklenmedi. Sanal ve gerçek bahis yürütmesi kapalı.

## 19 Ekim 2026 — gerçek Supabase okuma denetimi

Bağlı Supabase hesabında yalnızca bir proje görüldü: `oswpkwwbjwyktuqcakhr` (ACTIVE_HEALTHY). Bu projenin `public` şemasında tabloların RLS durumlarını sorgulayan **salt-okunur** SQL sorgusu **boş sonuç** verdi. Bu, AI Betting Lab tablolarının söz konusu projede kurulu olduğuna ilişkin kanıt bulunmadığı anlamına gelir. Projenin AI Betting Lab'e ait olduğu doğrulanmadan migration, JWT denemesi, yazma veya worker bağlantısı yapılmadı. `hosted_jwt_verified`, `hosted_rls_verified`, `worker_least_privilege_verified` kapıları **başarısız/bilinmiyor** kalır.

`python -m dashboard.hosted_readiness --manifest config/hosted-acceptance.json` yalnızca bağımsız denetim kanıtı dosyasının biçimini kontrol eder; başarılı biçim doğrulaması bile otomatik cron açmaz. Gerçek kabul için Supabase proje eşlemesi, hosted rol/JWT/RLS negatif ve pozitif testleri, kalıcı quota/lease, izinli veri kaynakları ve yayın kanıtları gerekir.

**Ek güvenlik düzeltmesi:** `dashboard.automation_cli` artık kısmi/başarısız günlük çalıştırmada eski dashboard JSON'unu değiştirmez. Bu, eksik günlük veri yüzünden son başarılı yayının bozulmasını önler.
