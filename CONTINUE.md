# 2026-10-16 — Manuel sonuç planlayıcısı ve 14. uzman pencereleri (YEREL, GITHUB'A GÖNDERİLMEDİ)

**Görev 4 PARTIAL, Görev 5 PARTIAL:** `experts/result_scheduler.py` ve `scripts/result_cycle.py` eklendi. Önceden maç başlamadan kilitlenmiş, model/hakem kanıtı olan bir tahmin için izinli kaynakta idempotent günlük veri toplama görevi oluşturur. Kaynak işi `kickoff+120min` öncesi çalışmaz; mevcut `engine.queue` kota ve lease güvenliği kullanılır. Ham snapshot doğrulaması `OutcomeJournal` tarafından yapılır; eski önbellek, yanlış yerel/sağlayıcı kimliği, belirsiz veya eksik final reddedilir. Yeni tarihli bir görevle tekrar kontrol mümkündür, skor/provenance düzeltmesi manuel incelemeye alınır; hiçbiri eski skoru değiştirmez.

**14. uzman yerel metrikler:** 7/30/90/180 günlük Brier/Log Loss, kilitli tahmin ve sonuçlandırılmış tahmin sayıları. Metrikler `eligible locked predictions` içindir, lig/bülten kapsama oranı değildir. Gerçek oran, CLV, ROI veya sanal defter hesaplanmadı.

**Yerel test kanıtları:** Yeni 14 test (12 scheduler + 2 CLI) başarılı. Uçtan uca seçilmiş kaynak/sonuç testleriyle 74/74, farklı tahmin/kalibrasyon testlerinde 121/121; foundation 34 başarılı, 2 kontrollü atlama. Test grupları aynı olmayan modülleri kapsar; tek komutla tüm testleri çalıştırma girişimi zaman aşımına uğradı. Native/hosted PostgreSQL/JWT/GitHub Actions bu teslimde kabul edilmiş sayılmaz.

**GÜVENLİK VE SINIRLAR:** Kaynak gerçek ağ erişimiyle denenmedi; testlerde sentetik HTTP kullanıldı. `scripts.result_cycle` yalnızca yerel SQLite için plan/reconcile/report komutlarıdır, ağ işlemi yapmaz. Gerçek otomatik günlük cron, hosted yetki, gerçek kaynak yayın zamanı, sonuç düzeltme politikası ve tüm kullanıcı arayüzü açık. Pilot, yayın ve gerçek bahis kapalı. 001–005 migration ve Supabase değişmedi. `main` değiştirilmedi. GitHub `feature/expert-engines` remote HEAD kontrol edildi: `dd8c67f`, yerel ZIP delta henüz PR #1'e yüklenmedi; önceki GitHub yazma HTTP 403 engeli devam ediyor.

**Sonraki aşama:** Denetimli günlük işçi işletimi için gerçek sağlayıcı sözleşme/yayın zamanı incelemesi; tarihsel skor düzeltme olaylarının `append-only` sürümlü karar politikası; RLS/JWT kabul kapısı; Supabase 006 taslağı yalnız onaydan sonra uygulama; dashboard. Work ZIP'ten devam ederken önce `docs/result_scheduler.md` dosyasını oku.

---
# 2026-10-16 — Forward verified outcomes and grade journal (local only)

