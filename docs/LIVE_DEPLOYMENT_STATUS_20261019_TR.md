# AI Betting Lab — canlı otomasyon durumu (19 Ekim 2026)

**Gerçek Supabase projesi tespit edildi:** `oswpkwwbjwyktuqcakhr`.

ÖNEMLİ DÜZELTME: Önceki denetim yanlışlıkla `public` şemasına bakmış ve tablo bulamamıştı. Uygulamanın tabloları `lab` şemasındadır. Salt-okunur sorguyla 60'tan fazla `lab` tablosunun RLS açık olduğu görüldü. `anon` ve `authenticated` rollerinin `lab` şemasında `USAGE` ve kontrol edilen tablolarda `SELECT`/`INSERT` izinleri bulunmadı. Bunlar **yalnızca katalog kontrolleridir**, canlı JWT oturumuyla uçtan uca RLS testi değildir.

Mevcut iş akışı `schedule: 30 4 * * *` (UTC; Türkiye 07.30) içeriyor fakat **GitHub deposuna yüklenmedi**. GitHub App `contents:write` yetkisi 403 döndürüyor. Kod paketine eklenmesi canlıda çalıştığı anlamına gelmez.

## Henüz tamamlanmayanlar

1. GitHub deposuna yazma izni ve iş akışının varsayılan dalda yayınlanması (GitHub Actions cron varsayılan daldan çalışır).
2. Her koşuda korunan kalıcı kota/lease ve snapshot depolama; GitHub cache kalıcı veritabanı değildir. Mevcut workflow bunu güvenli biçimde bloke eder.
3. Gerçek Supabase JWT oturumuyla RLS, worker en az yetki, API şema erişimi ve yayına alma uçtan uca testleri.
4. Tahminlerin Supabase/Vercel'e gerçekten yazılması ve gösterilmesi. Mevcut workflow yalnızca artifact üretir, deploy etmez.
5. Sonuç toplama ve tahmin kilitleme zincirinin gerçek iş verisiyle uçtan uca çalıştırılması.

**Sonuç:** Canlı otomasyon henüz aktif değildir. Bu paket yalnızca hazırlanmış/güvenli biçimde engellenen kod ve yeni denetim içerir. Sanal portföy ve gerçek para işlemleri kapalıdır.
