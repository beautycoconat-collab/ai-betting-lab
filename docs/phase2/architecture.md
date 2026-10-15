# Aşama 2 mimarisi ve veri sözleşmeleri

Karar: Aşama 1'in `betting_lab/`, ilk migration, kaynak ayarları ve testleri değişmeden kalır. Yeni `engine/` kaynak kodundan Python 3.12 ile çalışır. Sayısal bağımlılıklar NumPy/SciPy'dir. Ne API anahtarı ne LLM kullanılır.

Akış: kaynak registry → izin/inceleme kapısı → kuyruk lease → kalıcı ortak kota rezervasyonu → HTTP → zaman damgalı ham snapshot → saf adapter → karantina/normalizasyon → kaynak ve hedef tanımı ayrılmış veri seti → kronolojik bölme → model eğitimi → doğrulamada seçim → dokunulmamış testte ölçüm. Ham veri başarıdan önce yazılır; bozuk JSON bile inceleme için saklanır. Sonuç dosyası ve tahmin dosyası birbirinden ayrıdır.

## Kaynak ekleme sözleşmesi

1. Resmî API/lisans/kota kaynaklarını ve izin inceleme tarihini registry'ye ekleyin. Belirsiz izin `approved` olmamalıdır.
2. `engine/adapters.py` içindeki `Adapter` protokolünü uygulayın: URL oluşturma, decode, catalog, rows, parse. Ağ çağrısı adapter içine yazılmaz.
3. `ADAPTERS` haritasına kaydedin. URL parçalarını allowlist regex ile doğrulayın. Yeni alanları tahmin etmeyin.
4. Çeşitli sürümler, boş/oynanmamış maç, bozuk alan, hatalı hedef/kapsam ve parser tekrarlarını test edin. Canlı testi sentetik testten ayrı raporlayın.
5. Aynı upstream'in aynaları için `quota_group` ve bağımlılık notu belirleyin. Kaynak sayısını model oy sayısı yapmayın.

`Result` sözleşmesi: source, native_id, competition, season, ISO match date, home/away names, iki nullable gol, score target, nullable neutral, optional UTC kickoff. Eksik nötr saha bilgisi mevcut eğitim hattından dışlanır. Gün düzeyindeki arşiv verisine hayalî kickoff saati eklenmez. `regulation90`, `final_including_extra_time` ve `provider_final_unknown` ayrı hedeflerdir.

## Tekrarlar ve kimlikler

Snapshot içindeki aynı native ID ve aynı içeriğin tekrarları bir kez sayılır. Çelişkili skor/alan varsa ilk kayıt dahil bütün çelişenler karantinaya girer. Veri hazırlama aynı kaynakta aynı gün/takımların çelişkilerini de dışlar. Tek kaynakla eğitim, farklı arşivlerin aynı maçı tekrar ağırlıklandırmasını engeller.

Kaynaklar arası birleştirme ayrı `identity.deduplicate` fonksiyonunda yalnızca incelenmiş `(source, competition, team name) → canonical ID` haritasıyla yapılır. Competition ID'leri de önceden uyumlu hale getirilmelidir. Bütün provenance kayıtları korunur. Bulanık ad benzerliği otomatik birleştirme yapmaz. Milli arşiv güncel ülke adlarını geçmişe uygulayabilir; bu sağlayıcı tercihi tarihsel takım sürekliliği açısından sınırlamadır.

## Çalıştırma güvenliği

SQLite gerçek worker depolamasıdır. Claim `BEGIN IMMEDIATE`, beş dakikalık lease ve token kullanır. Süresi geçen iş yeniden alınır; eski token yeni lease'i bitiremez. HTTP girişimi rezervasyondan sonra sayılır, başarısız istek de kotaya dahildir. Aşama 1'in aynı `requests`/`cooldowns` tabloları kullanılır. 401/403/429 en az 24 saat cooldown; daha uzun Retry-After korunur. Şema hatası kalıcı başarısızlık, geçici ağ hatası en çok üç denemedir. Tek kaynak hatası diğer kaynağın işini durdurmaz.

40 MB SQLite sınırı yeni HTTP isteğinden önce denetlenir; yanıt üst sınırı 2 MB'dir. Bu sınır disk üzerinde kesin 40 MB hard quota değildir: son kabul edilen yanıtın normalize edilmesi veritabanını büyütebilir, sonraki toplama durur. Arşiv genişletmesi ayrıca 10 MB ve 100 kat oran ile sınırlandırılır. Büyük yeni kaynaklar için kalıcı depolama bütçesi tasarlanmadan limitler artırılmamalıdır. Model değerlendirme JSON dosyaları bu SQLite kotasına dahil değildir; ZIP'te yaklaşık 100 MB açılmış rapor vardır.

İstek/snapshot zamanları gerçek gözlem zamanıdır. `bootstrap` bu tarihleri yeniden yazmaz ve paketlenen geçmiş istekleri mevcut sayaçla birleştirir. Kuyruk kodu token/durum koruması sağlar; SQLite dosyasına doğrudan yazma yetkisi olan yönetici için güvenlik sınırı değildir. Üretimde merkezi veritabanı rolleri ve erişim yönetimi gerekir.

## Model kaydı ve üretim sınırı

Model artifact JSON'dur; pickle çalıştırılmaz. Parametreler, eğitim bitişi ve skor hedefi kaydedilir. Rapor Python/NumPy/SciPy sürümlerini, kod hash'lerini, veri hash'lerini ve ayrık fold maç ID'lerini taşır. Validation seçimi yalnızca araştırma champion adayıdır; Aşama 1'in üretim model rolü veya kuponları otomatik değiştirilmez. Artifact kaynağına güvenilmiyorsa dağıtım öncesi paket hash'leri doğrulanmalıdır.
