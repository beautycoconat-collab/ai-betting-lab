# Aşama 0.1 test raporu — 15 Ekim 2026

## GitHub geliştirme deposu doğrulaması — tamamlandı

Kaynak ağacı commit `82b4deb` üzerinde gerçek klasörlerine açıldı. Yerelde üretilen 198 izlenen dosyanın GitHub blob SHA değerleri birebir karşılaştırıldı: **198/198 eşleşti, eksik 0**. Beş ek dosya doğrulanmış kaynak arşivi ve geri yükleme altyapısıdır. Büyük uluslararası tarihsel çıktıların Git ağacında ikinci kopyası oluşturulmadı; iki arşiv parçasında korunur.

GitHub Actions koşusu [`38750591704`](https://github.com/beautycoconat-collab/ai-betting-lab/actions/runs/38750591704) başarıyla tamamlandı. Sonuçlar: **159 Python testi çalıştı; 152 geçti, 7 kontrollü atlandı**. Atlamaların 5'i yalnız tam tarihsel arşivde tutulan büyük kanıt dosyalarına, 2'si genel Python koşusuna DSN verilmemesine aittir. Ayrı native PostgreSQL 17 adımında bağımsız bağlantı, ACL/RLS/SECURITY DEFINER sınırları, tekil iş alma ve eşzamanlı günlük bütçe tetikleyicisi geçti. PGlite grupları **23 + 28 + 56 + 16 = 123** kontrolü geçti.

`github.event.repository.private == false` koşulu kaldırılmıştır; doğrulama public ve private depolarda çalışır. Son kaynak taramasında anahtar, parola, private-key başlığı veya gömülü bağlantı bilgisi bulunmadı. Bu işlem sırasında hosted Supabase'e migration uygulanmadı ve sanal pilot başlatılmadı. Gerçek kullanıcı JWT kabul testi hâlâ açık bir sınırdır.

## GitHub Actions doğrulaması — kaynak arşivi

GitHub Actions koşusu `38746160374`, commit `07f11b0` üzerinde başarıyla tamamlandı. Arşiv hash doğrulaması ve çıkarma, Python regresyonları, native PostgreSQL bağımsız oturum/güvenlik testleri ve PGlite migration kontrolleri geçti. İlk koşuda farklı platformdaki yaklaşık `1.29e-26` kayan nokta farkı, bit düzeyinde eşitlik isteyen testin taşınabilirlik hatasını ortaya çıkardı; tolerans `rtol=1e-15` olarak sınırlandırıldı ve ikinci koşu geçti.

Hosted Supabase üzerinde bu GitHub kaynak-ağacı geçişi sırasında yeni migration çalıştırılmadı ve gerçek kullanıcı JWT testi yapılmadı.

## Bağlantı sonrası güncelleme — 09:46 UTC / 12:46 İstanbul

Gerçek Supabase Free test projesinde **001, 002, 003, 004 ve ek 005** sırasıyla uygulandı. Başlangıçta public/lab uygulama tabloları, Auth kullanıcıları ve Storage dosyaları yoktu. Hosted PostgreSQL 17.11 üzerinde erişim güvenliği SQL senaryosu geçti: 14 rol, 67 RLS tablosu, anon/authenticated yazma retleri, service_role ACL sınırları, Red Team sayısal RPC ve rol taklidi retleri, append-only ledger. ACL'den ayrı RLS testi geçici izinlerle yapıldı ve izinler rollback edildi.

Gerçek bulut testi 003'te yerelde görünmeyen worker üyeliği eksiğini ortaya çıkardı. Supabase'in yönetilen postgres rolü yeni worker rollerine SET ROLE yapamıyordu. Eski migration değiştirilmeden **005_hosted_worker_membership.sql** eklendi; yalnız postgres migration sahibine 14 worker ve dashboard üyeliği verildi. Ardından hosted güvenlik senaryosu geçti. Anon/authenticated/service_role'a worker üyeliği verilmedi.

Gerçek API probe'u geçerli publishable/anon anahtarıyla Auth settings için 200, lab şemasındaki üç PATCH için 406/PGRST106 verdi. Bu, API şema sınırıdır; giriş yapmış gerçek kullanıcının JWT testi değildir. Anonymous sign-in kapalıydı; ayar değiştirilmedi, test hesabı yaratılmadı. Auth kullanıcı sayısı 0 kaldı.

Hosted bütçe tetikleyicisi sıralı 12 sentetik test eklemesinin 10'unu kabul etti, 2'sini daily_limit ile reddetti. Bu yönetici testidir; gerçek bahis veya pilot değildir. Cüzdan 100000 kuruş, betting_enabled=false, pilot_start=null ve ledger tek açılış satırı kaldı. Sentetik test kayıtları test projesinde tutuldu; muhasebe işlemi gibi yorumlanmamalıdır.

Farklı backend PID'leriyle iki worker denendi; tek iş bir kez alındı. Ancak bağlayıcı çağrıları sıraya koydu: kayıtlı zamanlar gerçek çakışmayı göstermedi. Bu nedenle **gerçek eşzamanlılık kanıtlanmadı**. Standalone native testler/CI hâlâ bekliyor; farklı PID olması tek başına concurrency kanıtı sayılmadı.

Canlı hesap ölçümü: Free plan doğrulandı; veritabanı 14.325.427 bayt, Storage 0 bayt, bağlantı sayısı 12/60. Bu tarihsel ölçümdür, güncel kota hakkı değildir. Organizasyon egress bilinmiyor; otonom guard defer kalır. Gerçek anahtar/DSN rapora veya ZIP'e konmadı.

Security advisor: ERROR/WARN yok; özel lab şemasında kasıtlı default-deny nedeniyle 63 INFO `rls_enabled_no_policy` bildirimi var. Bunları susturmak için geniş erişim politikası eklenmedi. Açıklama: https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy

Güncel yerel sonuç: **157 Python passed, 2 native skipped; 123 PGlite kontrolü passed** (yeni 005 kontrolü dahil). Ham gerçek bulut bulguları reports/phase01/hosted-connected.json, tekrar çalıştırılabilir SQL supabase/tests/hosted-security.sql ve hosted-budget-seed.sql içinde. Aşağıdaki eski blocked kayıtları bağlantı öncesi tarihsel sonuçlardır.

GitHub bağlantısında yalnız COD-Form-Backend, davetiyehemen, rain-seo-radar, rain-video-automation ve instagram-dm-automation görünüyordu. AI Betting Lab bulunmadığı için başka repoya kod yüklenmedi ve Actions çalıştırılmadı. Repo erişimi/linki, güvenli native DB bağlantısı ve gerçek test kullanıcısı JWT doğrulaması kalan kabul kapılarıdır. **Aşama 0.1 bütünüyle tamamlandı değildir.**

---

## Bağlantı öncesi sonuçlar — tarihsel kayıt

**Durum: yerel hazırlık doğrulandı; bulut kabulü BLOCKED.** Supabase bağlantısı, test projesi bilgileri ve native PostgreSQL sunucusu bu ortamda bulunmadı. GitHub Actions uzakta çalıştırılmadı. Sanal pilot başlatılmadı.

| Ortam | Bu sürümde gerçekten çalıştırılan | Sonuç |
|---|---|---|
| Yerel Python | Eski 33 + 66 + 34 ve yeni 24 | **157 geçti**; eski native sınıfın 2 testi skipped |
| PGlite | Eski 23 + 28 + 56 ve yeni 15 | **122 kontrol geçti** |
| Native PostgreSQL | cloudcheck.runner preflight | **blocked: missing_test_configuration**; DB'ye bağlanılmadı |
| Hosted Supabase | cloudcheck.runner preflight | **blocked: missing_test_configuration**; migration/Auth/RLS çalışmadı |
| Gerçek kapasite ölçümü | cloudcheck.monitor preflight | **blocked**; hesap kullanımı ölçülmedi, guard defer |
| GitHub Actions | YAML hazırlandı | Çalıştırılmadı |

Bu turdaki ham kayıtların tamamı **reports/phase01/** altında. native.json ve hosted.json boş migration listesiyle blocked gösterir; başarılı test gibi sayılmaz. Python 3.12, Pydantic 2.13.5, psycopg 3.3.6 ve PGlite 0.3.14 kullanıldı. Yeni 24 testin Auth çağrıları mock'tur; gerçek bulut kanıtı değildir.

Yeni PGlite kontrolleri dört migration'ın sıralı uygulanmasını, definer search_path düzenini, anon/authenticated/service_role erişim kısıtlarını, ACL'den ayrı RLS sınamasını ve cüzdan/pilotun değişmediğini doğruladı. Native çok oturumlu kilit davranışı veya gerçek Supabase Auth bunlardan çıkarılamaz.

Yeni runner 2 bağlantıyla claim ve 12 bağlantıyla bütçe tetikleyicisi deneyi içerir; **henüz yürütülmedi**. Test pilot açmadan yalnız sentetik test satırlarıyla çalışmak üzere yazıldı. Tam mali kupon işlem motorunu kanıtlamaz. Eski 001/002/003 ve çalışan Python modülleri değiştirilmedi; ek 004 ve cloudcheck modülleri oluşturuldu. Koruma raporu reports/phase01/baseline-integrity.json içindedir.

Eksik erişimler: yalnız boş test projesine ait DSN/host/ref, uygun CA, anon/publishable key, sıradan test kullanıcısı access token'ı, GitHub test environment ve native sunucu. Değerler rapora/ZIP'e yazılmamalıdır. İsimler ve kurulum PHASE01.md içinde.

Kapasite koruması canlı SQL ölçümü için hazırdır; organizasyon planı/egress adaptörü ve mevcut worker'lara global bağlantısı tamamlanmadı. Eksik ölçümde işlem başlatmama davranışı yerel testlerle doğrulandı. Üretime geçiş ve Aşama 0.1 tamamlandı iddiası için PHASE01.md içindeki açık kabul kapıları kapanmalıdır.

---

## Önceki Aşama 0 raporu — tarihsel kayıt

Python 3.12, Pydantic 2.13.5 ve paket kilidindeki PGlite kullanıldı. Hosted Supabase kullanılmadı.

| Grup | Sonuç | reports/phase0/ altındaki ham kayıt |
|---|---|---|
| Aşama 1 Python | 33 geçti | python-phase1.txt |
| Aşama 2 Python | 66 geçti | python-phase2.txt |
| Foundation Python | 34 geçti, 2 atlandı | python-foundation.txt |
| 001 SQL | 23 geçti | postgres-phase1.txt |
| 001 + 002 SQL | 28 geçti | postgres-phase2.txt |
| 001 + 002 + 003 SQL | 56 geçti | postgres-foundation.txt |
| Eski SQL kontrollerinin 003 sonrası tekrarı | 51 geçti | postgres-compatibility.txt |

Toplam **133 Python testi geçti; 2 test skipped**. SQL tarafında **107 ayrı kontrol** geçti; 51 eski kontrolün tekrarını yeni test olarak saymıyoruz. Eski 99 Python testi korunmuştur.

## Zorunlu senaryolar

| No | Senaryo | Doğrulanan kapsam |
|---|---|---|
| 1 | Geçerli mesaj | Python/SQL kabul |
| 2 | Eksik alan | Ret |
| 3 | Yanlış sürüm | Ret |
| 4 | Red Team sayısal müdahale | numeric_override ve rol yetkisi ret |
| 5 | Olmayan kanıt | İlişkisel doğrulama/FK ret |
| 6 | Aynı mesaj | Aynı içerik idempotent; farklı içerik ret |
| 7 | Eski tahmin UPDATE | Append-only tetikleyici ret |
| 8 | V1/V2 | Ayrı revizyonlar |
| 9 | Yetkisiz istemci | Yerel SQL rollerinde kritik yazma engelli; hosted Auth/RLS doğrulanmadı |
| 10 | İki worker | Ayrı SQLite bağlantılarıyla eşzamanlı claim geçti; native PostgreSQL atlandı |
| 11 | İki kez sonuçlandırma | İptal/iade idempotent; mükerrer kredi yok. Kazandı/kaybetti motoru sonraki aşama |
| 12 | Günlük 100 TL | SQL sıralı işlemlerde eski/yeni ortak bütçe ve iade sonrası sınır geçti; native eşzamanlı test atlandı |
| 13 | Kaynak kotası | Yerel kuyruk ve SQL rezervasyonu duruyor |
| 14 | Çelişkili veri | unknown/conflicting korunuyor |
| 15 | İki itiraz | İkinci tur abstain/skip; üçüncü tur engelli |
| 16 | Hedef ve zaman | Karışık hedef, gelecek veri, yanlış fixture/takım reddi |
| 17 | Eski testler | 99 Python ve 51 eski SQL kontrolü geçti |

## Kapsam ve sınırlar

Sözleşmeler, rol kaydı, görev bağımlılıkları/lease/retry, kanıt referansları, iki turlu deterministik hakem akışı, tahmin revizyonları, denetim zinciri ve ek şema çalıştırıldı. Elo/Poisson/Dixon-Coles yeniden yazılmadı. Bu aşama yeni tahmin başarısı veya kârlılık iddiası üretmez.

SQL testleri sentetik fixture/kanıt/odds kullanır. Bazı provenance testleri doğrulama dallarını sınamak için sentetik test satırında real etiketi kullanır; bunlar gerçek piyasa kanıtı değildir. demo.json açıkça sentetik ve çevrimdışıdır. Önceki gerçek tarihsel kanıt dosyaları korunmuştur.

Native PostgreSQL sunucusu/DSN yoktu; kurulum işletim sistemi izin engeline takıldı. test_postgres_concurrency.py içindeki iki test bu yüzden atlandı. PGlite, bağımsız PostgreSQL oturumlarındaki kilitleri veya gerçek Supabase Auth/RLS'yi kanıtlamaz. Eksik erişimler: disposable native PostgreSQL DSN, ayrı Supabase test projesi ve kontrollü worker kimlikleri. Ücretli API veya LLM anahtarı gerekmez.

14 rolün araştırma zekâsının tamamı, bulut kota telemetrisi, otomatik arşivleme, bütün kupon türlerinin hesap/sonuçlandırma motoru ve canlı pilot tamamlanmış değildir. Teslimat test edilmiş yerel temeldir; tüm üretim kabul kapılarının tamamlandığı anlamına gelmez. NEXT_PHASE.md somut devam işlerini içerir.

## Koruma ve tekrar üretim

scripts/phase0_report.py kullanıcı ZIP'indeki 123 dosyanın değişmediğini bayt karşılaştırmasıyla doğruladı. SHA-256 kayıtları baseline-integrity.json, import envanteri module-inventory.json içindedir. 001/002 korunmuş, 003 eklenmiştir. Çalıştırma komutları RUN_PHASE0.md içindedir.
