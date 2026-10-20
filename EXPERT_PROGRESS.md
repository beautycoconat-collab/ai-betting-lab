# 2026-10-19 — Uzman 01/14 günlük çevrim bağlantısı

- Baş Koordinatör günlük çevrimi kaynak kuyruğu, model araştırması ve sonuç uzlaştırma ile birleştirir: **PARTIAL** (hosted worker kapalı).
- Kaynak Avcısı OpenLigaDB için kalıcı kota/lease defteri şartıyla çağrılır: **PARTIAL** (Bundesliga canlı kapsam; geniş lig keşfi henüz yayınlanmıyor).
- Uzman 06–11 mevcut model/Red Team/Hakem zinciriyle çalışır; çözülmeyen kanıtta sonuç `conditional_scenarios` veya `insufficient_data` kalır.
- Uzman 14 yalnız önceden kilitlenmiş ileriye dönük tahmin + doğrulanmış sonuç planlarını derecelendirir: **PARTIAL**. Bugünkü dashboard adayları onaylanmış ileri tahmin sayılmaz; sahte Brier/Log Loss üretilmez.
- Risk/portföy ve pilot: **BLOCKED / KAPALI**.

## Vercel dashboard yayın kabulü — 2026-10-19

**Dashboard yayında:** https://ai-betting-lab.vercel.app/ . Kullanıcının üretim dağıtımı için devam onayından sonra `6yD5cZV4npcW6Epat3uThRnvRTm4` READY oldu. Vercel proje ID: `prj_5bVfIsnlr2SKOurNjyUlgczkFxDc`; takım `beautycoconat-8169s-projects`. Vercel Drop ile 40 kaynak dosyası yüklendi; GitHub otomatik bağlantısı kurulmadı. Paket GitHub `a580320` sürümünün runtime dosyalarını ve doğrulanmış JSON'unu içerir. Paket SHA-256: `0dbc62f601b796fc26f7b2926c78da7898b4363aee6facc23e8f9beeae23d3b3`.

Gerçek hosted HTTP kabulü: 19/23/24/25 Ekim sorguları 200 ve sırasıyla 0/1/6/2 maç; hatalı tarih 400, olmayan fixture 404. Statik JSON yerel kaynak dosyasıyla byte-byte eşit. Detay API iki koşullu senaryoyu aynen döndürüyor, tüm model 1X2 kütleleri geçerli. API `no-store`; yürütme false. Kanıt: `reports/experts/vercel_http_20261019.json`.

Tarayıcıda gerçek uygulama açıldı: 23 Ekim seçimi → Stuttgart/Mönchengladbach kartı → saha senaryosu → ensemble olasılıkları/skorlar/piyasalar → Poisson model değişimi → gerçek Red Team/Hakem needs_reanalysis ve abstain/skip kararları. 14 rolün eksik veri/blocked durumları görünür. Bu gerçek masaüstü tarayıcı kabulüdür; mobil cihaz kabulü yapılmadı. Tarayıcı logundaki görülen hatalar Chrome uzantısına ait, uygulama hatası olarak sayılmadı.

**Açık sınırlar:** Yayın, işçinin oluşturduğu doğrulanmış kaynak snapshot'ını okuyor. Vercel hosted DB credential bağlantısı ve JWT/RLS kabulü tamamlanmadı; Supabase canlı okuması etkin değil. Sürekli günlük veri/yeniden yayın otomasyonu etkin değil. Kaynak snapshot'ı 24 saati geçince güncel fikstür gösterimi güvenle kapanır; ertesi gün kendiliğinden yenilenmiş gibi sunulmaz. Diğer ligler, dört eşleşmeyen maç için tahmin, gerçek oran/CLV/ROI ve tüm 14 rolün canlı araştırması tamamlanmadı. Pilot, portföy ve cron kapalı; migration veya yetki değişikliği yok.

Sıradaki iş: yalnız bu repoya Git bağlantısı veya kontrollü artifact dağıtım hattı; kota durumunu koruyarak günlük yenileme; hosted en az yetki/JWT kabulü; güncel sezon eğitim kapsamı ve kesin saha kanıtı. Üretim dashboard yayını bu güvenlik kapılarının geçtiği anlamına gelmez.

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
# Uzman motorları — 15 Ekim 2026

Bu dal, `31b30d5105abb1368839014c9a15b211fd7ce1f5` üzerine uyumlu Python genişletmesidir.
Mevcut modeller, foundation sözleşmeleri, kuyruk, bütçe korumaları ve 001–005 migration'ları değiştirilmedi.
Önceki oturumda push edilemeyen uzman dosyaları geçici ortamda kaybolmuştu. Bu çalışma yeniden kuruldu ve yeniden test edildi; eski commit/test sonuçları yeni çalışma için kanıt sayılmadı.

## Gerçek kapsam

