# Ücretsiz dağıtım ve saklama planı

Bu teslimat hesaplara deployment yapmaz. Yerel Python ve PGlite ile çalışır; ücretli bir bağımlılık yoktur. Pydantic/NumPy/SciPy ücretsizdir. Gerçek Supabase erişimi, worker login rolleri ve Auth politikaları henüz doğrulanmadı.

## Bugün çalıştırılabilecek yol

Model eğitimi, ham arşivler ve büyük artifact'lar yerel makinede kalır. Kaynak toplama aynı kalıcı SQLite dosyasıyla yapılır; yeni dosya açarak sayaç sıfırlanmaz. `foundation.Runtime`, mevcut `engine.Queue` ve Store'u kullanır. SQLite dosya büyüklüğü 40 MB iç sınırını aşarsa yeni Foundation yazma işlemi ve kaynak HTTP rezervasyonu durur. Son yazma sınırı aşırabilir; bu sert dosya sistemi kotası değildir.

Supabase için `lab` şemasında metadata, normalize kayıt, mesaj, karar, ledger ve hash saklanması planlanır. Ham HTML/ZIP ve model dosyaları buraya gömülmez. `003` yeni raw_snapshots.payload kayıtlarını 64 KiB ile sınırlar. Kaynak URI, hash, zaman ve izin bilgisi SQL'de tutulur; büyük içerik yerel/arşiv depoda kalır. Mevcut bucket kullanılırsa ayrıca saklama ve trafik bütçesi hesaplanmalıdır.

## Hesap sınırları — resmî kaynaklar kontrol edildi

15 Ekim 2026 Türkiye tarihiyle kontrol edilen resmî sayfalar:

- [Supabase fiyatlandırma](https://supabase.com/pricing): Free için proje başına 500 MB veritabanı, 1 GB dosya depolama, 5 GB egress ve iki aktif proje sınırı listelenir. Hareketsiz Free proje bir hafta sonra duraklatılabilir. Hesaptaki diğer uygulamaların kullanımı da bütçeye dahildir.
- [Vercel Cron kullanım sınırları](https://vercel.com/docs/cron-jobs/usage-and-pricing): Hobby cron görevi günde bir kez sınırındadır. Dakikalık/saatlik canlı worker burada varsayılmaz. İleride Vercel yalnız hafif panel/okuma uçları için değerlendirilebilir.
- [GitHub Actions faturalandırması](https://docs.github.com/billing/managing-billing-for-github-actions/about-billing-for-github-actions): özel depolarda ücretsiz dakika ve saklama hesabın planına bağlıdır; dahil miktarı aşan kullanım ücretlenebilir. Bu nedenle yeni workflow yalnız elle ve `FREE_BUDGET_CONFIRMED=true` ile çalışır. Hesap harcama limiti sıfıra ayarlanıp kontrol edilmeden açılmaz.

Planlar değişebilir; bu sayılar sisteme sınırsız ücretsiz kullanım hakkı vermez. Hiçbir görev ücretli plana otomatik geçmez. Sağlayıcı kullanım verisi bilinmiyorsa planlanmış uzak toplama kapalı kalmalıdır. Bu teslimatta sağlayıcı hesap faturası/usage API'sini otomatik okuyan servis yoktur.

## Supabase kurulumu için koşullar

1. Mevcut veritabanını yedekleyin ve şema envanterini alın. `lab` zaten Aşama 2 ise yalnız `003` uygulayın; yeni boş projede 001→002→003 sırasını kullanın.
2. Migration içindeki NOLOGIN grup rolleri için rol oluşturma yetkisini doğrulayın. Mevcut yetkilerle başarısız olursa korumaları kaldırmayın; proje yöneticisinin rol kurulumu gerekir.
3. Her sunucu worker'ına yalnız ihtiyaç duyduğu `lab_<role>` üyeliğini verin. Tarayıcıya service role/DB şifresi koymayın. lab şemasını PostgREST'e varsayılan olarak açmayın.
4. Aynı kullanıcı için frontend Auth/RLS entegrasyonunu ve farklı kullanıcıların izolasyonunu ayrı test edin. `lab_dashboard` tek proje çıktısı için salt okunur gruptur; çok kiracılı Auth tasarımı değildir.
5. SQLite→PostgreSQL kaynak ID ve kota geçmişi aktarımını doğrulayın. İki bağımsız sayaçla aynı kaynağı toplamayın. Otomatik aktarım worker'ı bu aşamada yoktur.
6. Gerçek bağımsız PostgreSQL oturum testlerini disposable test veritabanında çalıştırın; sonra hosted ortamda Auth/JWT testleri yapın.

Yerel rol tanımı tek başına bulut bağlantısı kurmaz. İlk pilot ve kupon kuralları kapalıdır; bu dosyadaki adımlar pilotu otomatik açmaz.

## Saklama politikaları

| Sınıf | Konum | Tasarlanan süre | İç bütçe |
|---|---|---:|---:|
| Ham arşiv/yanıt | Yerel veya mevcut uygun depolama | 30 gün sıcak, sonra hash ile arşiv | 2 MB HTTP yanıtı, 40 MB yerel DB |
| Normalize veri | SQL metadata/normalize tablolar | 730 gün | 100 MB yumuşak pay |
| Model artifact | Yerel veya mevcut uygun depolama | 730 gün, kullanılan sürümler daha uzun | Dosya başına 20 MB, toplam 100 MB iç pay |
| Denetim/ledger/mesaj | SQL + ayrı integrity export | 2.555 gün tasarım hedefi | 50 MB yumuşak pay; mesaj 16 KiB |

Süreler sağlayıcı garantisi veya mevcut otomatik silme işi değildir. Arşivlenmemiş veri silinmez. Tahminde kullanılmış model/kanıt ve finansal ledger bağımlılıkları çözülmeden retention uygulanmaz. Append-only tabloları normal worker silemez. DB yöneticisi gözetiminde arşivleme ve kotalı bakım işi sonraki aşamada geliştirilecektir.

Üretime geçmeden toplam veritabanı büyüklüğü `select pg_database_size(current_database());` ile ölçülmeli, örneğin 350 MB uyarı/400 MB yeni iş durdurma eşiği mevcut hesabın diğer kullanımlarıyla birlikte seçilmelidir. Bu değerler önerilen çalışma eşikleridir; hosted ölçüm bağlantısı henüz kurulmadığı için otomatik hesap kotası denetimi tamamlandı diye raporlanmaz.
