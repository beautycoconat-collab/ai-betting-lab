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
# AI Betting Lab — Geliştirme teslimi (2026-10-16)

## Kodun kökeni
- Kullanıcı ZIP kaynağı: GitHub `feature/expert-engines` @ `dd8c67fadd9e92487c534c0e4afa3e205a04e393`.
- Bu çalışmadaki yeni kodlar **yerel olarak** hazırlanmıştır.
- GitHub'a gönderme denendi, fakat `GitHub create_blob` 403 `Resource not accessible by integration` döndürdü.
- **PR #1 güncellenmedi. Main ve Supabase değiştirilmedi.**

## Somut uygulanmış eklemeler
### Görev 1 — Motor A / PARTIAL
`experts/source_bridge.py`:
- İzinli kaynak ve tamamlanmış `v2_jobs` doğrulaması.
- Kaydedilmiş sıkıştırılmış ham snapshot SHA-256 kontrolü.
- Sınırlı açma (10 MB); izinli kaynak adapteriyle yeniden ayrıştırıp normalize edilen satır ile saklanan kaydı birebir karşılaştırma.
- `snapshot_observed_at <= as_of < kickoff`, tutarlı lig/sezon/takımlar/maç günü/hedef.
- Yayın zamanı, ilk 11 veya oran kanıtını uydurmadan `not_proven` işaretleme.
- Yalnızca **önceden toplanmış kayıtlardan offline doğrulama**; canlı collector/worker uçtan uca henüz yok.
`tests_experts/test_source_bridge.py`: 11 doğrulama ve hata yolu testi.

### Görev 2 — Motor B / PARTIAL
`experts/football.py`: `home_over`, `home_under`, `away_over`, `away_under` pazarları.
- Tam/yarım gol çizgileri ve çizgi eşitliğinde `push`, toplam olasılık kütlesi.
`experts/workflow.py`: 2,5 alt/üst + takım 1,5 üst çıktıları.
`tests_experts/test_team_totals.py` ve `tests_experts/test_workflow.py`: model tutarlılığı ve yüzeyde görünürlük testleri.
- Mevcut skor modelleri korunmuş; yeni kalibrasyon/çok sezonlu model kabulü bu artışta yapılmadı.

### Görev 4 — Motor D / PARTIAL
`experts/settlement.py`: **salt hesaplama, sanal** settlement.
- 90 dakikalık doğrulanmış 1X2, KG, toplam gol, takım golü ve desteklenen handikap.
- `won/lost/push/pending/blocked` sonuçları.
- Ertelenmiş maç `pending`; iptal/terk sağlayıcı kuralı olmadan `blocked` — otomatik iade uydurulmaz.
- Desteklenmeyen çeyrek handikap ve ilk yarı piyasaları reddedilir.
`tests_experts/test_settlement.py`: 12 test.
- Henüz Supabase'e veya ileriye dönük sanal işlem defterine bağlanmadı.

### Görev 3 — Motor C / PARTIAL (önceki sürüm korunmuş)
Red Team ve Bilimsel Hakem kodları değiştirilmedi; katkı ablation testi için gerçek kanıt eksik.

### Görev 5 — Otomasyon/dashboard / PARTIAL (önceki sürüm korunmuş)
Canlı uzman dispatcher entegrasyonu, scheduler ve panel tamamlanmadı.

### Görev 6 — Pilot/Öğrenme/Radar / NOT_STARTED
Sanal pilot ve gerçek veri akışı açılmadı. Auth/JWT/RLS/odds ve canlı veri kabulü bekliyor.

## Yerel test sonuçları
- `python -m unittest discover -s tests_experts -q`: **114/114 başarılı**.
- `python -m unittest discover -s tests_foundation -q`: **36 test, 34 geçti, 2 kontrollü atlandı**.
- `python -m scripts.ci_python`: **273 test, 6 hata, 7 atlandı**. Altı hata bu ortamda `psycopg` kurulu olmadığı için `tests_cloud/test_cloud.py` yapılandırma testlerinde oluştu. Kalan 260 test hata vermedi; bunu tam başarılı CI olarak sunma.
- `python -m unittest discover -s tests_phase2 -q`: **66 test, 4 hata**. Kullanıcıdan yüklenen GitHub ZIP'inde eski uluslararası ham/prediction arşivlerinin bazıları eksik. Bu dosyalar uydurulmadı.
- Gerçek ağ bağlantısı, native PostgreSQL, Supabase hosted/Auth/JWT ve GitHub Actions bu çalışmada tekrar sınanmadı.

## Sonraki gerçek adımlar
1. GitHub yazma yetkisi olan araç/oturumda ZIP içindeki değiştirilmiş dosyaları `feature/expert-engines` dalına aktar; PR #1'e ekle. Önce branch head'i karşılaştır; mevcut değişikliklerin üstüne kör overwrite yapma.
2. `requirements-cloud.txt` bağımlılıklarını kur; eksik eski arşivleri güvenilir kaynaktan temin et; tüm regresyonu çalıştır.
3. Görev 1'de gerçek collector worker + `v2` snapshot ve expert job bağlantısı ile kalıcı doğrulanmış kanıt (kanıt yayın zamanı ayrı) tamamla.
4. Görev 2'den Görev 6'ya önceki ana talimat sırasıyla devam et.
5. Supabase migration için ayrıca kullanıcı onayı iste. Canlı pilotu başlatma.

**Başarı oranı, canlı tahmin kârlılığı veya tamamlanmış altı görev iddiası yoktur.**
