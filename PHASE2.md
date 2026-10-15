# AI Betting Lab — Aşama 2

Bu paket gerçek geçmiş maçlarla çalışan, sayısal skor tahmin motorunu içerir. Aşama 1 dosyaları değiştirilmedi. Vercel arayüzü, sanal kupon yürütme ve gerçek Supabase bağlantısı bu teslimatın çalışan modülleri arasında değildir. Gerçek para veya bahis hesabı entegrasyonu yoktur.

## Hızlı başlangıç — API anahtarı olmadan

Python 3.12 ile proje kökünde çalıştırın. Mevcut Aşama 1 `data/lab.sqlite` dosyanız varsa aynı dosyayı koruyun; silmeyin veya kotayı sıfırlamak için yeni veritabanı açmayın.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-phase2.txt
python -m unittest discover -s tests -v
python -m unittest discover -s tests_phase2 -v
python -m engine.bootstrap --db data/lab.sqlite
python -m engine status --db data/lab.sqlite
```

Windows PowerShell: aktivasyon komutu `.venv\Scripts\Activate.ps1` olur. Diğer Python komutları aynıdır. `pip install .` gerekmez; bütün komutları bu klasörden çalıştırın.

`bootstrap` ağ çağrısı yapmaz. Paketteki CC0 ham kanıtlarını SHA-256 ile kontrol edip yeniden ayrıştırır. İstek sayacını birleştirir; mevcut sayaçları silmez. Kaynakların hakları farklı olduğundan bütün geliştirme SQLite veritabanı ZIP'e konulmadı. Fjelstul ve TheSportsDB canlı çağrılarının sayısal sonuçları raporda, CC0 eğitim kaynaklarının ham yanıtları ise pakettedir. OpenLigaDB'nin Aşama 1 ham veritabanını elinizde tutuyorsanız yeni adapter ile ağsız işleyebilirsiniz:

```bash
python -m engine.import_phase1 --db data/lab.sqlite
```

## Gerçek verilerle tekrar eğitim

Milli maçlar için 2010–2019 eğitim, 2020–2021 doğrulama, 2022–2023 test kullanıldı. Hedef, kaynak tanımına göre **uzatma dahil, penaltı atışları hariç** final skorudur. Bu veri setini 90 dakika tahmini olarak kullanmayın.

```bash
python -m engine.evaluate --dataset reports/phase2/international/dataset.json --out reports/local-international
```

Bundesliga 2024/25 için ayrı **90 dakika** hedefi kullanıldı. Bu küçük veri seti uzun dönem başarı iddiası taşımaz.

```bash
python -m engine.evaluate --dataset reports/phase2/bundesliga/dataset.json --train-end 2025-01-01 --validation-end 2025-03-01 --test-end 2025-06-01 --out reports/local-bundesliga
```

İsterseniz paketlenen ham veriden yeniden kurulan SQLite üzerinden de aynı veri hazırlama hattını çalıştırın:

```bash
python -m engine.evaluate --db data/lab.sqlite --source international --out reports/local-from-db
python -m engine.evaluate --db data/lab.sqlite --source openfootball --competition de.1 --start 2024-01-01 --train-end 2025-01-01 --validation-end 2025-03-01 --test-end 2025-06-01 --out reports/local-club-from-db
```

## Kaydedilmiş modelden tek maç tahmini

```bash
python -m engine.predict --model reports/phase2/international/dixon_coles.model.json --fixture examples/phase2/international-fixture.json --out prediction.json
```

Örnek fikstür gerçek 18 Aralık 2022 Arjantin–Fransa maçıdır. Model 2019 sonunda eğitimini tamamlamıştır. Bu **bugün yeniden hesaplanan tarihsel holdout tahminidir**, 2022'de yayımlanmış bir tahmin değildir. Gerçek sonuç farklı `*-actual-result.json` dosyasındadır. Fikstüre sonuç alanı eklerseniz komut reddeder. Yeni fikstürde tarih, ev/deplasman takım adı, doğrulanmış nötr saha bilgisi ve aynı hedef tanımı zorunludur. Bilinmeyen takımlar ortalama parametreye döner ve çıktıdaki `unknown_teams` alanında görünür.

Çıktı 0–20 gol için 21×21 matris, bu matrisin dışındaki olasılık, 1X2 olasılıkları ve en olası beş skoru içerir. Sonsuz destekli dağılımın parametreleri de saklanır; 21+ gollü skorlar sıfır yapılmaz. Python'da `distribution.probability(h,a)` her negatif olmayan tam sayı skor için kullanılabilir.

## Çok sezonlu keşif ve görev kuyruğu

```bash
python -m engine enqueue --source openfootball --kind discover
python -m engine enqueue --source openliga --kind discover
python -m engine work --max-jobs 8
python -m engine status
python -m engine catalog --source openfootball
python -m engine plan --source openfootball --leagues de.1 eng.1 --seasons 2022-23 2023-24 2024-25
python -m engine plan --source openliga --leagues bl1 bl2 --seasons 2022 2023 2024
python -m engine work --max-jobs 8
```

`catalog` ve `plan` önce başarılı keşif snapshot'ı ister. Desteklenen sezon/ligler kaynak yanıtından alınır; varsayımsal lig listesi üretilmez. OpenLigaDB için bl1/bl2/bl3 ve açıkça futbol olarak etiketlenen ligler kabul edilir. Aynı kaynak/kind/parametre işi tekrar eklenirse ikinci HTTP çağrısı oluşturulmaz. Aynı URL için altı saat önbellek, kaynak başına saatte en fazla bir çağrı, 24 saatte dört ve 31 günde 124 çağrı iç limitleri korunur. FootballCSV, OpenFootball ile ortak kota kullanır.

**Canlı doğrulama:** 14 Ekim 2026 21:16 UTC civarında OpenLigaDB'den 680, OpenFootball'dan 270 lig-sezon katalog kaydı alındı. Gerçek kataloglardan seçilen 2022–2024 sezonları kuyruğa eklendi. Mevcut 2024/25 gerçek sezonu yeni iki adapter ile ağsız doğrulandı. Yeni sezonların indirmeleri sonraki saatlik kota penceresine ertelendi; bütün sezonlar indirilmiş değildir. FootballCSV adapteri sentetik testlidir; canlı CSV çağrısı doğrulanmadı. Geniş çok yıllı gerçek eğitim kanıtı milli maç arşivinden gelir. `work` zamanı geldiğinde yeniden çağrılabilir; sayaçları veya sistem saatini değiştirmeyin. `bootstrap` OpenFootball'un gerçek katalog snapshot'ını da ağsız yükler.

Öteki çalışan çağrılar:

```bash
python -m engine enqueue --source international
python -m engine enqueue --source fjelstul
python -m engine enqueue --source worldcup --season 2018
python -m engine enqueue --source thesportsdb --league 4328 --season 2024-2025
python -m engine work
```

Worker zamanı gelmemiş iş için bekleme döngüsüne girmez; çıkar. En fazla 20 görev inceler. Güncel izin inceleme son tarihi 13 Kasım 2026'dır; bu tarihten sonra kaynak incelemesi yenilenmeden ağ çağrıları durur. Bu tarih, sağlayıcının lisans süresi değil, iç yeniden inceleme kuralıdır. Yeni snapshot yenileme/günlük üretim zamanlayıcısı bu teslimatta etkin değildir; mevcut tamamlanmış iş aynı parametrelerle tekrar indirilmez.

## Testler ve veritabanı

```bash
python -m unittest discover -s tests -v
python -m unittest discover -s tests_phase2 -v
npm ci --prefix supabase/tests --ignore-scripts --no-audit --no-fund
node supabase/tests/validate.mjs
node supabase/tests/validate-phase2.mjs
```

`001_lab.sql` değişmedi. Yeni `002_research_engine.sql`, 9 araştırma tablosu, RLS, değiştirilemez kayıtlar ve lease tabanlı görev fonksiyonları ekler. Yerel PostgreSQL semantiği PGlite ile test edildi. Gerçek Supabase ağ bağlantısı, servis rolü yetkilendirmesi, hosted eşzamanlı oturumlar ve SQLite→Supabase aktarım worker'ı **doğrulanmış/uygulanmış değildir**. Yeni tablolara varsayılan PUBLIC erişimi verilmez. Migration'ı mevcut Supabase'e uygulamak ve gerekli sunucu rolünü tanımlamak ayrı entegrasyon adımıdır; hiçbir anahtar istemciye konulmaz.

GitHub Actions `phase2-tests.yml` yalnızca elle çalışır; `FREE_BUDGET_CONFIRMED=true` koşuluyla açılır. Zamanlanmış veri toplama yoktur. Paylaşılan kalıcı kota sayacı ve hesap ücretsiz bütçesi doğrulanmadan kısa ömürlü runner'larda otomatik ağ toplaması açılmamalıdır.

## Erişimler ve tamamlanmamış işler

Mevcut motor için API anahtarı, ücretli API/LLM/VPS/abonelik gerekmez. Supabase proje erişimi ve sunucu bağlantı bilgileri paylaşılmadığı için hosted entegrasyon yapılmadı. Football-Data.org, The Odds API ve API-Football gibi opsiyonel ücretsiz planlar için kullanıcıya ait anahtar/hesap ve ilgili koşul incelemesi eksik; bu kaynaklar kapalıdır.

Dış skor tahmini toplamak için ayrı, izin kontrollü saklama fonksiyonu vardır. Otomatik toplama izni doğrulanmış dış tahmin kaynağı bulunmadığından **gerçek dış tahmin sayısı 0, ensemble ağırlığı 0**. Geçmiş doğruluk ve kaynaklar arası korelasyon henüz ölçülemez. FootballCSV/OpenFootball ve WorldCup/OpenFootball ilişkisi bağımsız sinyal olarak sayılmaz. Kaynaklar arasında otomatik bulanık eşleştirme yapılmaz; `engine/identity.py` yalnızca incelenmiş alias haritasıyla birleştirir. Büyük, gerçek, elle doğrulanmış bir alias kataloğu henüz yoktur.

Kronolojik tek holdout ve kalibrasyon tanılamaları tamamlandı. Rolling/walk-forward çapraz doğrulama, olasılık yeniden kalibrasyonu, xG, LightGBM, XGBoost, üretim champion geçişi ve ensemble bu aşamada uygulanmadı. Skor olasılıkları kârlılık veya bahis avantajı kanıtı değildir. Aşama 1'in 1.000 TL sanal cüzdanı, 100 TL/gün sınırı, 7 günlük kapalı pilotu ve Balanced ayarları korunur.

## İçerik

- `engine/`: adapterler, registry kullanan kuyruk, normalizasyon, kimlik eşleştirme, veri hazırlama, modeller, değerlendirme, tahmin ve ayrı dış tahmin saklama.
- `config/source_registry_v2.json`: 27 kaynak, izin/kota/kapsam/kanıt/inceleme durumu.
- `docs/phase2/`: mimari, veri şeması, kaynak matrisi, model ve kabul raporları.
- `evidence/phase2/`: CC0 ham yanıtlar, özgün zaman ve SHA-256'ları, birleştirilecek kota geçmişi.
- `reports/phase2/`: gerçek toplama, eğitim/test/kalibrasyon, yeniden eğitim tekrarlanabilirliği, Python ve SQL sonuçları.
- `examples/phase2/`: gerçek holdout fikstürleri; tahminler ve gerçekleşen skorlar ayrı dosyalarda.
- `supabase/migrations/002_research_engine.sql`: yalnızca ek migration.
- `tests_phase2/`: sentetik birim/sözleşme testleri ve açıkça ayrı gerçek kanıt kabul testleri.

Başlangıç için `docs/phase2/results.md`, kaynak koşulları için `docs/phase2/sources.md` okunabilir. Paket SHA-256 dosya listesi `reports/phase2/package-manifest.json` içindedir.
