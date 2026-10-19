## Vercel dashboard yayın kabulü — 2026-10-19

**Dashboard yayında:** https://ai-betting-lab.vercel.app/ . Kullanıcının üretim dağıtımı için devam onayından sonra `6yD5cZV4npcW6Epat3uThRnvRTm4` READY oldu. Vercel proje ID: `prj_5bVfIsnlr2SKOurNjyUlgczkFxDc`; takım `beautycoconat-8169s-projects`. Vercel Drop ile 40 kaynak dosyası yüklendi; GitHub otomatik bağlantısı kurulmadı. Paket GitHub `a580320` sürümünün runtime dosyalarını ve doğrulanmış JSON'unu içerir. Paket SHA-256: `0dbc62f601b796fc26f7b2926c78da7898b4363aee6facc23e8f9beeae23d3b3`.

Gerçek hosted HTTP kabulü: 19/23/24/25 Ekim sorguları 200 ve sırasıyla 0/1/6/2 maç; hatalı tarih 400, olmayan fixture 404. Statik JSON yerel kaynak dosyasıyla byte-byte eşit. Detay API iki koşullu senaryoyu aynen döndürüyor, tüm model 1X2 kütleleri geçerli. API `no-store`; yürütme false. Kanıt: `reports/experts/vercel_http_20261019.json`.

Tarayıcıda gerçek uygulama açıldı: 23 Ekim seçimi → Stuttgart/Mönchengladbach kartı → saha senaryosu → ensemble olasılıkları/skorlar/piyasalar → Poisson model değişimi → gerçek Red Team/Hakem needs_reanalysis ve abstain/skip kararları. 14 rolün eksik veri/blocked durumları görünür. Bu gerçek masaüstü tarayıcı kabulüdür; mobil cihaz kabulü yapılmadı. Tarayıcı logundaki görülen hatalar Chrome uzantısına ait, uygulama hatası olarak sayılmadı.

**Açık sınırlar:** Yayın, işçinin oluşturduğu doğrulanmış kaynak snapshot'ını okuyor. Vercel hosted DB credential bağlantısı ve JWT/RLS kabulü tamamlanmadı; Supabase canlı okuması etkin değil. Sürekli günlük veri/yeniden yayın otomasyonu etkin değil. Kaynak snapshot'ı 24 saati geçince güncel fikstür gösterimi güvenle kapanır; ertesi gün kendiliğinden yenilenmiş gibi sunulmaz. Diğer ligler, dört eşleşmeyen maç için tahmin, gerçek oran/CLV/ROI ve tüm 14 rolün canlı araştırması tamamlanmadı. Pilot, portföy ve cron kapalı; migration veya yetki değişikliği yok.

Sıradaki iş: yalnız bu repoya Git bağlantısı veya kontrollü artifact dağıtım hattı; kota durumunu koruyarak günlük yenileme; hosted en az yetki/JWT kabulü; güncel sezon eğitim kapsamı ve kesin saha kanıtı. Üretim dashboard yayını bu güvenlik kapılarının geçtiği anlamına gelmez.

## Vercel yayın denemesi — 2026-10-19

Kullanıcı dashboard önizlemesi ve eklenti başarısızsa tarayıcı üzerinden çalışma için onay verdi. Vercel MCP create_project 403 verdi; CLI kurulu değil. Tarayıcıda proje oluştu: `beautycoconat-8169s-projects/ai-betting-lab`. Vercel GitHub bağlantısı `bengbengg0` hesabında olduğundan asıl kaynak repo içe aktarılamadı; herhangi bir yeni GitHub yetkisi verilmedi. İncelenmiş kaynaklardan 40 dosyalık, yaklaşık 701 KB deployment paketi yüklendi; veritabanı sırrı yok.

İlk deployment `4KHVYAxrCNWGWhohxe7hiYVYApmP` ERROR: PYTHON_ENTRYPOINT_NOT_FOUND. Build günlüğünün işaret ettiği `[tool.vercel] entrypoint = "api.dashboard:handler"` pyproject.toml'a eklendi. Dashboard Python regresyonu 31/31 geçti. Düzeltilen paket mevcut projeye yüklendi, fakat son ekran açıkça **New Production Deployment / Deploy to Production** diyor. Önizleme onayını üretim onayı saymadan bu düğmeden önce duruldu. Başarılı yayın veya API/browser kabulü henüz yok. Yeni migration, portföy, pilot, cron veya başka proje değişikliği yok.

