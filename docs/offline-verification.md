# Offline doğrulama

İlk Python paketleri ve model dosyaları indirilirken internet gerekir. Shared cache
ve `.venv` hazır olduktan sonra normal CLI/UI akışı API key, Azure kaynağı veya cloud
endpoint gerektirmez. `--allow-download` yalnızca açık ilk-kurulum seçeneğidir ve UI'da
sunulmaz.

```powershell
python offline_check.py --db-path runtime_data/rag.db --model-cache-dir '<shared-cache>'
```

Araç cached modelleri, SQLite integrity/embedding metadata'sını ve Python runtime
kaynaklarındaki bilinen cloud endpoint kalıplarını kontrol eder. README URL'leri
runtime çağrısı sayılmaz. SDK katalog metadata'sının değişmemesi veya geçersiz proxy
testi tam ağ izolasyonunu kanıtlamaz; bu nedenle overall sonuç normalde `WARN` olur.

## Manuel kesin adım

1. Modellerin cache'te olduğunu doğrulayın.
2. Ağ adaptörünü işletim sistemi ayarlarından kapatın.
3. `--allow-download` olmadan ingestion, retrieval ve tek RAG sorusu çalıştırın.
4. Yeni model/EP dosyası oluşmadığını ve API key istenmediğini doğrulayın.

Shared cache'i farklı SDK sürümleriyle veya eşzamanlı uygulamalarla kullanmak katalog
metadata'sı ve process-global manager nedeniyle risklidir.
