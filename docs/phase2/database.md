# Ek Supabase tasarımı

`001_lab.sql` aynen korunur; `002_research_engine.sql` ona bağımlı ek migration'dır. Gerçek Supabase'e uygulanmış değildir. PGlite PostgreSQL semantiğini test eder; hosted Supabase Auth/PostgREST, rol eşleştirme ve eşzamanlı ağ oturumlarını test etmez.

| Yeni tablo | Amaç ve ilişkiler |
|---|---|
| source_catalog | Kaynak, lig, sezon, keşif zamanı; sources ve raw_snapshots FK |
| collection_jobs | Tekil dedupe_key, kaynak/kind/parametre, pending/running/done/failed/blocked, token ve lease |
| source_health | Kaynak bazında başarılı/hatalı çağrı sayıları ve son hata |
| normalization_runs | Ham snapshot ve parser SHA-256, kabul/karantina sayıları |
| research_results | Normalizasyon FK; kaynak maç ID, ayrı hedef tanımı, gerçek skorlar, nullable nötr saha |
| dataset_manifests | Veri hash'i, retrospective/point_in_time, kronolojik sınırlar ve maç listeli manifest |
| research_model_runs | Veri manifest FK, algoritma, kod/artifact hash'i, JSON parametreler, eğitim tarihi, ölçümler |
| research_score_predictions | Model FK, fixture ref, matematiksel oranlar, rho, grid+tail, 1X2; gerçek skor alanı yok |
| external_score_forecasts | Ayrı ham kaynak FK, gözlem/yayın/kickoff zamanları, seçim/olasılıklar; ağırlık zorunlu 0 |

Bütün yeni tablolarda RLS açık, PUBLIC erişimi kapalıdır. Katalog, normalizasyon, sonuç, dataset, model, tahmin ve dış tahmin kayıtları UPDATE/DELETE kabul etmez. Düzeltme yeni normalizasyon/model kaydıyla yapılır. İş kuyruğu ve sağlık sayaçları doğaları gereği güncellenebilir.

`claim_collection_job()` satır kilidi ve SKIP LOCKED ile işi alır. `complete_collection_job(id,token,status,error)` yalnızca güncel ve süresi geçmemiş lease'i bitirir. Çağrı yetkileri PUBLIC'ten alınmıştır; üretim worker rolü özel olarak tanımlanmalıdır. Mevcut tarayıcıya servis anahtarı verilmez.

Skor tahmini insert trigger'ı modeldeki gerçek eğitim tarihiyle bildirilen tarihi eşleştirir; eğitim tarihinden sonraki maç şartı vardır. 1X2 toplamı ve grid+tail toplamı 1 olmalıdır; negatif hücreler reddedilir. Bu kontrol JSON matrisin Poisson parametrelerinden hesaplandığını kendi başına yeniden ispatlamaz; matematiksel doğrulama Python model testlerindedir. Dış olasılık map'inin ayrıntılı şema kontrolü Python ingestion kapısındadır; doğrudan DB yazma yetkisi yalnızca güvenilir worker'a verilmelidir.

SQLite'ta ham snapshot, türetilmiş normalizasyon, rejected satırları ve job/health tabloları çalışır. Cached replay türetilmiş satırları yeniden kurar, değişmeyen ham hash ve parser hash'li audit run bırakır. Bu yerel replay işlemi Supabase'in append-only yeni normalizasyon yaklaşımından farklıdır. SQLite→Supabase import, production role grants ve point-in-time ingest henüz uygulanmadı; bu yüzden Supabase bağlantısı varmış gibi davranılmaz.

Sonraki kabul kapısı: mevcut projeye migration dry-run, en az iki bağımsız oturumla kota ve lease yarış testleri, server role için en az yetki, timestamp/ham hash roundtrip ve yedekten geri yükleme denemesi.