- **Task 4 PARTIAL:** Added `experts/outcome_journal.py`, `tests_experts/test_outcome_journal.py`, `docs/forward_outcome_journal.md`. Forward lock requires actual pre-kickoff `Runtime.clock`, a prematch model output, matching model `versions` SHA, a persisted referee dependency with `approved` status, and the immutable fixture contract. Synthetic approved handlers in tests are NOT acceptance for a real approved forward model.
- Source evidence: only existing completed `v2_jobs` source snapshots, rehashed raw payload, re-normalized adapter result, exact native ID, team/competition/season/kickoff and explicit `regulation90` score. Post-match `observed_at` >= kickoff+90min is necessary but not provider publication verification. Conflicting or corrupt data fail closed. OpenFootball and OpenLiga synthetic source formats tested.
- SQLite-only append-only `lab_locked_predictions`, `lab_verified_results`, `lab_prediction_grades`. Brier and Log Loss plus pure-market `won/lost/push` verdict; no virtual ledger, CLV or ROI are claimed. No automated fetching or hosted worker.
- **Task 1, 2, 3, 5 remain PARTIAL; Task 6 NOT_STARTED.** Existing migrations 001–005, Supabase and `main` unchanged. No real bets/pilot.
- **Local tests:** 20 new suite passed; focused regression 52 passed. Earlier interim full experts 175 passed, but final full regression rerun timed out; no full suite/CI acceptance for current state. See docs/forward_outcome_journal.md.
- **Delivery:** local ZIP only. GitHub connector previously denied write HTTP 403; PR #1 not updated. Next: scheduled result collection from approved feeds, immutable source time attestation and provider corrections, actual forward-only journal records, full regression, hosted JWT/RLS gates, dashboard.

---

## 2026-10-16 — Local research worker chain (this delivery; GitHub NOT pushed)

- **Task 1 PARTIAL:** Immutable-input `ResearchWorkerPipeline.plan()` validates fixture/time and prepares chained queued `validate -> model -> red_team -> referee` tasks. Existing `Dispatcher` lease, retry, cancellation, idempotency and append-only output semantics reused. Persisted source collection-to-claims lineage and live-source acceptance still incomplete.
- **Task 2 PARTIAL:** The `model` handler actually runs existing `ScoreEngine` plus `Synthesizer` with chronological checks; stores compact 1X2 probabilities, four model version hashes, model disagreement, and input hash. No fabricated xG/halftime and no champion promotion.
- **Task 3 PARTIAL:** `RedTeam.inspect` and independent `ScientificReferee.decide` now run via sequential queued worker handlers using their predecessor's immutable results. Two unchanged critical reviews lead to abstain. No empirical improvement/ablation proven.
- **Task 4 PARTIAL:** Existing pure settlement retained; no actual result feed or append-only hosted forward journal added.
- **Task 5 PARTIAL:** Four *local* expert worker handlers integrated and tested. Full 14-role hosted runtime, dashboard and daily automation still incomplete.
- **Task 6 NOT_STARTED:** Pilot and goal radar remain off.
- **Verification:** newly added worker-pipeline suite **12/12 passed**; full expert suite **161 passed**; foundation **34 passed + 2 skipped** and Phase-2 **73 passed** in this development phase (the latter two before this test-only addition). Offline replay `reports/experts/worker_pipeline_demo.json` shows all four stages done and valid audit, with **synthetic** evidence and `publishing_enabled=false`. Historical archive's real kickoff time remains unknown and not invented as a real observation. The global CI command exceeded execution time; native/hosted PostgreSQL and GitHub Actions were NOT accepted this turn.
- **Delivery:** local full/delta ZIP only. GitHub integration was previously denied write access (HTTP 403), no claim of push, no Supabase/migration/production modification. New readme `docs/worker_pipeline.md`.
- **Next:** strong persisted-source published-at attestation and collect->validate linkage; then real results/settlement journal, multi-season validations, hosted worker security and disabled daily scheduler.

---
## 2026-10-16 — Calibration challenger incremental development (local delivery)

