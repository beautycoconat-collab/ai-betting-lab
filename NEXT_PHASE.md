# Sonraki aşamalar ve açık kabul kapıları

## Aşama 0 sonrasında önce kapatılacak doğrulamalar

1. Disposable native PostgreSQL üzerinde iki bağımsız oturumun job claim yarışı ve 12 eşzamanlı sanal debit testi. Dosya: `tests_foundation/test_postgres_concurrency.py`. Teslimat ortamında çalıştırılamadı; atlanan testler başarı değildir.
2. Gerçek Supabase Auth/JWT, anon/authenticated/service rolü, worker login üyelikleri ve RLS entegrasyonu. PGlite sonuçları hosted başarı anlamına gelmez.
3. Üretim veri yükleme akışı: SQLite SHA-256 snapshot ID → Supabase UUID eşlemesi, kaynak politikaları ve geçmiş kota sayaçlarının tek yetkili depoya aktarımı. İki sayaçla aynı kaynağa paralel toplama yapılmamalı.
4. Worker yürütücülerinin süreç timeout'u, iş iptali ve üretim sağlık izleme. Şu anda lease/retry ve kalıcı görev protokolü vardır; gelecekteki bütün uzman yürütücüleri yoktur.
5. Hosted kullanım ölçümü ve retention/arşivleme worker'ı. Yerel boyut ve kaynak istek sınırları çalışır; bulut hesabının otomatik kullanım API bağlantısı yoktur.

## Yeni yol haritası

**Aşama 1 — çok kaynaklı veri ağı:** İzinli kaynak ve adapter sayısını artır; kalan sezon işlerini kota içinde bitir; doğrulanmış canonical kimlikleri ve upstream bağımlılık kanıtlarını genişlet. Yeni kaynak otomatik onaylanmaz. FootballCSV canlı doğrulaması eski teslimattan kalan iştir.

**Aşama 2 — gelişmiş matematik:** Mevcut Elo/Poisson/DC korunur. Gerçek xG/özellik verisi, walk-forward bölmeler, veri sızıntısı kapıları, validation ile kalibrasyon ve geçmişte doğrulanmış ensemble eklenir. Yarı piyasaları için ayrı veri/model gerekir. Sentez ve model belirsizlik aralıkları bu Aşama 0 teslimatında uygulanmadı.

**Aşama 3 — araştırma ve denetim:** Kadro/taktik araştırması, kaynaklı haber çıkarımı, gerçek Red Team kuralları, kanıtın futbol anlamını sınayan bilimsel hakem, test edilmiş senaryo katsayıları ve senaryo birleştirme. Yapısal kanıt kapısından geçen iddia otomatik gerçek kabul edilmez. Red Team katkısı aynı walk-forward bölmelerinde ablation ile ölçülür.

**Aşama 4 — oran ve sanal kupon:** İzinli gerçek oran adapteri, marj ve risk modeli, Balanced karar kuralları, resmî platform koşullarının doğrulanması. 50 TL kullanıcı varsayımı doğrulanmadan evrensel Nesine kuralı sayılmaz. Kombine/sistem/kolon/misli ve kazanma/kaybetme/ertelenme settlement motorları geliştirilir. Mevcut yeni fonksiyon yalnız kapalı tekli rezervasyon ve iptal iadesi temelidir.

**Aşama 5 — yedi günlük sanal pilot:** Yalnız test edilmiş champion, doğrulanmış prematch snapshot ve güncel gerçek oranla; panel, rapor, kaynak kesintisi ve bütçe alarmlarıyla. Gerçek para veya hesap girişi eklenmez.

**Aşama 6 — sürekli gelişim:** Champion/Challenger terfi kuralları, kaynak performansı, ablation, model kalibrasyonu ve sanal finansal ölçümler ayrı takip edilir. Champion promotion tablosu vardır; bu aşamada otomatik terfi yapan servis yoktur.

## Gerçek erişim eksikleri

Supabase proje bağlantısı/rol kurulumu verilmedi. GitHub ve Vercel'e deploy yapılmadı. Opsiyonel dış tahmin/oyuncu/xG/oran kaynakları için izin ve gerekiyorsa ücretsiz hesap anahtarları eksiktir. Mevcut yerel testler, demo ve Aşama 2 modelleri için anahtar gerekmez. Ücretli hizmet açılması hiçbir açık işin çözümü olarak varsayılmaz.
