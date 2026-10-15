# AI Betting Lab

Tam proje kaynakları, modelleri, tarihsel kanıtları ve testleri iki kayıpsız arşiv parçasında bulunur. Tarayıcı aktarımının klasör sınırlaması nedeniyle bu dağıtım biçimi kullanılmıştır. Dosyaların SHA-256 doğrulaması otomatik yapılır.

## Çalıştırma

Repoyu klonlayıp proje klasöründe:

```bash
python restore_project.py
python -m pip install -r requirements-cloud.txt
python -m unittest discover -s tests -v
python -m unittest discover -s tests_phase2 -v
python -m unittest discover -s tests_foundation -v
python -m unittest discover -s tests_cloud -v
```

Geri açma internet çağrısı yapmaz. Ardından bütün kaynaklar betting_lab/, engine/, foundation/, cloudcheck/, supabase/ ve diğer özgün klasörlerinde yer alır. Yerel dosya değişiklikleriniz varsa önce yeni bir klonda çalıştırın; geri açma paket yollarına dosya yazar.

GitHub Actions paketi otomatik açıp tam testleri ve PostgreSQL 17 üzerinde bağımsız bağlantı kontrollerini çalıştırır. Ücretli API/LLM/VPS gerekmez; gerçek bahis veya sanal pilot başlatılmaz. Hosted Supabase doğrulamasının kapsamı ve açık kalan kapılar TEST_REPORT.md içindedir. Şifre, token veya service-role anahtarı bu repoda bulunmaz.