- Task 1: prior queue/source bridge preserved; fixed isolated tests using independent source policy registry per case. Live expert and hosted acceptance still PARTIAL.
- Task 2: PARTIAL. Added `experts/calibration.py` multiclass temperature-scaling challenger and `experts/calibration_benchmark.py`, restricted to 1X2 and no score-matrix override. Chronological split: 135 model train, 73 calibrator train, 98 untouched test. Poisson baseline log loss 1.110270 / Brier 0.671348; temperature 1.269921 challenger log loss 1.078709 / Brier 0.651689. Single-season retrospective only, no automatic champion promotion. See docs/calibration_challenger.md and reports/experts/calibration_challenger.json.
- Task 3: review policies preserved; full real evidence-backed Red Team ablation remains PARTIAL.
- Task 4: previous deterministic virtual-only settlement preserved; automated real-result collection and journal not complete.
- Task 5: dispatcher/bridge preserved; hosted dashboard and running 14-role orchestration not complete.
- Task 6: NOT_STARTED; pilot remains off.
- Verification: expert suite **149 passed**, foundation suite **34 passed + 2 skipped**, collection/source/dispatcher selected suite **28 passed** after registry isolation correction; Python compilation succeeded. This is **not** full multi-project native/hosted CI.
- GitHub: this increment is **local ZIP only**; no GitHub PR update or commit claimed. Prior authenticated blob write resulted in HTTP 403 and this environment lacks direct remote write authorization. Supabase unchanged.
- Next: source evidence publication-time validation, actual model/review worker handlers, prospective result source adapter, multi-season calibration, full native/PostgreSQL JWT acceptance, then paused daily workflow. Never enable pilot before gates.

---

# 2026-10-16 — FOLLOW-UP incremental checkpoint (local only)

Branch ZIP baseline `dd8c67fadd9e92487c534c0e4afa3e205a04e393` plus the previously delivered local delta. **GitHub push remains BLOCKED**: Git blob API returned HTTP 403 in the preceding attempt; direct Git CLI cannot resolve github.com in this container. No claim of a remote commit or PR update. No Supabase / migrations / production / pilot changes.

**Task 1 — PARTIAL:** `engine/queue.py` source worker now checks lease ownership before raw snapshot publication and before publishing normalized results and completing the job; explicit retry/fencing tests. Rejects sources without a valid nonexpired reviewed source policy, recorded license and HTTPS terms link. Added a date-specific collection cycle without breaking legacy keys, linked cached jobs with original snapshots in local SQLite table `v2_job_snapshots`, and added `experts/collection_pipeline.py` to connect an actually completed v2 collection to an immutable fixture-verification expert task. The source-to-expert acceptance test uses synthetic HTTP fixture data; NOT hosted live acceptance, NOT published-time lineup or odds proof.

**Task 2 — PARTIAL:** Previously added team-goal markets unchanged this increment. Multiple seasons calibration/uncertainty still open.
**Task 3 — PARTIAL:** Existing Red Team and Scientific Referee unchanged; independent performance ablation still open.
**Task 4 — PARTIAL:** Previous pure `experts/settlement.py` unchanged; real verified post-match results and future-only settlement journal still missing.
**Task 5 — PARTIAL:** Local queue bridge above, but all expert handlers, actual scheduling and Vercel dashboard not integrated.
**Task 6 — NOT_STARTED:** Pilot/learning/radar disabled.

**Local test evidence:** expert 122 passed; foundation 34 passed, 2 skipped; queue + bridge regression 49 passed; Phase-2 selected quick/archival checks 72 passed. All referenced tests were run here. Four previously missing international artifact classes were recovered from the user's `AI_Betting_Lab_GitHub_Bolum_1.zip` and `AI_Betting_Lab_GitHub_Bolum_2.zip` without overwriting tracked files. Exact raw snapshot SHA and chronological fold tests passed. Full international prediction replay exceeded a 120-second execution limit and is NOT validated. `psycopg` is absent; hosted/native PostgreSQL and complete CI not claimed.

**Next:** complete verified source evidence persistence with independent published-at, real worker handler wiring for model/review, multi-season calibration/uncertainty, verified final score source and forward-only result tracking, disabled daily scheduler, Auth/JWT/RLS and live odds tests before prospective pilot. On a write-enabled GitHub session, compare remote HEAD before upload; do not overwrite concurrent work. See `docs/collection_pipeline.md`.

