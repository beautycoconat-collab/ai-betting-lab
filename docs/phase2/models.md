# Matematiksel modeller ve değerlendirme

Bütün modeller aynı eğitim etiketleriyle, aynı kronolojik bölmeler üzerinde karşılaştırılır. Rastgele train/test bölmesi yoktur. Eğitim bitiş tarihi ile doğrulama/test tarihleri ayrıdır. Aynı günkü Elo güncellemeleri günün bütün maçlarının özellikleri çıkarıldıktan sonra uygulanır. Holdout sırasında model parametreleri veya Elo puanları gerçek test sonuçlarıyla güncellenmez.

## Modeller

- Referans: eğitimdeki ortalama ev/deplasman gollerinden sabit iki bağımsız Poisson oranı.
- Elo: başlangıç 1500, K=20, nötr olmayan sahada 60 puan avantaj. Maçtan önceki Elo farkından, saha etkisiyle sayısal Poisson gol regresyonu öğrenilir. Elo tek başına tam skor dağılımı değildir; bu yüzden gol oranı bağlantısı açıkça uygulanmıştır.
- Poisson: takım hücum/savunma parametreleri ve saha avantajı. Hücum/savunma ortalamaları sıfıra merkezlenir. Zaman ağırlığında yarı ömür 730 gün, ridge katsayısı 0.01. Bu sabitler test sonuçlarına göre seçilmedi.
- Dixon–Coles: Poisson'a düşük skorlu dört hücre düzeltmesi eklenir. `(0,0):1−λμρ`, `(0,1):1+λρ`, `(1,0):1+μρ`, `(1,1):1−ρ`. Diğer hücrelerin çarpanı 1'dir. Parametreler ağırlıklı olasılık optimizasyonuyla birlikte öğrenilir.

λ ve μ için 0.02–8 aralığı, ρ için −0.12–0.015 aralığı kullanılır; böylece bütün dört düzeltme pozitiftir. Bu sınırlar model varsayımıdır; uç skor tahminlerini daraltabilir. SciPy L-BFGS-B analitik gradyanla kullanılır, yakınsamayan fit hata verir. Model başına convergence/iterasyon bilgisi evaluation.json içindedir.

Tam PMF `Poisson(h;λ) × Poisson(a;μ) × τ(h,a;ρ)` ile bütün negatif olmayan tam sayı çiftleri için tanımlıdır. 0–20 görüntüleme matrisi yeniden normalize edilmez; dışarıdaki kütle açıkça saklanır. 1X2 olasılıkları Skellam ve Dixon–Coles düzeltmesiyle hesaplanır. Log olasılığı doğrudan hesaplamak çok küçük olasılıklarda underflow'u önler.

## Ölçümler

1X2 Brier üç sınıfın kare hatalarının toplamıdır; üçe bölünmez (0–2 ölçeği). 1X2 log loss doğal logaritma kullanır. Exact-score log loss gerçekleşen tam skorun negatif log olasılığıdır. Exact-score Brier sonsuz skor sınıfları için `Σ p² − 2 p(gerçek) + 1` olarak değerlendirilir. Sayısal toplam 0–30 matrisinden gelir; atlanan `Σ p²`, dış kuyruk kütlesinin karesi ile üstten sınırlanır. Rapor tahminler arasındaki en büyük bu sınırı verir.

Kalibrasyon, en olası skorun güveni, önceden belirlenmiş 10 skor hücresi ve 1X2 için 10 eşit olasılık aralığında gerçekleşme sıklığıyla ölçülür. Bin başına örnek sayısı, ortalama tahmin, gerçekleşme ve ECE kaydedilir. Düşük örnek sayılı veya küçük olasılıklı hücrelerde ECE tek başına yeterli değildir. Olasılıkları doğrulama kümesiyle yeniden ölçekleyen temperature/isotonic calibration bu teslimatta uygulanmadı; rapor kalibrasyon tanılamasıdır.

Doğrulama exact-score log loss en düşük model seçilir. Test kümesi model seçimi veya yeniden eğitim için kullanılmaz. Testte başka bir model daha iyi çıkarsa raporda aynen gösterilir. Milli ve kulüp veri setleri farklı skor hedeflerine sahip olduğundan birleştirilmez.

## Sızıntı sınırı

Arşivler 2026'da indirilmiştir. Gerçek geçmiş sonuçlarla geriye dönük kronolojik test yapılmıştır; o tarihlerde bilinen arşiv sürümünün yeniden oynatıldığı ileri sürülmez. Arşivde sonradan yapılmış düzeltmeler ve güncel ülke isimleri bulunabilir. `point_in_time` modu, eğitim kesiminden sonra gözlenmiş arşivi reddeder. Doğrulanmış maç öncesi snapshot olmadan tarihsel bahis getirisi, kaynak tahmin başarısı veya gerçek zamanlı başarı iddiası kurulmaz.

## Birincil yöntem kaynakları

- Dixon & Coles (1997), Modelling Association Football Scores and Inefficiencies in the Football Betting Market: https://doi.org/10.1111/1467-9876.00065
- SciPy Poisson: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.poisson.html
- SciPy Skellam: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.skellam.html
- SciPy L-BFGS-B: https://docs.scipy.org/doc/scipy/reference/optimize.minimize-lbfgsb.html
