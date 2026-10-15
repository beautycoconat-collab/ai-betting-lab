# 14 uzman rol — görev, sözleşme ve yetki kaydı

Bu kayıt hedef mimariyi tanımlar. 14 rol, 14 LLM veya 14 tamamlanmış araştırma servisi değildir. Her rol Python/deterministik iş akışıyla yürütülebilir. LLM zorunlu değildir. Uygulama durumu her rolün altında belirtilmiştir.

## 01. Baş Koordinatör — Motor A

Kimlik: `coordinator`. PostgreSQL grup rolü: `lab_coordinator` (NOLOGIN).

Girdi: Fikstür kapsamı, bütçe, kaynak sağlığı, iş bağımlılıkları.

Çıktı: Kalıcı işler, öncelik planı, hata/erteleme durumu.

Yetki sınırı: İş planlamak ve durdurmak; olasılıkları değiştiremez.

Aşama 0 durumu: Kalıcı DAG kuyruğu ve lease/retry temeli.

## 02. Kaynak Avcısı — Motor A

Kimlik: `source_hunter`. PostgreSQL grup rolü: `lab_source_hunter` (NOLOGIN).

Girdi: Kaynak registry, lisans, kota, kategori ve lig kapsamı.

Çıktı: Kaynak politikası, katalog, ham snapshot, erişim raporu.

Yetki sınırı: Yalnız izinli kaynağa kota rezervasyonundan sonra erişmek.

Aşama 0 durumu: Mevcut engine.Queue ve adapterler yeniden kullanılır.

## 03. Veri Doğrulayıcı — Motor A

Kimlik: `data_validator`. PostgreSQL grup rolü: `lab_data_validator` (NOLOGIN).

Girdi: Ham snapshot, kimlik haritası, hedef ve zamanlar.

Çıktı: Verified/unknown/conflicting/unverified kanıt ve karantina.

Yetki sınırı: Kanıt kaydetmek ve doğrulama talep etmek; çelişkiyi uydurarak çözemez.

Aşama 0 durumu: Provenance, hedef ve kimlik kontrolleri; kanıt kayıt RPC.

## 04. Kadro ve Taktik Araştırmacısı — Motor A

Kimlik: `lineup_researcher`. PostgreSQL grup rolü: `lab_lineup_researcher` (NOLOGIN).

Girdi: İzinli kadro/sakatlık/hava/teknik direktör haberleri.

Çıktı: Kaynak referanslı yapılandırılmış kanıt, senaryo isteği.

Yetki sınırı: Kanıt sunmak; gol beklentisi veya oyuncu etkisi belirleyemez.

Aşama 0 durumu: Yalnız rol ve mesaj sözleşmesi; haber araştırması geliştirilmedi.

## 05. Dış Tahmin Araştırmacısı — Motor A

Kimlik: `external_researcher`. PostgreSQL grup rolü: `lab_external_researcher` (NOLOGIN).

Girdi: İzinli dış tahmin, yayın/gözlem zamanı, upstream.

Çıktı: Ayrı dış tahmin kayıtları ve geçmiş performans isteği.

Yetki sınırı: Dış tahmini etiketlemek; bağımsızlık/başarı kanıtlanmadan ağırlık veremez.

Aşama 0 durumu: Mevcut ayrı ingestion korunur; izinli gerçek dış tahmin yok.

## 06. Takım Gücü Analisti — Motor B

Kimlik: `team_strength`. PostgreSQL grup rolü: `lab_team_strength` (NOLOGIN).

Girdi: Zaman sıralı maçlar, rakip/saha, veri yeterliliği.

Çıktı: Elo ve hücum/savunma özellikleri, yeterlilik raporu.

Yetki sınırı: Test edilmiş sayısal algoritma çalıştırmak; gelecek verisini alamaz.

Aşama 0 durumu: Mevcut modeller kullanılır; yeni xG/takvim modeli geliştirilmedi.

## 07. Skor Simülasyon Motoru — Motor B

Kimlik: `score_engine`. PostgreSQL grup rolü: `lab_score_engine` (NOLOGIN).

Girdi: Model sürümü, feature snapshot, fixture, hedef.

Çıktı: Tam skor PMF, kuyruk kütlesi, 1X2, ayrı tahmin revizyonu.

Yetki sınırı: Sayısal model çalıştırmak ve append-only tahmin kaydetmek.

Aşama 0 durumu: Mevcut Elo/Poisson/DC çağrılır; revizyon köprüsü ve kayıt RPC.

## 08. Özel Bahis Piyasaları Uzmanı — Motor B

Kimlik: `market_specialist`. PostgreSQL grup rolü: `lab_market_specialist` (NOLOGIN).

