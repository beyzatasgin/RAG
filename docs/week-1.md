# Hafta 1 — Güvenli yerel model temeli

## Hedefler

Hafta 1'in amacı Microsoft Foundry Local model yaşam döngüsünü küçük, anlaşılır ve test edilebilir bir katmanda toplamak; embedding ve chat modellerini varsayılan olarak indirmesiz çalıştırmaktır. RAG cevap üretimi ve kullanıcı arayüzü henüz bu haftanın kapsamında değildir.

## Foundry Local nedir?

Microsoft Foundry Local, uyumlu modelleri Windows bilgisayarda yerel olarak çalıştırır. Model ilk kez edinildikten sonra inference için bulut API anahtarı gerekmez. Bu projede Windows için `foundry-local-sdk-winml==1.2.4`, CPython 3.13 tabanlı izole `.venv` içinde kullanılmaktadır.

## Chat ve embedding modelleri

- `qwen3-embedding-0.6b`, metni semantic aramada kullanılabilecek sayısal vektörlere dönüştürür.
- `qwen3-1.7b`, kullanıcı mesajından kısa doğal dil cevabı üretir.

Embedding modeli doküman alma aşamasında, chat modeli ise ileride grounded cevap üretiminde kullanılacaktır. İki modelin client türleri ve görevleri birbirinden farklıdır.

## Runtime lifecycle

`FoundryRuntime` şu sırayı yönetir:

1. SDK'yı yalnızca `initialize()` çağrıldığında import eder.
2. Process-global manager'ı başlatır veya mevcut manager'ı kullanır.
3. Model alias'ını katalogdan çözer.
4. Cache durumunu kontrol eder.
5. Gerekirse modeli yükler ve doğru client'ı oluşturur.
6. Context manager kapanırken yalnızca kendisinin yüklediği modelleri unload eder.

Cleanup hataları saklanmaz; yeniden denenebilir ve asıl uygulama hatasının kaybolmasına izin verilmez.

## Offline ve explicit download

`get_embedding_client()` ve `get_chat_client()` varsayılan olarak `allow_download=False` kullanır. Cache'te olmayan model offline modda açık bir hata üretir. İndirme ancak kullanıcı CLI'da `--allow-download` bayrağını verdiğinde mümkün olur. Demo betikleri doğrudan `download()`, `load()` veya EP indirme API'si çağırmaz.

## Shared cache

Bu geliştirme makinesinde iki model daha önce `.foundry_local_samples` cache'ine indirilmiştir. Tekrar indirmeyi önlemek için `model_cache_dir` yalnızca CLI argümanıyla açıkça seçilebilir. Uygulama verisi ve loglar `local-rag-assistant` dizininde tutulur.

Shared cache kullanımı risksiz değildir: SDK `foundry.modelinfo.json` dosyasını güncelleyebilir. Aynı cache'i farklı SDK sürümleriyle veya eşzamanlı uygulamalarla kullanmak önerilmez. Kalıcı uygulama yapılandırması tek app adı ve tek runtime kullanmalıdır.

## Çalıştırılan testler

Unit testler SDK'sız fake manager, model ve client nesneleriyle şunları denetler:

- Import sırasında SDK/model işlemi olmaması
- Path alanlarının `Configuration` factory'sine doğru aktarılması
- Varsayılan offline davranış ve explicit download sınırı
- Embedding ve chat çıktılarının işlenmesi
- Hatalarda non-zero dönüş ve her durumda cleanup
- Model sahipliği, unload ve cleanup retry davranışı

Gerçek cached-model smoke testlerinin sonuçları test çalıştırmasından sonra raporlanır; bu belge başarısız veya henüz çalıştırılmamış bir smoke'u başarılı saymaz.

## Öğrenme çıktıları

- Model cache'i ile modelin belleğe yüklenmesinin farklı kavramlar olduğunu görmek
- SDK singleton yaşam döngüsünü güvenli biçimde sarmalamak
- Offline varsayılanı ve açık indirme iznini ayırmak
- Gerçek SDK bağımlılığını fake nesnelerle unit testlerden uzak tutmak
- Shared cache'in disk kazancı ile metadata/eşzamanlılık risklerini değerlendirmek

## Tamamlanma kriterleri

- Runtime opsiyonel app-data, model-cache ve log yollarını destekler.
- Embedding ve chat demoları runtime katmanını kullanır.
- Normal testler gerçek model çalıştırmadan geçer.
- Cached embedding ve chat smoke testleri indirmesiz başarılı olur.
- Modeller süreç sonunda unload edilir ve DB değişmez.

Son üç madde ancak doğrulama komutları başarılı olduğunda tamamlanmış kabul edilir.
