# Vercel dashboard — 2026-10-16

## Çalıştırma

```sh
python -m pip install -r requirements-cloud.txt
python -m dashboard.export
node --check public/app.js
node scripts/check_dashboard.mjs
python -m unittest discover -s tests_dashboard -v
# Yerel statik kullanım (API yoksa aynı public JSON'a güvenli fallback):
python -m http.server 8000 --directory public
```

Vercel proje kökü depo köküdür. Framework preset: Other; output: `public`;
build: `node scripts/check_dashboard.mjs`. `vercel.json` salt okunur
`api/dashboard.py` fonksiyonunu paketler. Mevcut Vercel projesine deploy
bu oturumda yapılmadı; canlı URL veya Vercel build başarısı iddia edilmiyor.
Yeni servis/abonelik gerekmez. API için hiçbir secret gerekmez.

## Gerçek veri hattı

`reports/phase2/bundesliga/dataset.json` + kayıtlı baseline/Elo/Poisson/DC
modelleri → `dashboard.export` → `public/data/dashboard.json` →
`GET /api/dashboard?date=YYYY-MM-DD` → mobil arayüz.
`GET /api/dashboard?fixture=<id>` tek maç detayını döndürür.
Statik dağıtımda API yoksa UI aynı yayımlanmış JSON'u okur.
Araştırma/ML hesaplaması Vercel isteklerinde çalıştırılmaz.

18 gerçek tarihsel maç için modeller mevcut `engine.predict.predict` ile
tekrar çalıştırılır. Eğitim bitişi maçtan öncedir; model ve veri SHA-256
kanıtları dosyada tutulur. Bunlar 2026'da yeniden hesaplanan 2025 maçlarıdır,
maç öncesinde kaydedilmiş tahminler değildir. Gerçek sonuç ayrı alandadır.
Piyasa dönüşümleri mevcut `MarketSpecialist` kullanır; yarı modeli yoksa
`insufficient_data`. Piyasalar açıkça Poisson'a etiketlidir. Model seçimi
skor/1X2 alanını değiştirir; piyasaların modelini değiştirmez.

`--database /absolute/runtime.sqlite` mevcut SQLite'ı `mode=ro` açar,
yalnız sınırlı fikstür kimlik alanlarını projekte eder. Doğrulanmamış runtime
fikstürü bugünün yayımlanmış maçı sayılmaz. Audit gövdeleri, görev girdileri,
serbest metin kanıtlar, anahtarlar veya cüzdan kopyalanmaz.

## Durum ve açık bağlantılar

- FULL (yerel sayısal kabul): arşiv modelleri → public projection → API sorguları.
- PARTIAL: mobil dashboard kodu, tarih/arama, maç dosyası, model değiştirme,
  skor/1X2/gol piyasaları, tarihsel Log Loss ve kalibrasyon SVG grafikleri.
  Tarayıcı görsel/etkileşim QA yapılmadı: managed preview için gerekli
  control-browser becerisi mevcut değil; alternatif preview başlatılmadı.
- PARTIAL: 14 rol ve maça özel kayıt alanları. Yürütme kaydı yoksa açıkça
  "kayıt yok" gösterilir; otomatik çalışmış veya onaylamış sayılmaz.
- BLOCKED: güncel doğrulanmış günlük fikstür ve tahmin yayın hattı;
  hosted Auth/JWT/RLS ile uzman/denetim/portföy okuma entegrasyonu.
- BLOCKED: canlı bakiye/ROI/drawdown/CLV ve ileriye dönük 7/30/90/180 gün
  grafikleri. Gerçek defter/fiyat olmadan grafik veya bakiye uydurulmaz.
- BLOCKED: Vercel dağıtım kabulü; mevcut Vercel proje erişimi bu turda yok.

`public/` içeriği açık yayımlanmak üzere hazırlanmıştır; özel kayıt veya
credential eklemeyin. CSP harici script/bağlantıyı engeller; sayısal bar
uzunlukları için yalnız style attribute'a izin verilir. API yalnız GET
sağlar; hiçbir tahmin/cüzdan yazma veya pilot etkinleştirme yolu yoktur.
001–005 migration'ları, hosted veritabanı ve main dalı değiştirilmez.

Sonraki adım: gerçek günlük fikstür/tahmin için kanıtlı, sürümlü yayın
sözleşmesi; read-only hosted projection ve JWT kabulü; ardından Vercel
preview deploy onayı ve mobil/tarayıcı kabulü. Sahte veriyle boşluk doldurulmaz.

## Worker köprüsü — 2026-10-19

Kalıcı `ResearchWorkerPipeline` model çıktısı artık sınırlı skor özeti, model
sürümleri ve ensemble piyasa dönüşümlerini içerir. Büyük grid ve ham haberler
worker display alanına kopyalanmaz. Eski çıktılar geriye dönük değiştirilmez.
Yeni `dashboard/contracts.py` sürüm/olasılık/top-skor sözleşmesini doğrular.

