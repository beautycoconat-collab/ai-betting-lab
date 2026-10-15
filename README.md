# AI Betting Lab

Denetlenebilir, çok kaynaklı futbol skor tahmini ve yalnızca sanal para araştırma altyapısıdır. Başlangıç sanal bakiyesi 1.000 TL, günlük sanal harcama üst sınırı 100 TL ve strateji `Balanced` olarak sabittir. Gerçek bahis hesabı veya gerçek para işlemi yoktur; pilot kapalıdır.

## Depo yapısı

- `betting_lab/`: veri toplama, kaynak adapterleri, kimlik eşleştirme ve SQLite saklama
- `engine/`: Elo, Poisson, Dixon-Coles, zaman sıralı dataset ve değerlendirme
- `foundation/`: 14 rol için sözleşmeler, görevler, kanıt ve inceleme akışı
- `cloudcheck/`: native PostgreSQL ve hosted Supabase güvenlik doğrulayıcıları
- `supabase/migrations/`: sıralı `001`–`005` migration dosyaları
- `supabase/tests/`: PGlite ve güvenlik senaryoları
- `tests*`: Python regresyon, sözleşme, model ve eşzamanlılık testleri
- `docs/`, `ARCHITECTURE.md`, `DATABASE_SCHEMA.md`, `MESSAGE_PROTOCOL.md`: mimari belgeleri

## Kurulum ve test

Python 3.12 ve Node.js 22 önerilir.

```bash
python -m pip install -r requirements-cloud.txt
python -m scripts.ci_python
npm ci --prefix supabase/tests --ignore-scripts --no-audit --no-fund
node supabase/tests/validate.mjs
node supabase/tests/validate-phase2.mjs
node supabase/tests/validate-foundation.mjs
node supabase/tests/validate-cloud.mjs
```

Native PostgreSQL doğrulaması disposable bir PostgreSQL 17 veritabanı ister:

```bash
LAB_TEST_DSN='host=127.0.0.1 dbname=ai_betting_lab_test_ci user=postgres' \
LAB_EXPECTED_DB_HOST=127.0.0.1 \
LAB_DISPOSABLE_TEST_PROJECT=1 \
python -m cloudcheck.runner --mode native --out reports/ci/native.json
```

GitHub Actions aynı kontrolleri PostgreSQL 17 servis konteyneriyle çalıştırır. İş akışları yalnız `contents: read` yetkisine sahiptir ve Private depoda da çalışabilir.

## Tarihsel veriler

Büyük, yeniden üretilebilir tarihsel tahmin matrisleri Git ağacında ikinci kez tutulmaz. Orijinal 203 dosyalık teslim `project-source.zip.part-00`, `project-source.zip.part-01` ve `source-package.json` ile kayıpsız korunur. Tam tarihsel kanıt testleri için:

```bash
python restore_project.py
```

Betik her parçanın ve birleşik arşivin SHA-256 değerini doğrular, yol geçişlerini reddeder ve sonra dosyaları çıkarır. Yerel değişiklik bulunan bir çalışma ağacında çalıştırmadan önce temiz bir klon kullanın.

## Güvenlik

Bağlantı dizeleri ve anahtarlar yalnız ortam değişkenlerinden okunur. `service_role`, veritabanı parolası veya kullanıcı JWT’si Git’e eklenmez. Hosted Supabase doğrulaması ayrı, boş bir test projesi için manuel iş akışıdır; bu depoyu kullanmak gerçek Supabase projesine migration uygulamaz.

Güncel doğrulama kapsamı ve açık kapılar için `TEST_REPORT.md` ve `CONTINUE.md` dosyalarını okuyun.