Devam: Kullanıcı bu yalnız-okunur dashboard için Production dağıtımını onaylarsa mevcut hazır Vercel ekranından sürdür; veya GitHub bağlantısına yalnız bu repo erişimi kullanıcı tarafından sağlandıktan sonra feature dalı Preview dağıtımını seç. Build/HTTP/API/etkileşim kabulünü gerçekten çalıştır; giriş noktası düzeltmesini hosted build başarılı olmadan tamamlandı sayma.

## GitHub teslimat doğrulaması — 2026-10-19

Uzak `feature/expert-engines` commit **9bd15a79917159e6d79fd115f2fa5a6433d3e16b**, yerel test edilmiş ağaca `git diff --exit-code` ile eşit doğrulandı. PR #1 bu sekiz yeni commit'i içeriyor ve açıklaması güncellendi. Git CLI kimlik erişimi yoktu; önceden yetkilendirilmiş GitHub tarayıcı yüklemesi kullanıldı. Yerel Git bundle checkpoint mevcut.

Bu commit'in GitHub Actions **39290072695**, verify job **118188393455** sonucu **success**: Python, native PostgreSQL bağımsız bağlantılar, dashboard Node ve PGlite migration/güvenlik adımları geçti. Bu hosted JWT/Auth/RLS kabulü değildir. Yerel Python kanıtı 410/403/7 olarak ayrı raporlanır.

Vercel güvenli girişinde hesap sayfası görüldü; AI Betting Lab proje araması içerik hatası verdi, tek yeniden yükleme sonrasında tekrar giriş sayfasına yönlendi. Proje/deployment kabulü doğrulanamadı; yayın yapılmadı. Bir sonraki oturum önce mevcut Vercel oturumunu/proje erişimini doğrulamalı; giriş veya yayın kabulü gerekirse güvenli akışı kullanmalı. Başka projelerde işlem yapılmadı.

## 2026-10-19 — Gerçek fikstür ve koşullu model bağlantısı

**Durum: PARTIAL.** OpenLigaDB Bundesliga 2026/27 kaynağı gerçek ağ erişimiyle toplandı: 306 normalize kayıt, 0 ret. 19 Ekim için bu ligde maç yok; sonraki 7 günde 9 maç var. Başka ligler kapsanmış sayılmaz. Beş maçta tam takım adı/eğitim eşleşmesi var; dört maç `insufficient_data`. Sağlayıcı neutral bilgisini vermediğinden her uygun maç için iki ayrı venue senaryosu hesaplandı; bunlar birleştirilmiş nihai tahmin değildir. 612 gerçek tarihsel maç, kronolojik eğitim/doğrulama ayrımı kullanıldı. Güncel sezon eksikleri ve eski eğitim kesimi görünür.

Mevcut UI korunarak tarih düğmeleri, senaryo seçimi, Elo/Poisson/Dixon–Coles/baseline/ensemble olasılıkları, skorlar, piyasalar ve gerçek deterministik rol analizleri bağlandı. Kadro, dış tahmin, oran ve gerçekleşmiş öğrenme için veri yok; risk yürütmesi kapalı. Red Team ve iki tur Hakem gerçek kodla çalıştı; eksik kadro kanıtı nedeniyle abstain/skip. Bu, 14 uzmanın FULL olduğu anlamına gelmez.

Yalnız `oswpkwwbjwyktuqcakhr` test projesindeki mevcut tablolara kontrollü, idempotent DML uygulandı: 1 gerçek kaynak snapshot metadata kaydı, 9 maç, 50 koşullu challenger model çıktısı, 10 araştırma audit kaydı, 90 rol yürütme bağlamı. Tüm maç sayısı 21; eski 12 maç korundu. İçe aktarma önce rollback ile, sonra commit ve aynı veriyi yeniden oynatma ile doğrulandı. Olasılık kütlesi ve maç öncesi cutoff SQL kontrolleri geçti. Model kod hash'i ile model durum hash'i ayrı tutuluyor. `prediction_runs` champion sayısı 0. Bu doğrulama yönetici MCP SQL erişimidir; hosted JWT/Auth/RLS veya düşük yetkili worker kabulü değildir. Migration, yetki ve cüzdan değişmedi.