| Rol | Yürütülebilir işlev | Durum / kalan iş |
|---|---|---|
| 01 Koordinatör | İstanbul gününe göre maç planı, bağımlı kalıcı görevler, idempotency; mevcut lease/retry motoru | PARTIAL: otomatik worker dispatcher bütün uzmanlara bağlanmadı |
| 02 Kaynak Avcısı | Registry uygunluğu, izin süresi, mevcut adapter/kota kuyruğu, keşif işi planlama | PARTIAL: bu oturumda yeni sitelerin lisansı veya canlı erişimi doğrulanmadı; registry tarihsel incelemeyi kullanır |
| 03 Veri Doğrulayıcı | Kimlik/hedef/zaman/snapshot denetimi, çelişkileri karantina çıktısında tutma | PARTIAL: canonical eşleştirme mevcut engine'de; yeni servis hosted quarantine tablosuna yazmaz |
| 04 Kadro/Taktik | Kaynaklı iddiaları doğrulama, eksik konu ve bilinmeyenleri raporlama | PARTIAL: gerçek kadro/sakatlık veri adapteri yok; oyuncu etkisi üretilmez |
| 05 Dış Tahmin | İzin ve yayın zamanı kontrollü mevcut ingest, sıfır model ağırlığı | BLOCKED canlı toplama: doğrulanmış dış tahmin adapteri yok |
| 06 Takım Gücü | Mevcut Elo, rakip düzeltilmiş hücum/savunma, betimleyici son 10 maç formu ve dinlenme | PARTIAL: xG/xGA null; ayrı ileri özellik modeli yok |
| 07 Skor Motoru | Dört mevcut model, girdi/model SHA-256, sonsuz PMF ve dışarıda kalan kütle | Yerel matematiksel çekirdek çalışıyor; hosted kayıt ve belirsizlik kestirimi PARTIAL |
| 08 Piyasalar | 1X2, tam/yarım çizgili alt/üst, KG Var, ev handikapı; push ayrımı | Desteklenen yerel piyasalar çalışıyor; yarılar insufficient_data, çeyrek handikap desteklenmez |
| 09 Sentezleyici | Eğitimden ayrı doğrulamada skor log-loss minimizasyonu, aynı çıktılı modelleri gruplama | PARTIAL: kalibrasyon ölçülür, kalibrasyon dönüşümü yok; genel korelasyon kümeleri yok |
| 10 Red Team | Sızıntı, düşük örneklem, kadro eksikliği, model ayrılığı, yüksek güven, ortak upstream | Deterministik kurallar çalışıyor; performans katkısı ablation ile henüz kanıtlanmadı |
| 11 Hakem | Bağımsız tekrar denetim, kanıt referansı, iki tur, abstain/skip, idempotent audit | Yerel protokol çalışıyor; hosted rol yürütmesi ve semantik senaryo çözümü PARTIAL |
| 12 Oran Analisti | Zaman/izin/hedef kontrolü, marj/no-vig/EV, karşılaştırılabilir kapanış fiyatı CLV | PARTIAL: gerçek canlı oran adapteri yok; CLV gerçek veriyle test edilmedi |
| 13 Risk Yöneticisi | Balanced limit ön kontrolü, 50 TL varsayımıyla uyumsuzluğu reddetme, ileriye dönük wait/skip journal | PARTIAL ve kapalı: bet kararı/kupon yürütme yok; eski cüzdan korunur |
| 14 Öğrenme Denetçisi | Brier/log-loss, skor Brier, kalibrasyon kutuları, ROI/DD ayrımı, 7/30/90/180 pencereleri, challenger ön incelemesi | PARTIAL: otomatik promotion yok; zaman bloklu bootstrap ve ablation eksik |

Hiçbir rol yalnız adı bulunduğu için tamamlandı sayılmamaktadır. Test edilmiş yerel işlevler, canlı kaynak veya hosted entegrasyon başarısı anlamına gelmez.

## Üç çalışma sistemi

- `ResearchLab`: mevcut modeller → doğrulama → skor/sentez → piyasalar → itiraz/hakem → oran → risk ön izlemesi. Eksik kanıtta iki turdan sonra skip. Koleksiyon görevlerini planlar; onları yürütmüş gibi işaretlemez. Takım gücü analizi ayrıca benchmark'ta çalışır; model girdisine kanıtsız katsayı eklemez.
- `StrategyExperiments`: yalnız tarihsel test, toplu metrik, Supabase kupon satırı üretmez. Oran yoksa ROI/CLV yoktur.
- `PortfolioJournal`: yalnız o anda üretilen ileriye dönük wait/skip kararlarını mevcut append-only hash zincirine kaydeder. Tarihsel kayıt ve gecikmiş yeni karar reddedilir. Sıfır stake, yürütme kapalı.

`ResearchLab` girdi ve çıktıları model/version hash ile yerel audit'e append-only kaydedilir; aynı tahmin tekrarında yeni çıktı satırı yazılmaz. ReviewSession iki tur sınırını kendi audit olayları üzerinde uygular; eski foundation review tablolarıyla ortak bir hosted oturum yürütücüsü henüz yoktur. Yerel SQLite dosyasına erişim güvenilir süreç sınırıdır, bulut rol yetkilendirmesi değildir.

## Çalıştırma

