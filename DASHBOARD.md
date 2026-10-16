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
