# Current checkpoint — 2026-10-16

Delivery update: browser commits 453240f (dispatcher) and d3e45a8 (nine tests)
verified by git fetch and zero diff for those files. Terminal push remains
unconfigured; authenticated browser is approved. Next increment adds bounded,
immutable task input storage; 11 dispatcher tests pass. Full regression:
232 run, 225 passed, 7 skipped. No hosted migration or pilot activation.

Final tests: 230 run, 223 passed, 7 skipped. Code commit fb8d494.
Push blocked by absent HTTPS Git credentials (could not read Username).
Do not claim remote delivery. A Git bundle preserves changes.

Read MASTER_PROGRESS.md first. New files: experts/dispatcher.py and
tests_experts/test_dispatcher.py. Runtime queue reused; no existing migration
changed. Actual DataValidator callable bound; other handlers remain unbound.
Next command: `python -m scripts.ci_python`. Then implement immutable input
storage and source-job linkage. Do not call this a live end-to-end worker.
Git remote tree at 5b54b79 matched local tracked tree; histories safely merged.

# Uzman geliştirme devam kaydı — 15 Ekim 2026

Aktif dal: `feature/expert-engines`; taban: `31b30d5105abb1368839014c9a15b211fd7ce1f5`.
Ana dal değiştirilmedi. Önceki push başarısızlığında yerel dosyalar kayboldu; experts/ bu oturumda yeniden kuruldu ve yeniden test edildi. Önceki yerel commit kimliklerini aramayın.

Tamamlanan somut iş: `experts/contracts.py`, `research.py`, `football.py`, `review.py`, `portfolio.py`, `workflow.py`, `walkforward.py`, `benchmark.py`; `tests_experts/`; mevcut CI Python keşfine yeni testlerin eklenmesi. 14 rol için durumlar EXPERT_PROGRESS.md içinde. Bütün canlı işlevler tamamlanmış değildir.

Son doğrulama: 221 Python testi (214 başarılı, 7 kontrollü skip), PGlite 123 başarılı. Yerel native PostgreSQL kurulamadı; PR #1 GitHub Actions koşusu `38804459813` PostgreSQL 17 servis konteynerinde native bağımsız oturum/eşzamanlılık adımı dahil başarıyla tamamlandı. Hosted yalnız read-only ACL/RLS katalog kontrolü; JWT kabulü açık. Migration 001–005 aynen korundu; Supabase'e yazma yapılmadı.

Sıradaki somut işler:

1. PR #1 açıktır: `feature/expert-engines` → `main`. İncelemeden sonra birleştirme kararı ver; ana dal bu teslim sırasında değiştirilmedi.
2. GitHub Actions koşusu `38804459813` başarıyla geçti. Sonraki kod değişikliklerinde aynı native ve PGlite kapısını tekrar çalıştır.
3. Sadece mevcut test projesinde, güvenli secret deposuyla gerçek kullanıcı JWT/Auth/RLS kabulünü tamamla. Test kullanıcısı/yetki/migration gerekiyorsa önce somut değişikliği hazırla ve izin al. Mevcut projeyi boşmuş gibi cloudcheck.runner ile migration'dan başlatma.
4. Kaynak izinlerini güncel birincil kaynaklarla araştır. Gerçek kadro, dış tahmin ve oran adapterleri yok; koşulları doğrulanmadan ekleme. Sonuçları kaynak registry'de PARTIAL/BLOCKED tut.
5. Mevcut Runtime lease/retry kuyruğuna gerçek uzman dispatcher bağla; yeni yerel review audit'ini hosted rol sınırlarıyla birleştir. Queue görevlerini işlenmeden done yapma.
6. Ayrı çok sezonlu doğrulama, kalibrasyon dönüşümü, belirsizlik modeli, zamansal bootstrap, Red Team/özellik ablation ekle. Tek sezon ensemble iyileşmesini genelleme.
7. Sanal kupon yürütücüsünü kapalı tut. Araştırma ve tarihsel deneylerde cüzdan harcama; gerçek zamanlı kararlarla tarihsel replay'i karıştırma.

Yeniden başlatma:

```bash
git switch feature/expert-engines
python -m pip install -r requirements-cloud.txt
python -m scripts.ci_python
python -m experts.benchmark --out reports/experts/benchmark.json
```

Teslim yedeğindeki `expert-changes.bundle`, main üzerine bu dalın commitlerini içerir. Kaynak ZIP `.git`, bağımlılık/cache, bağlantı bilgisi veya büyük arşivlerin ikinci kopyasını içermez; mevcut depo arşiv parçaları değiştirilmedi.

