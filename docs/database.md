# Supabase veritabanı tasarımı

`001_lab.sql` tek transaction halinde ayrı `lab` şeması kurar. Para tam sayı kuruş, zaman `timestamptz`; günlük limit `Europe/Istanbul` takvim günüdür. Model/odds JSON alanları provenance alanlarının yerine geçmez.

| Tablo | Amaç / temel ilişki |
|---|---|
| sources | Lisans, izin, inceleme sonu ve kota politikası |
| raw_snapshots | Kaynak URL, edinim zamanı, SHA-256, payload, real/synthetic etiketi |
| ingestion_runs | Kaynak çalışması, durum, hata ve satır sayıları |
| source_observations | Snapshot'a bağlı immutable kaynak maç gözlemi |
| quarantine | Ayrıştırılamayan satır index'i, sebep ve çözüm |
| teams | Canonical takım; ülke/cinsiyet/kadro bağlamı |
| team_aliases | Kaynak takım ID + yarışma → canonical takım; inceleme kanıtı |
| matches | Canonical maç ve güncel operasyonel durum |
| match_aliases | Kaynak maç ID → canonical UUID; onay kanıtı |
| match_versions | Snapshot'a bağlı kickoff/durum/skor değişiklik geçmişi |
| model_versions | Kod/dataset hash, training cutoff, parametreler, champion/challenger |
| predictions | Maç/model, feature cutoff, 1X2 dağılımı, skor grid'i ve input snapshot listesi |
| odds_snapshots | Maç/kaynak/bookmaker/market/sonuç, decimal odds, kaynak ve edinim zamanları |
| external_predictions | Dış kaynak tahminleri, publish/observe zamanları ve upstream cluster |
| evaluation_runs | Kaynak veya modelin zaman bölmeleri ve ölçümleri |
| quota_usage | Kaynak/pencere başına tüketim ve üst sınır |
| paper_wallet | Tek çalışma cüzdanı, 100.000 kuruş başlangıç, pilot başlangıç/bitiş, kapatma anahtarı |
| paper_bets | Immutable karar referansları, kilitli oran, stake, İstanbul bütçe günü, durum |
| wallet_ledger | Append-only opening/stake/settlement/correction denetim hareketleri |
| settlements | Tek kuponun ilk sonuçlandırması, sonuç kanıtı, payout ve kural sürümü |

## Cüzdan işlem sınırı

`place_paper_bet` tek DB transaction'ında wallet satırını `FOR UPDATE` kilitler. Aynı cüzdana paralel istekler sıraya girer. Kilit alındıktan sonra sunucu saati okunur; client'ın budget_day göndermesi mümkün değildir. Önce aynı idempotency key'in orijinal payload'ı kontrol edilir. Aynı istek aynı bet ID'sini döndürür; farklı payload reddedilir.

Pilot açık ve 7 günlük pencere içindeyse; doğru maç/model/odds, kickoff güvenlik aralığı, oran tazeliği, approved kaynak, gerçek provenance ve feature cutoff kontrol edilir. Günün bütün stake'leri toplanır; 10.000 kuruş üstü reddedilir. Tek maç 1.000 kuruş, toplam açık risk 10.000 kuruş sınırı da uygulanır. Cüzdan düşümü, kupon ve ledger kaydı birlikte commit olur. Herhangi bir hata hepsini geri alır.

Günlük üst sınır **tüm paper_bets durumlarını** kapsar: void veya won stake'leri bütçeden düşmez. Bakiyenin artması günlük sınırı artırmaz. Pilot tekrar başlatılıp ikinci cüzdan yaratarak sınır bölünemez: wallet tek satırdır. Yeni deney reset'i gelecekte ayrı açık migration/onaylı lifecycle gerektirir.

## Yetki ve değişmezlik

Tüm tablolar RLS açık, tüm PUBLIC table/function/sequence yetkileri kapalıdır. Henüz authenticated dashboard read policy veya worker grant yoktur. Tarayıcıya hiçbir yazma yetkisi verilmez. Append-only trigger, snapshots/observations/versions/predictions/odds/external_predictions/ledger/settlements üzerinde UPDATE/DELETE reddeder.

Cüzdan, paper_bets ve model rolü ileride kontrollü RPC'lerle güncellenecektir. Normal runtime rollerine bu tablolarda doğrudan DML verilmemelidir. PostgreSQL sahibi/superuser trigger ve izinleri değiştirebilir; bu yönetici sınırı yazılımla ortadan kaldırılamaz. Migration sahibi runtime hesabı değildir. Hosted Supabase mevcut default grant/RLS davranışı entegrasyon testinde ayrıca denetlenmeli.

`paper_bets` güncellemesi settlement için gerekecek; stake/prediction/locked_odds alanlarını değişmez kılan özel mutation trigger ve settlement RPC Aşama 3'ün şartıdır. Bu aşamada tabloya runtime erişim zaten kapalıdır. Sonuç düzeltmesi mevcut ledger'ı değiştirmez; yeni correction ve reconciliation kaydı gerektirir. Sonuçlandırma motoru henüz uygulanmadı.

## Snapshot ve tekrar çalıştırma

Yerel SQLite ham HTTP byte'larını zlib ile saklar, hash bu orijinal byte'larındır. Tekrar aynı gövde tek blob olur; farklı edinim zamanları ayrı snapshot'tır. Kaynak gözlemi snapshot+source_match_id ile benzersizdir. En güncel görünüm geçmişi silmeden seçilir.

Opsiyonel importer, yerel snapshot ID'sinden UUIDv5 üretir; tekrar aktarımda `ON CONFLICT DO NOTHING` kullanır. PostgreSQL payload JSONB olduğundan boşluk/anahtar sırası korunmaz; SHA-256 orijinal HTTP byte'larına aittir, JSONB yeniden serileştirmesine değil. Byte-level arşiv ileride Storage nesnesiyle bağlanacaktır. İçe aktarım otomatik canonical maç onayı vermez.

Bozuk JSON gövdeleri şu an yalnız güvenli hata loguna gider; başarılı JSON snapshot'larında hatalı satırlar tam ham gövdeyle karantinaya bağlanır. Bütün başarısız cevapların byte-level arşivi ve distributed quota RPC sonraki aşama iyileştirmeleridir.

## Zaman sızıntısı ve açık kapılar

DB temel olasılık toplamı, kickoff öncesi oluşturulma ve stake anında snapshot cutoff'u doğrular. Eğitimin bütün feature dönüşümlerinin doğru olduğu yalnız SQL ile kanıtlanamaz; temporal dataset builder ve model testleri gerekir. Score grid'in boyut/normalize/kuyruk doğrulaması da model katmanında eklenecek. Mevcut migration bir tahmin modeli sağlamaz.

Yerel PGlite 23 kontrol geçti. Hosted PostgreSQL iki ayrı bağlantıyla yarış testi, uzak RLS/auth testi, importer replay testi ve cloud kota testi henüz yapılmadı; bunlar pilotu açmadan önce zorunlu.