Girdi: Desteklenen skor modeli, piyasa ve gerekli yarı verisi.

Çıktı: Piyasa olasılığı veya unsupported/insufficient_data.

Yetki sınırı: Yalnız doğrulanmış matematiksel dönüşüm; yarı verisini uyduramaz.

Aşama 0 durumu: Rol/sözleşme; yeni yarı ve handikap modeli yok.

## 09. Tahmin Sentezleyici — Motor B

Kimlik: `synthesizer`. PostgreSQL grup rolü: `lab_synthesizer` (NOLOGIN).

Girdi: Bağımsız model çıktıları, kalibrasyon, bağımlılık, senaryolar.

Çıktı: Sentez dağılımı, belirsizlik ve yöntem sürümü.

Yetki sınırı: Yalnız geçmiş veride doğrulanmış ağırlıklar; çoğunluk oyu yok.

Aşama 0 durumu: Yalnız sözleşme; ensemble ağırlıkları öğrenilmedi.

## 10. Red Team — Şeytanın Avukatı — Motor C

Kimlik: `red_team`. PostgreSQL grup rolü: `lab_red_team` (NOLOGIN).

Girdi: Tahmin, kaynaklar, kadro, veri yeterliliği ve bağımlılıklar.

Çıktı: Kanıtlı finding ve yeniden analiz isteği.

Yetki sınırı: Sorun sınıflandırmak; numeric_override her zaman null.

Aşama 0 durumu: Yapılandırılmış itiraz kabulü; otomatik futbol eleştirisi yok.

## 11. Bilimsel Hakem — Motor C

Kimlik: `scientific_referee`. PostgreSQL grup rolü: `lab_scientific_referee` (NOLOGIN).

Girdi: Finding, kanıt, model ve zaman bilgileri.

Çıktı: approved/needs_reanalysis/insufficient_evidence/rejected/abstain kararı.

Yetki sınırı: En çok iki inceleme; çözülmeyen durumda skip; olasılık değiştiremez.

Aşama 0 durumu: Deterministik iki turlu kanıt kapısı; bilimsel etki ölçümü gelecekte.

## 12. Oran Analisti — Motor D

Kimlik: `odds_analyst`. PostgreSQL grup rolü: `lab_odds_analyst` (NOLOGIN).

Girdi: Gerçek oran snapshot, sağlayıcı, piyasa, zaman.

Çıktı: Marj, ima edilen olasılık, avantaj ve geçerlilik raporu.

Yetki sınırı: Oranı denetlemek; gerçek oran yoksa getiri üretmez.

Aşama 0 durumu: Mevcut odds şeması korunur; yeni toplama/avantaj motoru yok.

## 13. Risk Yöneticisi — Motor D

Kimlik: `risk_manager`. PostgreSQL grup rolü: `lab_risk_manager` (NOLOGIN).

Girdi: Hakem kararı, oran, belirsizlik, cüzdan, açık risk, platform kuralı.

Çıktı: bet/wait/skip, azami risk bütçesi, sanal kupon isteği.

Yetki sınırı: Sanal limitleri uygulamak; kaybı telafi için miktar büyütemez.

Aşama 0 durumu: Paylaşılan bütçe koruması, kupon şeması, yalnız void settlement.

## 14. Sonuç ve Öğrenme Denetçisi — Motor D

Kimlik: `learning_auditor`. PostgreSQL grup rolü: `lab_learning_auditor` (NOLOGIN).

Girdi: Zaman sıralı sonuçlar, tahminler, sanal işlemler, deneyler.

Çıktı: Kalibrasyon/ablation/performance raporları, terfi önerisi.

Yetki sınırı: Kanıta dayalı terfi önermek; her maç sonrası keyfî model değişimi yok.

Aşama 0 durumu: Mevcut değerlendirme korunur; terfi/ablation kayıt temeli.

## Ortak kurallar

Her çalıştırma ayrı agent_run_id ile kaydedilir. Sözleşmeler schema_version=1.0 kullanır. Kaynak, kanıt, model, fixture ve zaman ilişkileri ayrıca doğrulanır. Red Team ve Hakem numeric_override=null dışında değer veremez. Görev lease ve retry kayıtları kalıcıdır. Normal roller kritik tablolara doğrudan yazamaz; izinli RPC kullanır. Yerel SQLite dosyasına erişimi olan Python süreci güvenilir işçi kabul edilir; SQLite ağ kimlik doğrulama katmanı değildir.

Rol katkısı ileride aynı walk-forward bölmelerinde ablation ile ölçülür. Şu anda yeni rollerin futbol tahmin başarısını artırdığına dair deney yapılmadı.