---

# Aşama 0.1 devam kaydı — 15 Ekim 2026 (tarihsel)

## GitHub geliştirme deposu geçişi tamamlandı

Commit `82b4deb` ile Python, SQL, test, belge, sözleşme ve GitHub Actions dosyaları gerçek klasörlerinde bulunur. Yerel 198 izlenen dosyanın tamamı GitHub blob SHA değerleriyle eşleşti; eksik dosya yoktur. Kaynak arşivi ve geri yükleme dosyaları ayrıca korunur. Büyük uluslararası tarihsel dataset/tahmin dosyaları Git geçmişinde çoğaltılmadı.

GitHub Actions koşusu `38750591704` başarıyla geçti: 159 Python testi çalıştı (152 geçti, 7 kontrollü atlandı), native PostgreSQL bağımsız oturum ve eşzamanlılık kontrolleri geçti, PGlite 123 kontrol geçti. Private-repo engeli kaldırıldı. Gizli bilgi taramasında bulgu yoktur. Bu geçişte hosted Supabase migration'ı uygulanmadı ve pilot başlatılmadı.

Sıradaki gerçek kabul kapısı, ayrı test kullanıcısıyla hosted Supabase JWT/Auth/RLS sınamasıdır. Bunun için yalnız güvenli secret deposundaki değerler kullanılmalı; anahtarlar rapora veya kaynak koda yazılmamalıdır.

## GitHub kaynak ağacı geçişi

Kaynak arşivi SHA-256 ile doğrulandı ve güvenli yollarla çıkarıldı. Python, SQL, test, belge ve iş akışı dosyaları GitHub'daki gerçek klasörlerine taşınmak üzere hazırlandı. Büyük uluslararası tahmin matrisleri ve dataset Git ağacında çoğaltılmayacak; doğrulanmış arşiv parçalarında korunur. `github.event.repository.private == false` koşulu kaldırıldı. Gerçek Supabase projesine yeni migration uygulanmadı; pilot kapalıdır.

GitHub Actions'ın genişletilmiş kaynak ağacındaki son koşu bağlantısı ve sonuçları TEST_REPORT.md'nin en üst bölümüne yazılmalıdır. Gerçek kullanıcı JWT kabul kapısı hâlâ açıktır.

## Son güncelleme — gerçek bulut bağlantısı sonrası

001–005 Supabase Free test projesine uygulandı. Proje başlangıçta boştu; şimdi yalnız lab şeması ve açıkça sentetik doğrulama kayıtları bulunur. Pilot kapalı, cüzdan 1000 TL. Hosted güvenlik SQL'i ve anonim API sınırı geçti. Ayrıntılar TEST_REPORT.md'nin ilk bölümü ile reports/phase01/hosted-connected.json içinde. 005, yönetilen postgres hesabına worker SET ROLE üyeliğini tamamlar; eski migration'lar aynıdır.

157 Python testi geçti, 2 native test atlandı. PGlite 123 kontrol geçti. Farklı backend oturumları denendi fakat bağlayıcı sıraladığı için gerçek eşzamanlılık kanıtlanamadı. Sıralı günlük bütçe tetikleyicisi 10 kabul/2 ret verdi. Gerçek kullanıcı JWT testi yapılmadı; Auth settings 200 olması kullanıcı oturumu testi sayılmadı.

GitHub uygulaması AI Betting Lab reposunu göstermiyor. Sıradaki somut iş: doğru repo linkini almak ve GitHub uygulamasının erişimine eklemek; sonra kodu doğru repoya yükleyip mevcut CI workflow'unu çalıştırmak. Diğer beş repo bu projeyle ilgisiz olduğundan değiştirilmedi. Araçlar yeni repo oluşturma veya secrets yazma yeteneği sunmadı. Repo olmadan başka projeyi hedef seçmeyin.

Bulut artık boş olmadığından cloudcheck.runner'ın migration başlangıç adımı aynı projede tekrar çalışmaz. Aynı şema üzerinde güvenlik kontrolü için hosted-security.sql tekrar kullanılabilir; hosted-budget-seed.sql tekrar ekleme yapmaz, mevcut test betleri varsa durur. Şema/veri silmeyin. Eşzamanlılık ve gerçek JWT için PHASE01.md'deki güvenli test bağlantısı akışı kullanılmalı; secret değerlerini rapora/sohbete koymayın.

