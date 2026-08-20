# 7–10 dakikalık demo akışı

1. **Problem (1 dk):** Genel modelin özel belgelerde hallucination riski.
2. **Mimari (1 dk):** Retrieve → Augment → Generate ve tamamen yerel modeller.
3. **Ingestion (1 dk):** Bir `.txt` yükle, güvenlik kontrollerini ve özeti göster.
4. **Retrieval (1 dk):** SQLite chunk/embedding ve hybrid skorları göster.
5. **Grounded cevap (2 dk):** Grand Slam sorusu, cevap ve doğrulanmış kaynaklar.
6. **No-result (1 dk):** Belgelerde olmayan soru ve chat kısa devresi.
7. **Sınırlamalar (1 dk):** Küçük model hatası, inline citation uyarısı ve insan kontrolü.
8. **Evaluation (1 dk):** Hit@k, MRR ve latency; generation kalitesi olmadığını belirt.

Gerçek olmayan başarı veya ağ izolasyonu iddiası yapılmaz. Demo öncesi disk, cache,
DB integrity ve model yolları kontrol edilir.