Yerel tam test: `python -m scripts.ci_python` → 410 test, 403 başarılı, 7 kontrollü atlama. Node sözdizimi/veri/UI smoke testleri ayrı yürütüldü; gerçek tarayıcı veya mobil layout kabulü sayılmaz. Yeni PGlite/native/hosted Auth testi çalıştırılmış sayılmaz.

Sıradaki somut işler: GitHub branch/PR teslimatını doğrula; Vercel proje oturumu/preview yayın kabulü; düşük yetkili hosted bağlantı ve JWT/RLS kabulü; devamlı kaynak kota deposu ve otomatik artifact yayınını kabul ettikten sonra zamanlayıcıyı etkinleştir. Pilot ve portföy açılmayacak. Eksik kadro/oran adapterleri, bağımsız ablation ve ileriye dönük performans hâlâ PARTIAL/BLOCKED.

Komutlar:
```sh
python -m scripts.ci_python
node --check public/app.js
node scripts/check_dashboard.mjs
node scripts/test_dashboard_ui.mjs
# Kota geçmişi bulunan mevcut SQLite ile; yeni boş DB ile kota sıfırlamayın:
python -m dashboard.daily --database data/dashboard-live.sqlite --collect
```

GitHub Actions workflow yalnız manuel ve `LAB_RESEARCH_ACCEPTED` kapılıdır; cron yok. İlk çalıştırma korunmuş quota cache olmadan güvenle durur. Hosted okuma `LAB_DASHBOARD_HOSTED=true` ile isteğe bağlıdır; `cloudcheck.config` proje/verify-full TLS/CA doğrulaması gerekir. Bağlantı sırları yalnız sunucu ortamında sağlanmalı. API model eğitmez; işçi üretilmiş projection'ı okur. Statik veri 24 saat sonra güncel fikstür olarak gösterilmez.

---

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
# Uzman motorları yeniden doğrulama — 15 Ekim 2026

Bu bölüm mevcut çalışma dalına aittir; aşağıdaki Aşama 0.1 kayıtları tarihsel sonuçlardır.

GitHub PR #1 üzerinde `Complete offline and native verification` koşusu `38804459813` başarıyla tamamlandı. `verify` işi; Python regresyonları, PostgreSQL 17 servis konteynerindeki bağımsız native oturum ve eşzamanlılık kontrolleri ile dört PGlite grubunun tamamını geçti. Bu sonuç, aşağıdaki yerel native ortam eksikliğini kapatan ayrı CI kanıtıdır; hosted Supabase JWT/Auth kabulü değildir.

| Ortam | Bu çalışmada gerçekten elde edilen sonuç |
|---|---|
| Python | `python -m scripts.ci_python`: 221 test; 214 geçti, 7 atlandı. Yeni uzman testleri 62 adet. |
| Atlamalar | Büyük uluslararası arşiv gerektiren 5 eski test; DSN/opt-in gerektiren 2 native test. |
| PGlite | Dört script yeniden çalıştı: 23 + 28 + 56 + 16 = 123 başarılı kontrol. |
| Native PostgreSQL | Yerel ortamda çalıştırılamadı. PR CI koşusu `38804459813` içinde PostgreSQL 17 servis konteyneriyle bağımsız bağlantı ve eşzamanlılık adımı geçti. |
| Hosted Supabase | Yalnız `oswpkwwbjwyktuqcakhr` üzerinde read-only katalog/ACL kontrolü yapıldı. 67 lab tablosu, RLS kapalı tablo 0, beklenen güvenli search_path dışında SECURITY DEFINER 0. Pilot false. |
| Hosted rol sınırı | anon/authenticated ve 14 worker için predictions, prediction_runs, review_decisions, paper_wallet, wallet_ledger üzerinde INSERT/UPDATE/DELETE yetkisi 0. Bu metadata kontrolüdür; gerçek JWT veya kötü niyetli yazma denemesi değildir. |
| Hosted JWT/Auth | Yeni gerçek kullanıcı JWT testi yapılmadı; açık kabul kapısı. |