Canlı kapasite ölçümü ve Free plan doğrulandı; organizasyon egress bilinmediği için otonom çalışma kapalı kalır. Security advisor'ın 63 INFO bildirimi private-schema default-deny tasarımıyla ilgilidir. Bütün Auth/CI/concurrency kabul kapıları kapanmadan üretim/pilot başlatmayın.

---

## Bağlantı öncesi çalışma kaydı

Güncel durum: Aşama 0 kodu korunarak cloudcheck/ bağlantı/SQL/Auth test runner'ı, 004_cloud_security.sql, tests_cloud/, validate-cloud.mjs, cloud-validation.yml ve PHASE01.md eklendi. Yerel 157 Python testi ve 122 PGlite kontrolü geçti. Native/hosted raporları blocked; hiçbir bulut testinin geçtiği iddia edilmiyor. Sanal pilot kapalı.

Sonraki somut adım: PHASE01.md'deki secrets isimleriyle ayrı boş Supabase test projesini ve GitHub supabase-test environment'ını hazırlamak. Önce workflow hosted=false ile native konteyner testlerini, sonra hosted=true ile gerçek proje testlerini çalıştırmak. Gerçek değerleri sohbete veya repoya koymayın.

Runner komutları: `python -m cloudcheck.runner --mode native --out reports/phase01/native.json`, `python -m cloudcheck.runner --mode hosted --out reports/phase01/hosted.json`. Her biri açık disposable onayı ve hedef bağlama ayarları ister. Bağlantı olmadan çıkış 2/blocked. Var olan lab şemasına migration uygulamaz; proje temizleme/silme yapmaz. Yarıda kalan uygulamanın raporu son başarılı migration'ı gösterir.

Kapasite: `python -m cloudcheck.monitor --out reports/phase01/capacity.json`. Canlı SQL ölçümü hazır; organizasyon planı/egress API adaptörü henüz yok ve guard bu yüzden defer kalır. Worker bağlantısı tamamlanmadan otonom toplama açılmamalı. Ayrı LOGIN worker bağlantıları ve hosted JWT testleri de bekliyor.

Paketleme: `python -m scripts.package_cloud --baseline /guvenli/yol/asama-0.zip --out /cikti/asama-0.1.zip`. Eski kaynak/migration dosyalarının değişmediğini denetler; yalnız TEST_REPORT.md ve CONTINUE.md güncellenmiştir. Diğer eklemeler yeni dosyalardır. Paket bağlantı bilgileri, CA/anahtar dosyaları, node_modules ve geçici DB içermez.

---

## Önceki Aşama 0 çalışma kaydı

Temel: kullanıcı tarafından gönderilen ai-betting-lab-asama-2(1).zip. Eski dosyalar ve 001/002 migration değiştirilmez. Yeni kod foundation/ altında, yeni migration 003_multi_agent_foundation.sql olacaktır.

Tamamlanan: 123 eski dosya bayt düzeyinde korunmuştur. foundation/ sözleşmeleri, 14 rol kaydı, kalıcı görev/lease/retry, kanıt doğrulama, iki turlu inceleme, tahmin revizyonları ve hash zinciri uygulanmıştır. 003 migration ilişkiler, RLS/worker yetkileri ve ortak sanal harcama sınırı ekler. Gerçek bahis yoktur; pilot kapalıdır.

Sıradaki somut işler: ayrı boş native PostgreSQL test veritabanında eşzamanlılık testleri; ardından ayrı Supabase test projesinde Auth/RLS ve worker kimliklerinin doğrulanması. Bulut kota telemetrisi, otomatik arşivleme ve diğer eksikler NEXT_PHASE.md içinde. 14 uzmanın bütün araştırma işlevleri tamamlanmış değildir.

Son doğrulama: 133 Python testi geçti, native PostgreSQL gerektiren 2 test atlandı. PGlite üzerinde 107 ayrı SQL kontrolü geçti; eski 51 kontrol ayrıca 003 sonrasında tekrar geçti. Ham çıktılar reports/phase0/ altında. Gerçek Supabase bağlantısı yoktur. PostgreSQL kurulumu işletim sistemi izin engeline takıldı; native DSN sağlanmadı.

Kurulum ve tüm komutlar RUN_PHASE0.md içinde. Hızlı başlangıç: `python -m pip install -r requirements-foundation.txt`, `python -m unittest discover -s tests_foundation -v`, `python -m foundation.demo`. Demo sentetik ve çevrimdışıdır; iki çözülmemiş itiraz sonunda skip üretir. Yerel demo DB'leri ZIP'e dahil edilmez. 001/002 değişmedi; yeni şema 003_multi_agent_foundation.sql içindedir.
