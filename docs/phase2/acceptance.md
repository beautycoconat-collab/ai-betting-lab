# Aşama 2 kabul durumu

| İstek | Kanıt | Durum |
|---|---|---|
| Mevcut kod/migration korunsun | phase1-preservation.json; 34 özgün dosyanın byte karşılaştırması | Geçti |
| Çok lig/sezon keşfi | discovery-live.json, discovery-summary.json: iki gerçek API kataloğu | Geçti |
| Çok sezon görev planlama | openfootball-plan.json, openliga-plan.json, planned-collection-status.json | Kod ve gerçek katalog planlaması çalışıyor; ek sezon HTTP işleri kota bekliyor |
| Tekrarların ayıklanması | normalize testleri; gerçek 2 çelişkili kaydın karantinası | Geçti |
| En az 20 kaynak incelemesi | sources.md ve source-research.json: 27 kaynak | Geçti; izin/kota bulunamayanlar açıkça kapalı |
| Çalışan adapterler | 7 adapter için test; 6 kaynakta gerçek yanıt normalizasyonu | FootballCSV canlı doğrulaması eksik |
| Merkezi registry/kuyruk/sağlık | engine/queue.py, registry, queue-status.json, retry/quota/lease testleri | Yerel SQLite üzerinde çalışıyor |
| Elo/Poisson/Dixon–Coles | model artifact'ları, yakınsama bilgileri, PMF testleri | Geçti |
| Gerçek görülmemiş maç tahmini | milli 2.034 ve Bundesliga 98 ayrı test maçı | Geçti; geriye dönük holdout |
| Sızıntı denetimi | fold hashleri/IDleri, tarih ayrımı, future label testleri | Geçti; tarihsel point-in-time arşiv kanıtı yok |
| Brier/log loss/referans | iki evaluation.json, results.md | Geçti |
| Skor kalibrasyonu | 10 sabit skor hücresi, en olası skor, 1X2 reliability/ECE | Tanılama çalışıyor; yeniden kalibrasyon eğitilmedi |
| Dış skor tahmini | ayrı ingest/table, izin ve sıfır ağırlık testleri | Gerçek dış tahmin 0; izinli kaynak olmadan toplanmadı |
| Yeni Supabase migration | 002_research_engine.sql, 28 yeni SQL kontrolü | Yerel doğrulandı; hosted Supabase entegrasyonu yok |
| Tekrarlanabilirlik | gerçek ham hash, fold hash, JSON artifact, sürümler, tekrar eğitim farkı 0 | Geçti; aynı ortam/sabit veri ile |
| Ücretsiz/sanal sınırlar | ücretli bağımlılık yok; Aşama 1 33 Python/23 SQL regresyonu | Geçti; gerçek para entegrasyonu yok |

Test verisi ayrımı: `test_adapters.py`, `test_models.py`, `test_queue.py` sentetik birim/sözleşme verisi kullanır. `test_real_artifacts.py` paketlenen gerçek arşivleri kontrol eder. Raporlanan model başarıları sentetik test verisinden üretilmedi. SQL dosyalarının test satırları yalnızca PGlite içindeki sentetik fixture'lardır; gerçek Supabase verisi gibi sunulmaz.

Bir sonraki aşamanın koşulları: kota zamanı gelen çok sezon işlerini kalıcı sayaçla tamamlamak; kulüp bazında daha uzun tarihsel holdout/walk-forward test yapmak; incelenmiş takım/lig alias haritasını genişletmek; Supabase proje bağlantısı, en az yetkili worker rolü ve hosted eşzamanlılık testlerini tamamlamak. Dış tahmin kaynağı için açık otomatik kullanım izni ve gerçek maç öncesi timestamp arşivi gerekir. Bunlar gerçekleşmeden üretim champion/kupon/pilot açılmaz.
