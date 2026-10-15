# GitHub çalışma kopyası

Kaynak kodları proje kökündedir. Büyük tarihsel kanıt/tahmin dosyalarının tamamı teslim edilen ZIP içindedir; kaynak repo aktarımında bu büyük dosyalar hariç tutulur. Orijinal dosyalar sentetik veriyle değiştirilmez. Tam 157 test için teslim ZIP'ini kullanın. Kaynak repo CI'si bu dosyalara bağlı 5 testi açıkça skipped gösterir; geçti saymaz. Yerel tam teslim test komutları:

```bash
python -m pip install -r requirements-cloud.txt
python -m unittest discover -s tests -v
python -m unittest discover -s tests_phase2 -v
python -m unittest discover -s tests_foundation -v
python -m unittest discover -s tests_cloud -v
```

Tam teslim ZIP'i tarihsel dosyaları doğrudan içerir. CI'nin geçmesi, hariç tutulan 5 artifact kontrolünün çalıştırıldığı anlamına gelmez. Bu kontroller teslim ortamında ayrı çalıştırılıp raporlanmıştır.

`.github/workflows/verification-ci.yml` public repoda push/PR ile bir defalık doğrulama yapar. PostgreSQL servisi yalnız GitHub'ın geçici runner'ındaki localhost'a açıktır; Supabase veya gerçek bahis hesabına bağlanmaz. Eski manual workflow'lar korunmuştur. Gerçek hosted doğrulama raporu TEST_REPORT.md içindedir; JWT ve doğrudan bulut bağlantısı ayrı kabul kapılarıdır.