```bash
python -m pip install -r requirements-cloud.txt
python -m scripts.ci_python
python -m unittest discover -s tests_experts -v
python -m experts.benchmark --out reports/experts/benchmark.json
npm ci --prefix supabase/tests --ignore-scripts --no-audit --no-fund
node supabase/tests/validate.mjs
node supabase/tests/validate-phase2.mjs
node supabase/tests/validate-foundation.mjs
node supabase/tests/validate-cloud.mjs
```

Benchmark yalnız depoda bulunan 306 gerçek Bundesliga maçını kullanır. Testlerde `example.invalid`, A/B takımları ve sabit UUID kullanılan kayıtlar açıkça sentetiktir. Gerçek maçların eksik başlama saatleri doldurulmaz. Arşiv 2026'da gözlemlendiği için 2025 tahminleri retrospective olarak etiketlenir.

İleriye dönük kullanım; veri erişim zamanı, doğrulanmış kaynaklar, JWT/Auth/RLS kabulü, belirsizlik ve yürütücü entegrasyonu tamamlanmadan açılmamalıdır.
# 2026-10-16 increment

Latest: bounded immutable task inputs and late-binding rejection added;
11 dispatcher tests pass, full suite 225 pass / 7 skip. Existing limitations
remain: all expert handlers and live collection acceptance are not complete.

Roles 01/03: PARTIAL. Local Dispatcher invokes registered handlers and the
existing DataValidator, persists output and task completion atomically, fences
expired/cancelled workers, blocks missing handlers/dependency outputs. Nine
synthetic local acceptance tests passed. No live source or hosted worker
acceptance claimed. Other roles retain their prior status below.

# 2026-10-16 bağımsız kabul güncellemesi

Uzman 14 PARTIAL: sürümlü doğrulanmış sonuçlara bağlı Brier/Log Loss,
1X2 reliability bins, 7/30/90/180 capture-time pencereleri ve eşleşmiş maçlarla
model karşılaştırması eklendi. Sonuç düzeltmesi önce karantina, sonra kanıtlı
yerel hakem onayı gerektirir; eski sonuç/grade silinmez, yeni metrikte mükerrer
tahmin sayılmaz. Kapsama/abstain denominator eksikse null; ROI/CLV fiyat olmadan null.
Uzman 02/03 PARTIAL: OpenFootball gerçek ağ formatı replay doğrulaması 306/0.
Diğer uzmanların daha önceki PARTIAL/BLOCKED sınırları devam eder.
Test: 370 run/368 pass/2 skip, PGlite 123 pass. Canlı pilot/hosted kabul yok.

# Uzman 09/14 — 2026-10-16 ek doğrulama

İki sezonlu walk-forward (612 gerçek Bundesliga maçı, 331 farklı test maçı)
çalıştı; üç dönem de baseline'a karşı raporlandı. Uzman 09 hâlâ PARTIAL: tek lig,
canlı model veya kârlılık kabulü değil. Uzman 14 PARTIAL: scheduler/CLI pencereleri
son onaylı skor revizyonundan hesaplanıyor, eski grade'ler silinmiyor.
Yeni fixture/abstain denominator ve fiyat kanıtı yoksa ilgili alanlar null kalır.
372 full test/370 pass/2 skip; son pencere düzeltmesine 21 hedef test pass.

# Son ek — radar ve otomasyon

14 uzman hâlâ belirtilen PARTIAL/BLOCKED sınırlarındadır. Ayrı Canlı Gol Radarı
modülü PARTIAL tarihsel replay / BLOCKED canlı. Yedi sentetik kabul testi geçti;
gerçek canlı doğruluk veya kalibrasyon kanıtı yok. Elle çalıştırılan offline
replay workflow hazır; günlük üretim veya sanal portföy etkin değil.
Son tam yerel regresyon 379 run/377 pass/2 native skip.


### Dashboard projection (2026-10-16)
The actual baseline/Elo/Poisson/DC artifacts now feed 18 historical match details
and supported MarketSpecialist markets. 14 roles are visible but no_run is not
success. Red Team/referee show missing decisions explicitly. Portfolio/CLV/ROI
remain BLOCKED pending verified records. UI PARTIAL until browser + hosted acceptance.

### 2026-10-19 — persisted research display
Score engine now persists bounded display summaries and ensemble-derived markets.
The dashboard validates the complete validator/model/red-team/referee DAG and
immutable input hashes before projection. Only these four roles receive done
states for those records. Research mode is never upgraded to live verified data.
Legacy worker records are supported without inventing missing score distributions.
# 2026-10-20 — Uzman 02 kota kapısı

- Kaynak Avcısı hosted çalışmada HTTP öncesi merkezi Supabase rezervasyonu yapar: **FULL (kod/test)**.
- Onaysız, süresi dolmuş, günlük kotası dolmuş veya altı saat aralığını sağlamayan kaynakta HTTP çağrısı yoktur.
- Supabase ulaşılamazsa açık devam etmek yerine `hosted_quota_unavailable` ile durur.
- Canlı zamanlanmış worker: **BLOCKED**; JWT/RLS ve worker kabul işaretleri açılmadı.