İlk regresyon denemesi eksik psycopg bağımlılığı nedeniyle 6 hata verdi. Mevcut requirements-cloud.txt kurulduktan sonra tamamı yeniden çalıştırıldı. İlk test keşfinde import edilen TestCase ikinci kez keşfediliyordu; düzeltilerek yukarıdaki sayıya ulaşıldı. Başarısız ilk koşu başarı olarak sunulmadı.

Gerçek arşiv benchmark'ı: 135 eğitim / 73 doğrulama / 98 bağımsız test maçı. Ensemble ağırlıkları test verisinden öğrenilmedi.

| Model | 1X2 Brier (toplam tanımı) | 1X2 Log Loss | Tam skor Log Loss |
|---|---:|---:|---:|
| Baseline | 0.692886 | 1.135026 | 3.179433 |
| Elo | 0.661306 | 1.092905 | 3.097351 |
| Poisson | 0.671348 | 1.110270 | 3.102978 |
| Dixon-Coles | 0.666377 | 1.105077 | 3.113344 |
| Ensemble | 0.660219 | 1.088914 | 3.071025 |

Ayrı üç genişleyen walk-forward dilimi 134 farklı maç üzerinde değerlendirildi; toplu ensemble skor Log Loss 3.143488. Bu testler aynı sezonu kullanır, iki değerlendirme birbirinden bağımsız ikinci veri seti değildir. Kanıt/model hashleri, fold sınırları, skor matrisi, gerçek sonucu ayrı alanı ve kalibrasyon kutuları `reports/experts/benchmark.json` içindedir. Canlı başarı, kârlılık veya iyi kalibrasyon iddia edilmez.

Ham test günlükleri `reports/experts/python-tests.txt` ve `pglite-*.txt` dosyalarındadır. Migration 001–005 değişmedi. Yeni kullanıcı, migration, yetki veya pilot değişikliği yapılmadı. Mevcut 67 tablonun kayıtlarına yazılmadı. Veritabanı boyutu read-only ölçümde 14.325.427 bayt; bu tek ölçüm organizasyon egress veya güncel plan kotası doğrulaması değildir.

# Aşama 0.1 test raporu — 15 Ekim 2026 (tarihsel)

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
# 2026-10-16 local dispatcher verification

Latest immutable-input increment: 232 tests in 15.334s; 225 passed, 7 skipped.
Dispatcher-specific: 11 passed. Remote browser delivery of preceding increment
verified at 453240f/d3e45a8. Earlier terminal push failure is historical.

Final full regression: 230 tests, 223 passed, 7 controlled skips (21.072s).
Git push failed: no HTTPS Git authentication available. Remote PR unchanged.

Initial full run failed six configuration tests because psycopg was missing.
Installed pinned requirements-cloud.txt; subsequent full run: 228 tests,
221 passed, 7 skipped. Two further boundary tests added; dispatcher suite 9/9
passed. Full final regression pending. No new native/PGlite/hosted results
claimed; historical results below remain historical.

# Bağımsız doğrulama — 2026-10-16 sonuç sürümleri

- `python -m scripts.ci_python`: 370 test, 368 başarılı, 2 native PostgreSQL skip; 39.677 saniye.
- PGlite validate/phase2/foundation/cloud: 23/28/56/16, toplam 123 başarılı.
- Native PostgreSQL bu ortamda yok; hosted Supabase/JWT bu oturumda test edilmedi.
- Gerçek OpenFootball HTTP: 294 kabul, 12 legacy array ret. Parser düzeltmesi
  ve aynı snapshot offline replay: 306 kabul, 0 ret, ek ağ isteği 0.
- İlk devralma koşusu başarısızdı: eksik psycopg/büyük arşiv ve tam aktarılmamış
  ZIP bağımlılıkları. Sabitlenmiş requirements kuruldu; arşivler ZIP'ten yerel
  olarak korundu; final koşu başarılı. Tarihsel rapor sayıları kopyalanmadı.
