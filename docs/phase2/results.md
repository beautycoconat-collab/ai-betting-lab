# Gerçek değerlendirme sonuçları

Eğitim ve değerlendirme gerçek geçmiş maçlardan yapılmıştır. Bütün sayılar paketlenen evaluation.json dosyalarından türetilmiştir. Skor hedefleri farklıdır; iki veri seti birleştirilmemiştir.

## Milli maçlar — uzatma dahil, penaltı atışları hariç

Eğitim: 9800; doğrulama: 1471; görülmemiş test maçları: 2034. Doğrulama seçimi: **dixon_coles**.

| Model | 1X2 Brier ↓ | 1X2 Log Loss ↓ | Skor Log Loss ↓ | Skor Brier ↓ | Tam skor isabeti | En olası skor ECE ↓ |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 0.632186 | 1.049016 | 3.154565 | 0.938146 | 10.42% | 0.013189 |
| elo | 0.559170 | 0.943773 | 2.966895 | 0.927520 | 13.23% | 0.007344 |
| poisson | 0.533165 | 0.909331 | 2.866938 | 0.921132 | 13.47% | 0.015295 |
| dixon_coles | 0.533616 | 0.910424 | 2.868224 | 0.921258 | 13.82% | 0.011337 |

## Bundesliga 2024/25 — 90 dakika

Eğitim: 135; doğrulama: 73; görülmemiş test maçları: 98. Doğrulama seçimi: **dixon_coles**.

| Model | 1X2 Brier ↓ | 1X2 Log Loss ↓ | Skor Log Loss ↓ | Skor Brier ↓ | Tam skor isabeti | En olası skor ECE ↓ |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 0.692886 | 1.135026 | 3.179433 | 0.951327 | 10.20% | 0.001907 |
| elo | 0.661306 | 1.092905 | 3.097351 | 0.946532 | 7.14% | 0.026880 |
| poisson | 0.671348 | 1.110270 | 3.102978 | 0.945598 | 7.14% | 0.037317 |
| dixon_coles | 0.666377 | 1.105077 | 3.113344 | 0.945215 | 6.12% | 0.051086 |

Milli maç testinde Poisson, doğrulamada seçilen Dixon–Coles’tan az farkla daha iyi skor log loss verdi. Bundesliga testinde Elo daha iyi skor log loss verdi; referans modelin tam skor isabeti diğerlerinden yüksekti. Model seçim kuralı bu test sonuçlarına bakılarak değiştirilmedi. Olasılık kalitesi ve en çok olası skoru tutturma oranı aynı ölçüm değildir.

## Toplama kanıtı

- Milli maçlar: 49.943 kabul, 2 çelişkili satır karantinada. İlk toplama raporundaki 49.944/1 sayımı, ilk çelişen kaydın da dışlandığı cached-reparse.json ile düzeltildi. Ham kanıt değişmedi. 2010–2023 çalışma alt kümesi 13.305 maçtır.
- OpenFootball ve OpenLigaDB: mevcut gerçek 2024/25 sezonundan ayrı ayrı 306 kayıt yeni adapter ile tekrar ayrıştırıldı. Bunlar aynı maçlar olabilir; eğitimde iki kez sayılmadı.
- Yeni canlı Fjelstul: 1.248, WorldCup: 64, TheSportsDB: 5 kayıt. Nötr saha/hedef tanımı doğrulanmayan kayıtlar bu eğitimlere eklenmedi.
- Canlı keşif: OpenLigaDB 680 ve OpenFootball 270 katalog kaydı. OpenLigaDB kataloğu topluluk/test ligleri de içerebilir; kayıt sayısı kaliteli bağımsız lig sayısı değildir.
- Ek sezon indirmeleri saatlik kota nedeniyle beklemede. FootballCSV için canlı doğrulama yok.

## Test kanıtı

- Aşama 1: 33 Python regresyon testi; 23 yerel PostgreSQL kontrolü.
- Aşama 2: 66 Python testi; 28 yerel PostgreSQL kontrolü. Toplam 99 Python testi ve 51 SQL kontrolü.
- Her iki veri setindeki dört model yeniden eğitildi: örneklenen 1X2 olasılıklarında en büyük mutlak fark 0; tolerans 1e-12. Ayrıntı retraining-reproducibility.json.
- Gerçek Supabase ağ/rol entegrasyonu ve hosted eşzamanlılık test edilmedi.

Bu sonuçlar geriye dönük kronolojik tek holdout deneyleridir. Canlı başarı, bahis getirisi veya kârlılık kanıtı değildir.
