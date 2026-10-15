# Aşamalı kabul ve teslim durumu

## Aşama 1 — bu teslim

| Kabul | Durum / kanıt |
|---|---|
| Kaynak lisans/kota/erişim kararları | Tamam; sources.md, onaylanmayan kaynaklar kapalı |
| İki bağımsız adapter | Çalışıyor; OpenLigaDB/OpenFootball, parser testleri |
| Gerçek ağ verisi | HTTP 200; kaynak başına 306 gerçek gözlem; raporlar |
| Eksik/bozuk satır davranışı | Test edildi; NULL/karantina, skor uydurma yok |
| Idempotent yerel tekrar | Test edildi; cache ve benzersiz gözlem anahtarı |
| Kota başarısız isteği sayar | Test edildi; paylaşılan SQLite üzerinde 6 eşzamanlı istemciden 1 rezervasyon |
| 429 / uzun Retry-After | Test edildi; cooldown, otomatik hızlı retry yok |
| Kaynaklar arası kimlik | 306 aday, 0 skor çelişkisi, 0 çözümsüz takım; canonical auto-approval kapalı |
| Supabase migration | Yerel PostgreSQL motorunda uygulandı; 20 tablo |
| 100 TL limit, 1.000 TL başlangıç, idempotent stake | Yerel SQL testleri geçti; RPC üretime kapalı |
| Uzak Supabase import | Betik hazır, erişim yok; çalıştırılmadı |
| GitHub CI | Yapılandırma hazır; gerçek depoda çalıştırılmadı |
| Vercel panel / model / settlement | Sonraki aşamalar; yapılmış gibi sunulmadı |

Test raporu: **33 Python + 23 PostgreSQL kontrolü geçti.** PostgreSQL testleri PGlite üzerinde; gerçek Supabase RLS session'larını veya gerçek network concurrency'yi temsil ettiği iddia edilmiyor. Fixture'lar sentetik; gerçek toplama raporları ayrı.

## Aşama 2 — eğitim ve gerçek backend

Girdiler: mevcut repo ve Supabase projesi, güvenli sunucu bağlantısı, kaynak geçmiş kapsamı.

- Migration gerçek Supabase'e uygulanır; ayrı collector rolü oluşturulur; ilk import ve aynı import tekrarında satır artmama testi.
- Ortak quota reservation RPC: paralel worker toplamı sınırı aşamaz; reset zamanı UTC/provider billing cycle üzerinden doğrulanır.
- HTTP snapshot upload/ingestion transaction'ı ve distributed lease; çökme sonrası yeniden çalışma testi.
- 2+ geçmiş sezon güvenilir kapsam; train/validation/test kronolojik manifest. Test seti model geliştirmeden önce dondurulur.
- Elo, Poisson, Dixon-Coles için ayrı unit/integration testleri: güncelleme sırası, skor olasılık toplamı, tail mass, pozitif parametre/tau, optimizer başarısızlığı, bilinmeyen takım ve ertelenen maç.
- Her feature'ın maximum observed_at zamanı prediction cutoff'unu aşamaz. Aynı kickoff grubunda sonuçlar daha sonraki tahminlere sızamaz.
- Baseline raporları ve kalibrasyon analizi; hiçbir kârlılık iddiası yok. Odds yoksa sadece forecasting evaluation.

Çıkış: çalışan modeller, dataset manifestleri, test raporu, halen eksik veri ve anahtar listesi. Model geçmiyorsa paper motor devreye alınmaz.

## Aşama 3 — oran ve sanal işlem/sonuçlandırma

Girdiler: ücretsiz odds key, authenticated quota remaining/reset kanıtı, örtüşen lig/market, eligible champion.

- Odds adapter unit testleri: fractional/decimal kuralları, 1X2 ev/beraberlik/deplasman, stale/future timestamp, kota header maliyeti, eksik bookmaker.
- 7 günlük ücretsiz çağrı planı ve hard stop; ek market/region yanlışlıkla krediyi aşamaz.
- Strategy engine: edge, fractional Kelly, minimum/maximum tutar, integer kuruş yuvarlama, korelasyon/aynı maç limiti; veri yoksa NO_BET.
- `paper_bets` karar alanlarını koruyan trigger; izinli worker yalnız RPC çalıştırır.
- İki gerçek PostgreSQL bağlantısıyla 99 TL harcama sonrası iki eşzamanlı 1 TL talebinden sadece biri kabul; aynı idempotency key yarışında tek debit; payload değişiminde ret.
- İstanbul gün değişimi, pilot başlangıç/bitiş, wallet limit, postponed/cancelled/unknown durumlar, stale odds, kickoff değişimi, missing/future feature snapshots, gerçek/sentetik ayırımı.
- Settlement tek sefer; tekrar polling çift ödeme yapmaz. Lost=0 payout, won=kilitli oran × stake, void=stake dönüşü; günlük stake hakkı geri gelmez.
- Kaynak sonucu çelişirse settlement bekletilir. Düzeltmeler yeni correction hareketi; wallet=ledger toplamı invariant'ı.
- Worker crash/transaction rollback, DB outage, expired policy, frozen account ve manual kill switch testleri.

Çıkış: testleri geçmiş kapalı pilot. Sadece testler bitince başlangıç zamanı yazılır ve yedi günlük forward-test açılır.

## Aşama 4 — Vercel panel ve yedi günlük gözlem

- Mevcut Vercel projesine özel panel: bankroll, stake, open exposure, settled P/L, ROI ve örnek sayısı; veri gecikmesi/eksik günler görünür.
- Prediction table: model sürümü, 1X2 ve score grid, odds zamanı, lock zamanı ve neden NO_BET olduğu.
- Kaynak ekranı: izin/kota/freshness, quarantine, HTTP başarısızlıkları ve bağımsızlık belirsizliği.
- Model ekranı: champion/challenger, log loss/Brier/calibration ve gerçek ileri test ile retrospective test ayrımı.
- Sunucu sırları client bundle/repo/log'da yok; auth ve okuma RLS testleri; gerçek bahis entegrasyonu endpoint'i yok.
- 7 gün bitince yeni stake durur; sonuç bekleyen işlemler ayrı gösterilir. Rapor operasyonel dayanıklılık ve veri kalitesini değerlendirir; küçük örnekten kâr garantisi çıkarmaz.

## Aşama 5 — genişletme

StatsBomb tam lisans doğrulaması ve uygun kapsam sonrası xG; gerekçeli LightGBM/XGBoost challenger'ları; izinli dış tahmin arşivleri, zaman damgalı performans ve bağımsızlık testleri. Yeni kaynak yeterli veri ve şart doğrulaması olmadan model ağırlığı alamaz.