---
# 2026-10-16 — Ek yerel geliştirme (henüz GitHub'a aktarılamadı)

Referans ZIP: feature/expert-engines @ dd8c67f.
Görev 1 PARTIAL: experts/source_bridge.py, kaynak snapshot'larını ham SHA-256,
adapter parse, normalize edilmiş satır, gözlem zamanı, kimlik/hedef ve
kaynak politikası üzerinden doğrulayan yalnız offline köprü.
Görev 2 PARTIAL: experts/football.py, workflow.py; ev/deplasman takım golleri
alt/üst ve yayınlanan olasılık çıktıları.
Görev 4 PARTIAL: experts/settlement.py; salt hesaplamalı 90 dakika sanal
settlement (won/lost/push/pending/blocked), provider void kuralları yoksa blok.
Görev 3 ve 5 eski PARTIAL; Görev 6 NOT_STARTED.

Test: 114/114 expert başarılı; foundation 34 geçer / 2 skip.
Full Python CI 273 test, 6 ortam kaynaklı psycopg import hatası, 7 skip.
Ayrı phase2 test 66 içinde eksik snapshot/prediction arşivi nedeniyle 4 hata.
GitHub create_blob yetki engeli 403; bu değişikliklerin PR #1'e commit/push'u
gerçekleştirilemedi. Main ve Supabase değiştirilmedi. Pilot kapalı.

Detay: IMPLEMENTATION_HANDOFF_20261016.md. Yeni geliştirmeler yalnızca
kullanıcıya teslim edilen tam kaynak ZIP ve değişiklik ZIP'inde mevcut.

---
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
# Güncel devam — bağımsız devralma 2026-10-16

MASTER_PROGRESS.md'nin en yeni bölümünü ve docs/result_revisions.md'yi oku.
Taban dd8c67f; worktree /workspace/scratch/cb6ab5446cf9/abl-result-development.
Yerel entegrasyon commit'i 1cb4817. Güncel test: 370/368 pass/2 native skip;
PGlite 123 pass. ZIP'in büyük tarihsel dosyaları yerelde korundu, Git'e eklenmedi.
Yeni experts/result_versions.py: append-only düzeltme, hakem onayı, sürümlü grade,
kalibrasyon ve paired-model metrikleri. ResultScheduler bağlıdır. Eski performance
alanı ilk-sonuç tarihçesi; current_performance güncel kabul edilen sonuçları kullanır.
Tamamı yerel trusted-process; hosted güvenlik veya canlı portföy kabulü yok.

Sıradaki: tüm dosyaların uzak blob eşleşmesini ve PR CI'ı doğrula; sonra
gerçek sağlayıcı publication-time sözleşmesi, çok sezonlu modeller/ablation,
devre dışı günlük araştırma ve dashboard. Pilot açma. Supabase migration yalnız
ayrı kullanıcı onayından sonra uygulanabilir. Yeni prompt beklemek gerekmez.
Komutlar: python -m scripts.ci_python; python -m unittest tests_experts.test_result_versions -v.

# Son ek — iki sezon 2026-10-16

Son kaynak ağacında tam test 372/370 pass/2 skip (89.709s); pencere düzeltmesi dahil.

experts/multiseason.py eklendi; 612 gerçek maç/331 ayrı test maçı. Kaynak dosyası
evidence/phase2/raw/openfootball-2025-26.json ve metadata SHA ile tekrar üretilebilir.
`python -m experts.multiseason --out reports/experts/multiseason_20261016.json`.
Tam regresyon 372/370 pass/2 skip; son scheduler correction-to-window düzeltmesi
için 21 hedef test geçti. PR CI 38936533233 Python/native/PGlite başarılı.
Son artışı GitHub'a aktar ve uzak blob eşleşmesini doğrula; sonra MASTER_PROGRESS
açık işleri sırasıyla sürdür. Yeni migration uygulanmadı, hosted JWT hâlâ açık.

