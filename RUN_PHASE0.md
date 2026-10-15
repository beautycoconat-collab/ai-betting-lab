# Aşama 0 çalıştırma

Python 3.12 ve Node.js 22 veya 24 ile proje kökünde:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-foundation.txt
python -m unittest discover -s tests -v
python -m unittest discover -s tests_phase2 -v
python -m unittest discover -s tests_foundation -v
npm ci --prefix supabase/tests --ignore-scripts --no-audit --no-fund
node supabase/tests/validate.mjs
node supabase/tests/validate-phase2.mjs
node supabase/tests/validate-foundation.mjs
node supabase/tests/validate-legacy-after-foundation.mjs
```

Windows PowerShell aktivasyonu: `.venv\Scripts\Activate.ps1`. Diğer komutlar aynı proje kökünden çalışır. Kaynak kodundan çalıştırıldığı için `pip install .` gerekmez. İnternet yalnız eksik ücretsiz bağımlılıkları indirmek içindir; testler futbol sitelerine çağrı yapmaz.

## Çalışan Red Team/Hakem örneği

```bash
python -m foundation.demo --db data/foundation-demo.sqlite --out reports/phase0/demo.json
python -m foundation.export --audit-db data/foundation-demo.sqlite --audit-out reports/phase0/audit-export.json
```

Bu ayrı veritabanı açıkça **sentetik protokol demosudur**. Sahte oyuncu/sakatlık veya oran gerçek veri diye sunulmaz. İki çözülmemiş inceleme sonunda `abstain/skip` beklenir. Olasılık değiştirilmez ve sanal cüzdandan harcama yapılmaz. Aynı demo yeniden çalıştırıldığında yeni fixture/run kimlikleri oluşturur; eski kayıtları silmez.

Gerçek geçmiş verilerle modellerin çalıştırılması Aşama 2'deki `PHASE2.md` komutlarıyla devam eder. Bu aşama yeni model performansı üretmez; önceden paketlenen gerçek veri kanıtı ve modeller korunur.

## Native PostgreSQL eşzamanlılık testi — isteğe bağlı, burada çalıştırılamadı

Yeni ve boş, adı `ai_betting_lab_test` ile başlayan disposable bir PostgreSQL veritabanı oluşturun. Mevcut Supabase/prod veritabanını kullanmayın. Test var olan lab şeması bulursa durur; hiçbir şema veya veritabanı silmez.

```bash
python -m pip install 'psycopg[binary]>=3.2,<4'
```

`LAB_TEST_POSTGRES_DSN` ortam değişkenini yalnız bu disposable DB'nin bağlantısına ve `LAB_TEST_POSTGRES_DISPOSABLE=1` değerini ayarlayın. Bağlantı bilgisini GitHub koduna, istemciye veya rapora yazmayın. Sonra:

```bash
python -m unittest discover -s tests_foundation -p test_postgres_concurrency.py -v
```

Bu iki test farklı PostgreSQL bağlantılarıyla aynı job claim'ini ve 12 paralel legacy sanal harcamada 100 TL sınırını sınar. Bu ortamda DSN bulunmadı, PostgreSQL kurulumu işletim sistemi izin engeline takıldı. Dolayısıyla teslimat raporunda bu testler **skipped**, passed değildir. PGlite, hosted Supabase veya bağımsız PostgreSQL oturumlarının yerine sayılmaz.

## Migration uygulama

Boş bir yerel/PostgreSQL test veritabanında 001, 002, 003 sırasıyla uygulanır. Aşama 2 şeması zaten varsa yalnız 003 gerekir. Önce yedek/dry-run ve rol oluşturma yetkisi kontrol edilmelidir. Hosted Supabase URL/anahtarı bu projeye eklenmedi. `001/002` dosyalarının SHA-256 koruma raporu `reports/phase0/baseline-integrity.json` içindedir.

## Dosyalar

`ARCHITECTURE.md`: güncel mimari. `AGENT_ROLES.md`: 14 rol. `DATABASE_SCHEMA.md`: tablolar/ER/yetkiler. `MESSAGE_PROTOCOL.md`: mesaj sözleşmeleri. `TEST_REPORT.md`: gerçek test sonuçları ve açık kapılar. `DEPLOYMENT.md`: ücretsiz dağıtım/saklama. `NEXT_PHASE.md`: sonraki işler. `CONTINUE.md`: devam kaydı.
