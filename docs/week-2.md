# Hafta 2 — Güvenli ingestion ve retrieval

## Hedefler

Hafta 2, kullanıcının UTF-8 `.txt` ve `.md` belgelerini tekrar güvenle indeksleyebilmesini ve CLI üzerinden ilgili chunk'ları bulabilmesini sağlar. LLM ile grounded cevap üretimi ve Streamlit kullanıcı arayüzü bu haftanın kapsamında değildir.

## Akış

```text
Document → deterministic chunking → local embedding → SQLite
Query    → local embedding → NumPy full scan → semantic/hybrid results
```

`FoundryRuntime` embedding modelinin cache, load, client ve unload yaşam döngüsünü yönetir. Download varsayılan olarak kapalıdır.

## Normalize SQLite şeması

Yeni çalışma veritabanı varsayılan olarak `runtime_data/rag.db` yolundadır. Legacy `documents.db` değiştirilmez.

- `schema_info`: `schema_version=1`
- `documents`: benzersiz kaynak, içerik SHA-256, dosya boyutu ve UTC indeks zamanı
- `chunks`: belge foreign key'i, sıralı chunk index'i, içerik ve içerik hash'i
- `embeddings`: chunk foreign key'i, model alias, dimension, JSON vektör ve UTC üretim zamanı

Foreign key'ler her bağlantıda etkinleştirilir. Belge değişimi tek transaction içinde eski chunk/embedding kayıtlarını cascade ile yeniler. Embedding üretimi başarısız olursa önceki geçerli belge sürümü korunur.

## Chunk size ve overlap

Varsayılan maksimum chunk uzunluğu 800, overlap 100 karakterdir. Algoritma önce boş satır/paragraf sınırını, sonra kelime sınırını tercih eder. Uzun paragraflar yine maksimumu aşmadan bölünür. Aynı metin ve ayarlar her zaman aynı sırada aynı chunk'ları üretir.

## SHA-256 ve idempotency

Her dosyanın ham UTF-8 byte içeriği SHA-256 ile tanımlanır. DB'deki hash aynıysa dosya yeniden chunk edilmez veya embed edilmez. Kaynak dosya kaybolduğunda kayıt varsayılan olarak silinmez; `--delete-missing` açık kullanıcı kararıdır.

## Transaction ve rollback

Bir dosyanın bütün embeddingleri doğrulandıktan sonra document, chunk ve embedding kayıtları tek transaction içinde yazılır. JSON, dimension ve finite değer kontrolleri storage sınırında tekrar yapılır. Hata durumunda bağlantı rollback edilir ve kapanır.

## Semantic ve hybrid retrieval

Semantic skor cosine similarity ile hesaplanır. Varsayılan combined skor `%70 semantic + %30 keyword` olarak korunmuştur. Sonuçlar combined score azalan sırada; eşitlikte kaynak adı ve chunk index'iyle deterministik sıralanır. Query modeli ile DB model alias/dimension bilgisi uyuşmazsa karşılaştırma reddedilir.

Bu eğitim veri setinde bütün vektörler NumPy ile bellekte taranır. Bu açık ve anlaşılır yaklaşım küçük veri için uygundur; büyük veri için ileride gerçek bir vector index gerekir.

## Komut örnekleri

```powershell
python ingest.py --data-dir data --db-path runtime_data/rag.db --model-cache-dir 'C:\Users\Beyza\.foundry_local_samples\cache\models'
python retrieval.py --db-path runtime_data/rag.db --query "Grand Slam turnuvaları hangileridir?" --top-k 3 --debug --model-cache-dir 'C:\Users\Beyza\.foundry_local_samples\cache\models'
python main.py --db-path runtime_data/rag.db --model-cache-dir 'C:\Users\Beyza\.foundry_local_samples\cache\models'
```

Bu komutlarda `--allow-download` verilmediği sürece cache'te olmayan model indirilmez.

## Test yaklaşımı

Unit testler `tmp_path` veritabanları ve fake embedding client kullanır. Gerçek Foundry modeli, shared cache ve legacy DB unit testlerde açılmaz. Testler chunking sınırlarını, şemayı, foreign key/cascade davranışını, rollback'i, idempotency'yi, missing/delete politikasını, veri bozulmasını ve deterministic hybrid sıralamayı kapsar.

## Öğrenme çıktıları

- Dosya hash'iyle idempotent ingestion tasarlamak
- Normalize relational şema ve foreign key kullanmak
- Transaction sınırını pahalı model çağrısından sonra kurmak
- Vektör JSON'unu okuma sınırında doğrulamak
- Semantic ve keyword skorlarını açıklanabilir biçimde birleştirmek
- Legacy kullanıcı verisini yeni runtime verisinden ayırmak

Hafta 3'te retrieved chunk'lara dayanan grounded prompt ve yerel chat generation eklenecektir.
