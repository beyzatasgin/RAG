# Hafta 4 — Kullanıcı arayüzü ve proje doğrulaması

Hafta 4, önceki haftaların yerel RAG çekirdeğini sade bir Streamlit arayüzüyle
tamamlar. Uygulama tek kullanıcılı ve yereldir; çok kullanıcılı üretim sunucusu
olarak tasarlanmamıştır.

## Eklenenler

- Türkçe soru-cevap ve belge yönetimi sekmeleri
- Güvenli `.txt`/`.md` upload, 5 MiB sınırı, UTF-8 ve path traversal kontrolü
- Geçici dosya ve `os.replace` ile atomik kayıt
- Butonla başlatılan, download varsayılanı kapalı ingestion ve RAG işlemleri
- Session state içinde son cevap ve ingestion özetinin korunması
- Retrieval evaluation, latency benchmark ve offline-readiness kontrolü
- Headless Streamlit ve saf UI yardımcı testleri

UI açılışta model yüklemez. Her işlem `FoundryRuntime` context manager ile kapanır.
Uploadlar `runtime_data/uploads/`, ölçüm JSON dosyaları `runtime_data/` altında
tutulur ve Git tarafından ignore edilir. `delete_missing` UI'da sunulmaz.

## Kabul tanımı

Pipeline uçtan uca yerel çalışır, doğrulanmış kaynakları gösterir, no-result
kısa devresini korur ve model sınırlamalarını açıkça bildirir. Tam ağ izolasyonu
otomatik olarak kanıtlanmaz; adaptör kapalı manuel test ayrıca gereklidir.