- Yeni correction/grade yarış testi iki ayrı SQLite bağlantısı kullanır;
  hosted PostgreSQL eşzamanlılığı yerine sunulmaz.
- 001–005 aynı; Supabase'e migration/yetki/kullanıcı/cüzdan yazması yapılmadı.

# Ek kabul — 2026-10-16 çok sezon ve native CI

Son kaynak ağacı tekrar koşusu: 372 test / 370 başarılı / 2 native skip,
89.709 saniye. Son scheduler pencere düzeltmesi bu tam koşuya dahildir.

`python -m scripts.ci_python`: 372 run / 370 pass / 2 native skip, 48.444s.
Son scheduler metrik revizyonu sonrası sonuç/scheduler/CLI: 21 pass.
`experts.multiseason`: iki sezon 612 gerçek maç, 331 farklı test maçı; üç fold
train/validation/test 135/73/98, 306/73/104, 379/104/129. Ham snapshot hash ve
eşsiz kimlik testleri geçti. Skor Log Loss kıyasları reports/experts/multiseason_20261016.json.
PR CI 38936533233 / job 117093518310 (6b0407c): Python regressions, Native PostgreSQL
independent connections, PGlite migration/security adımlarının hepsi success.
Hosted Supabase/JWT bununla doğrulanmış sayılmaz; bu oturumda hosted yazma yok.

# Nihai yerel kaynak ağacı — radar replay dahil

`python -m scripts.ci_python`: 379 test / 377 başarılı / 2 native skip,
55.441s. Yedi yeni radar testi sentetik replay sınamalarıdır; canlı başarı değildir.
Son log reports/experts/intake_python_20261016.txt içindedir.
PGlite 123; native PR CI 38936533233 başarıyla tamamlandı. Hosted JWT/RLS
bağlantısı sınanmadı. Son radar dahil uzak PR CI ayrıca raporlanmalıdır.


## Dashboard increment — 2026-10-16
- `python -m unittest discover -s tests_dashboard -v`: 10/10 passed (4.385s).
- `python -m scripts.ci_python`: 389 executed; 387 passed, 2 native tests
  skipped without DSN (72.609s). Raw sanitized log:
  reports/experts/dashboard_python_20261016.txt.
- `node --check public/app.js`: passed.
- `node scripts/check_dashboard.mjs`: passed, 18 real retrospective fixtures,
  14 roles, 1X2 mass checks, pilot/execution disabled.
- `git diff --check`: passed.
- New dashboard tests cover archive/live separation, all four existing models,
  market complementarity/unsupported half, fixture lookup, bad schema/date,
  read-only DB projection, no implicit database creation, reproducibility and
  public field allowlist. No hosted database write performed.
- Browser visual/mobile interaction QA NOT RUN (managed control-browser skill
  unavailable). Vercel deployment/build NOT RUN. No claim of live data acceptance.
- PGlite/native prior green run remains separate evidence; this increment changes
  no SQL migration. Hosted JWT/Auth/RLS and portfolio acceptance remain BLOCKED.

## 2026-10-19 — persisted worker dashboard bridge
- Dashboard suite: 19 tests passed (2.934s); nine new worker/feed integration
  cases use synthetic evidence with real archived numerical models, not live news.
- Final complete Python run, pinned requirements-cloud.txt installed: 398 tests,
  391 passed / 7 controlled skips (32.349s). Five skips need the separate large
  international archive, two need native PostgreSQL DSN. Raw report:
  reports/experts/dashboard_worker_regression_20261019.txt.
- First full attempt hit six environment errors due absent psycopg; resolved by
  installing the existing requirements, then final suite passed. No dependency
  pin was changed. No cloud or native DB test is claimed from this local run.
- Node render/interaction smoke checks passed (archive, research empty/detail,
  HTML escaping, referee/risk, model switch, selected-date API, unsafe feed).
  This uses a minimal Node harness, NOT browser/layout/mobile verification.
- `node --check public/app.js`, existing publication checks, compileall and
  git diff --check passed. No new migration, hosted write or pilot activation.
- Prior remote native/PGlite green run 38941420495 remains separate evidence;
  new CI execution is to be verified at the new remote head.
