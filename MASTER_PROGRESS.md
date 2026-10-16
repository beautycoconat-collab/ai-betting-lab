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
# Master progress — 2026-10-16

Delivery update: 453240f and d3e45a8 are verified remote commits for dispatcher
and its nine tests. No longer blocked on delivery: browser upload works.
Further local increment: immutable bounded task inputs, late-binding rejection;
11 dispatcher tests pass. Latest full regression: 232 run, 225 passed, 7 skipped.

Final regression: 230 run, 223 pass, 7 skips. Push BLOCKED by missing Git
HTTPS authentication. Local commit fb8d494; PR #1 has not received this increment.
Git bundle preserves changes. No new cloud tests or migrations.

Remote starting point verified: feature/expert-engines at 5b54b79; PR #1.
Local and remote tracked trees matched before development; their histories were
merged without changing source files. Main and migrations 001–005 unchanged.

| Task | Status | Remaining acceptance |
|---|---|---|
| 1 Data/research | PARTIAL | Dispatcher added locally; actual validator binding tested. Collection-to-evidence persistence, all other handler bindings, hosted execution and live acceptance remain. |
| 2 Prediction | PARTIAL | Existing models preserved; multi-season acceptance and separately validated calibration remain. |
| 3 Review | PARTIAL | Existing deterministic review preserved; independent ablation remains. |
| 4 Portfolio/learning | PARTIAL | Existing preview/journal preserved; new policy and full settlement scope remain. |
| 5 Automation/dashboard | PARTIAL | Local dispatcher only; dashboard and disabled daily workflow not implemented in this increment. |
| 6 Pilot/learning/radar | NOT_STARTED | Pilot remains off; JWT and live odds gates open; radar not implemented. |

Role detail remains in EXPERT_PROGRESS.md. This increment changes roles 01 and
03 only. All other role claims remain as previously documented, not FULL by
virtue of having registry entries.

Dispatcher guarantees: transactional output/completion, immutable results,
dependency outputs, role-filtered leases, sanitized retry errors, cancellation,
expired-worker fencing. Handlers must be pure or independently idempotent;
lease fencing does not undo external side effects or stop a running process.
SQLite is a trusted-process boundary, not hosted authorization.

Tests: full suite at seven dispatcher tests: 228 run, 221 pass, 7 skip.
After adding two more boundary tests: dispatcher 9/9 pass. A final full run
is required before claiming 230-test full regression acceptance.
No fresh native/PGlite/hosted run claimed by this increment.

Next: durable immutable input envelopes; collection job linkage; actual
model/review handler bindings; live source-policy revalidation. Then proceed
through tasks 2–6 without enabling deployment or pilot.
# 2026-10-16 — Bağımsız devralma ve sürümlü sonuçlar

Uzak taban tekrar doğrulandı: dd8c67f. ZIP güvenli çıkarıldı; aynı tabanın
değişiklikleri yeni worktree'de birleştirildi. 001–005 migration aynı kaldı.
Görev 4 PARTIAL: yeni VersionedResults, ham kaynak doğrulamasıyla append-only
sonuç sürümleri, karantina/hakem onayı, yeniden değerlendirme ve aynı tahmini
iki kez saymayan güncel 7/30/90/180 günlük metrikleri sağlar. Eski kayıtlar
değişmez. Yerel SQLite bağımsız bağlantı yarışı testi geçti. Hosted kabul değildir.

Tam regresyon: 370 test, 368 başarılı, 2 native PostgreSQL atlandı; 39.677s.
PGlite: 23+28+56+16=123 başarılı. Native ve hosted bu oturumda çalıştırılmadı.
OpenFootball gerçek HTTP isteği: 294 kabul/12 legacy-array ret; adapter düzeltmesi
sonrası aynı ham snapshot offline replay 306 kabul/0 ret, ilave HTTP yok.
Skorun sağlayıcı yayımlanma zamanı bilinmiyor; gözlem zamanı ayrı tutuluyor.
Bu ileriye dönük model başarısı değildir. OpenLiga güncel lisans sayfası metni
doğrulanamadı; yeni live kabul BLOCKED.

Görev 1/2/3/4/5 PARTIAL; Görev 6 NOT_STARTED. 14 rolün tamamına FULL denmez.
Kaynak/worker zinciri ve kalibrasyon yerelde doğrulandı. Hosted JWT/RLS,
izinli canlı kadro/tahmin/oran, çok sezonlu doğrulama, bağımsız Red Team ablation,
dashboard, güvenli portföy işletimi ve gol radarı hâlâ açık.
GitHub API create_blob 403 döndü; önceden onaylı tarayıcıyla küçük dosya grupları
feature/expert-engines dalına aktarılıyor. Nihai uzak SHA teslimde doğrulanacak.
Pilot ve cron kapalı; Supabase'e yazma veya ücretli hizmet yok.

# İki sezonlu walk-forward ve CI — 2026-10-16

Son tam kaynak koşusu 372 test/370 pass/2 skip (89.709s); son pencere düzeltmesi dahil.

Görev 2 PARTIAL ilerledi: 2024–25 ve 2025–26, toplam 612 gerçek Bundesliga maçı;
331 farklı test maçı. Train/validation/test: 135/73/98, 306/73/104, 379/104/129.
Ensemble/baseline skor Log Loss: 3.071025/3.179433, 3.142827/3.262383,
3.035263/3.130691. Tek lig, retrospektif; yeni sezon takımları için fallback
model davranışı dahil; canlı başarı veya otomatik terfi kanıtı değildir.
Ham ikinci sezon JSON'u SHA-256 doğrulamasıyla korunur; çevrimdışı tekrar komutu:
`python -m experts.multiseason --out reports/experts/multiseason_20261016.json`.

Tam test: 372 run, 370 pass, 2 native skip. Son scheduler pencere düzeltmesi
sonrası hedefli sonuç/CLI testleri 21 pass. Güncel performans pencereleri artık
onaylanmış sonuç düzeltmesini kullanır; eski grade'ler audit olarak korunur.
PR CI koşusu 38936533233, job 117093518310: Python, native PostgreSQL ve PGlite
adımları başarıyla geçti (6b0407c ağacı). Son çok sezon artışının CI'ı ayrıca izlenecek.

# Son checkpoint — radar replay ve kapalı otomasyon

Son yerel kaynak ağacı: 379 test / 377 başarılı / 2 native PostgreSQL skip,
55.441s. Radarın 7 sentetik sınır testi dahil. PGlite 123 kontrol aynı migration
ağacında geçti. Önceki native PR CI 38936533233 success; son uzak ağaç ayrı kontrol edilir.

Görev 6 artık PARTIAL (yalnız radar tarihsel replay çekirdeği); canlı radar
BLOCKED: olay kaynağı, kanıt doğrulaması ve gerçek kalibrasyon yok. Model homojen
Poisson baseline, taktik/baskı/şut iddiası yok. Canlı çağrı her zaman BLOCKED.
Görev 5 PARTIAL: research-replay.yml yalnız workflow_dispatch; cron, fetch,
hosted secrets, deploy ve portföy yürütmesi yok.

Açık ana işler: 14 rolün hosted dispatcher/JWT/RLS kabulü; gerçek yayın-zamanı
kanıtları ve izinli kadro/dış tahmin/oran; bağımsız Red Team ablation;
dashboard; sanal portföy muhasebesi ve sürümlü risk politikalarının tam akışı;
canlı champion/challenger ve rollback; pilot kapıları. Hiçbiri FULL sayılmaz.
Tüm görevler için mevcut ana yetki geçerli; bunlar için yeni prompt gerekmez.