```sh
python -m dashboard.export --database /absolute/research.sqlite --include-research
node scripts/test_dashboard_ui.mjs
```

`--include-research` bilinçli public projeksiyon seçimidir; varsayılan kapalıdır.
`dashboard/research_feed.py` dört gerçek task output kaydını, DAG kenarlarını,
sabit girdileri, fixture/cutoff ve model sürümünü karşılaştırır. Okuma `mode=ro`.
Uyumsuz kayıt karantinaya ayrılır; hata metni veya ham input yayına konmaz.
Yalnız dört yürütülen rol `done` olur; diğer 10 rol için başarı uydurulmaz.

Panelde ayrı **Worker analizleri** sekmesi bulunur. Her kayıt `recorded_research`
ve `local_record_unverified` etiketlidir. Bunlar günün doğrulanmış maçları,
maç öncesi kilitli tahminler, canlı başarı veya portföy kararları sayılmaz.
Red Team kanıt kimlikleri/isteği ve hakem tur/risk kararı gösterilir. Eski worker
çıktısında skor özeti yoksa yeni dağılım uydurulmaz. Varsayılan public JSON'a
sentetik worker verisi eklenmedi. Günlük tarih seçimi API'ye tarih parametresi
ile gider. Hosted bağlantı, browser/mobile QA ve Vercel deploy hâlâ BLOCKED.

Yeni köprü entegrasyon testleri sentetik kanıt + gerçek arşiv modelleri kullanır;
canlı kaynak başarı iddiası değildir. Node testleri HTML üretim/olay akışı smoke
kontrolüdür, gerçek tarayıcı layout testi değildir. Pilot kapalı kalır.


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


Kaynak atfı: OpenLigaDB contributors, ODbL 1.0. Resmî izin ve API bilgileri: https://beta.openligadb.de/Privacy ve https://api.openligadb.de/index.html . `public/data/openliga-2026-bl1.json` gerçek ham snapshot; SHA-256 projection içindeki snapshot hash ile doğrulanabilir. Logo hakları aktarılmaz.

## Vercel dashboard yayın kabulü — 2026-10-19

**Dashboard yayında:** https://ai-betting-lab.vercel.app/ . Kullanıcının üretim dağıtımı için devam onayından sonra `6yD5cZV4npcW6Epat3uThRnvRTm4` READY oldu. Vercel proje ID: `prj_5bVfIsnlr2SKOurNjyUlgczkFxDc`; takım `beautycoconat-8169s-projects`. Vercel Drop ile 40 kaynak dosyası yüklendi; GitHub otomatik bağlantısı kurulmadı. Paket GitHub `a580320` sürümünün runtime dosyalarını ve doğrulanmış JSON'unu içerir. Paket SHA-256: `0dbc62f601b796fc26f7b2926c78da7898b4363aee6facc23e8f9beeae23d3b3`.

Gerçek hosted HTTP kabulü: 19/23/24/25 Ekim sorguları 200 ve sırasıyla 0/1/6/2 maç; hatalı tarih 400, olmayan fixture 404. Statik JSON yerel kaynak dosyasıyla byte-byte eşit. Detay API iki koşullu senaryoyu aynen döndürüyor, tüm model 1X2 kütleleri geçerli. API `no-store`; yürütme false. Kanıt: `reports/experts/vercel_http_20261019.json`.

Tarayıcıda gerçek uygulama açıldı: 23 Ekim seçimi → Stuttgart/Mönchengladbach kartı → saha senaryosu → ensemble olasılıkları/skorlar/piyasalar → Poisson model değişimi → gerçek Red Team/Hakem needs_reanalysis ve abstain/skip kararları. 14 rolün eksik veri/blocked durumları görünür. Bu gerçek masaüstü tarayıcı kabulüdür; mobil cihaz kabulü yapılmadı. Tarayıcı logundaki görülen hatalar Chrome uzantısına ait, uygulama hatası olarak sayılmadı.

**Açık sınırlar:** Yayın, işçinin oluşturduğu doğrulanmış kaynak snapshot'ını okuyor. Vercel hosted DB credential bağlantısı ve JWT/RLS kabulü tamamlanmadı; Supabase canlı okuması etkin değil. Sürekli günlük veri/yeniden yayın otomasyonu etkin değil. Kaynak snapshot'ı 24 saati geçince güncel fikstür gösterimi güvenle kapanır; ertesi gün kendiliğinden yenilenmiş gibi sunulmaz. Diğer ligler, dört eşleşmeyen maç için tahmin, gerçek oran/CLV/ROI ve tüm 14 rolün canlı araştırması tamamlanmadı. Pilot, portföy ve cron kapalı; migration veya yetki değişikliği yok.

Sıradaki iş: yalnız bu repoya Git bağlantısı veya kontrollü artifact dağıtım hattı; kota durumunu koruyarak günlük yenileme; hosted en az yetki/JWT kabulü; güncel sezon eğitim kapsamı ve kesin saha kanıtı. Üretim dashboard yayını bu güvenlik kapılarının geçtiği anlamına gelmez.

