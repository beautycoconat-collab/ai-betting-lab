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

