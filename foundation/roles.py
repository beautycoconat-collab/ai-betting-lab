"""Role registry describes the target architecture, not fourteen implemented agents."""
from .contracts import Role

# (Turkish name, engine, inputs, outputs, allowed action, current implementation)
SPEC = {
 'coordinator':('Baş Koordinatör','A','Fikstür kapsamı, bütçe, kaynak sağlığı, iş bağımlılıkları','Kalıcı işler, öncelik planı, hata/erteleme durumu','İş planlamak ve durdurmak; olasılıkları değiştiremez','Kalıcı DAG kuyruğu ve lease/retry temeli'),
 'source_hunter':('Kaynak Avcısı','A','Kaynak registry, lisans, kota, kategori ve lig kapsamı','Kaynak politikası, katalog, ham snapshot, erişim raporu','Yalnız izinli kaynağa kota rezervasyonundan sonra erişmek','Mevcut engine.Queue ve adapterler yeniden kullanılır'),
 'data_validator':('Veri Doğrulayıcı','A','Ham snapshot, kimlik haritası, hedef ve zamanlar','Verified/unknown/conflicting/unverified kanıt ve karantina','Kanıt kaydetmek ve doğrulama talep etmek; çelişkiyi uydurarak çözemez','Provenance, hedef ve kimlik kontrolleri; kanıt kayıt RPC'),
 'lineup_researcher':('Kadro ve Taktik Araştırmacısı','A','İzinli kadro/sakatlık/hava/teknik direktör haberleri','Kaynak referanslı yapılandırılmış kanıt, senaryo isteği','Kanıt sunmak; gol beklentisi veya oyuncu etkisi belirleyemez','Yalnız rol ve mesaj sözleşmesi; haber araştırması geliştirilmedi'),
 'external_researcher':('Dış Tahmin Araştırmacısı','A','İzinli dış tahmin, yayın/gözlem zamanı, upstream','Ayrı dış tahmin kayıtları ve geçmiş performans isteği','Dış tahmini etiketlemek; bağımsızlık/başarı kanıtlanmadan ağırlık veremez','Mevcut ayrı ingestion korunur; izinli gerçek dış tahmin yok'),
 'team_strength':('Takım Gücü Analisti','B','Zaman sıralı maçlar, rakip/saha, veri yeterliliği','Elo ve hücum/savunma özellikleri, yeterlilik raporu','Test edilmiş sayısal algoritma çalıştırmak; gelecek verisini alamaz','Mevcut modeller kullanılır; yeni xG/takvim modeli geliştirilmedi'),
 'score_engine':('Skor Simülasyon Motoru','B','Model sürümü, feature snapshot, fixture, hedef','Tam skor PMF, kuyruk kütlesi, 1X2, ayrı tahmin revizyonu','Sayısal model çalıştırmak ve append-only tahmin kaydetmek','Mevcut Elo/Poisson/DC çağrılır; revizyon köprüsü ve kayıt RPC'),
 'market_specialist':('Özel Bahis Piyasaları Uzmanı','B','Desteklenen skor modeli, piyasa ve gerekli yarı verisi','Piyasa olasılığı veya unsupported/insufficient_data','Yalnız doğrulanmış matematiksel dönüşüm; yarı verisini uyduramaz','Rol/sözleşme; yeni yarı ve handikap modeli yok'),
 'synthesizer':('Tahmin Sentezleyici','B','Bağımsız model çıktıları, kalibrasyon, bağımlılık, senaryolar','Sentez dağılımı, belirsizlik ve yöntem sürümü','Yalnız geçmiş veride doğrulanmış ağırlıklar; çoğunluk oyu yok','Yalnız sözleşme; ensemble ağırlıkları öğrenilmedi'),
 'red_team':('Red Team — Şeytanın Avukatı','C','Tahmin, kaynaklar, kadro, veri yeterliliği ve bağımlılıklar','Kanıtlı finding ve yeniden analiz isteği','Sorun sınıflandırmak; numeric_override her zaman null','Yapılandırılmış itiraz kabulü; otomatik futbol eleştirisi yok'),
 'scientific_referee':('Bilimsel Hakem','C','Finding, kanıt, model ve zaman bilgileri','approved/needs_reanalysis/insufficient_evidence/rejected/abstain kararı','En çok iki inceleme; çözülmeyen durumda skip; olasılık değiştiremez','Deterministik iki turlu kanıt kapısı; bilimsel etki ölçümü gelecekte'),
 'odds_analyst':('Oran Analisti','D','Gerçek oran snapshot, sağlayıcı, piyasa, zaman','Marj, ima edilen olasılık, avantaj ve geçerlilik raporu','Oranı denetlemek; gerçek oran yoksa getiri üretmez','Mevcut odds şeması korunur; yeni toplama/avantaj motoru yok'),
 'risk_manager':('Risk Yöneticisi','D','Hakem kararı, oran, belirsizlik, cüzdan, açık risk, platform kuralı','bet/wait/skip, azami risk bütçesi, sanal kupon isteği','Sanal limitleri uygulamak; kaybı telafi için miktar büyütemez','Paylaşılan bütçe koruması, kupon şeması, yalnız void settlement'),
 'learning_auditor':('Sonuç ve Öğrenme Denetçisi','D','Zaman sıralı sonuçlar, tahminler, sanal işlemler, deneyler','Kalibrasyon/ablation/performance raporları, terfi önerisi','Kanıta dayalı terfi önermek; her maç sonrası keyfî model değişimi yok','Mevcut değerlendirme korunur; terfi/ablation kayıt temeli'),
}
assert set(SPEC)=={r.value for r in Role}

def registry():
    return [dict(id=k,ordinal=i+1,name=v[0],engine=v[1],inputs=v[2],outputs=v[3],authority=v[4],implemented=v[5],llm_required=False) for i,(k,v) in enumerate(SPEC.items())]
