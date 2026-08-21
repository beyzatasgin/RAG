# Microsoft Foundry Local ile offline kullanım

## Amaç

Bu belge yalnızca bu projede doğrulanmış Microsoft Foundry Local kapsamını açıklar. Proje Windows x64, Python 3.13 proje ortamı ve `foundry-local-sdk-winml==1.2.4` ile geliştirilmiştir. Farklı işletim sistemi, mimari, Python veya SDK sürümü için aynı davranış otomatik olarak varsayılmamalıdır.

## Paket ve ortam seçimi

Proje WinML paket varyantını kullanır. Standart `foundry-local-sdk` ile `foundry-local-sdk-winml` aynı sanal ortamda birlikte kurulmaz; varyantların bağımlılıkları ve execution provider tercihleri karışabilir. Kurulu sürüm salt okunur olarak kontrol edilebilir:

```powershell
& '.\.venv\Scripts\python.exe' -m pip show foundry-local-sdk-winml
& '.\.venv\Scripts\python.exe' -m pip check
```

Bu komutlar model başlatmaz. Paket kurulumu veya güncellemesi ise ağ kullanabilir ve ayrı bir değişiklik olarak doğrulanmalıdır.

## Model cache kavramı

Embedding ve chat modellerinin dosyaları repository dışında seçilen model cache dizininde tutulur. İlk model hazırlığı önemli ağ trafiği ve disk alanı gerektirebilir. Bir modelin katalogda görünmesi, bütün dosyalarının hazır olduğu veya offline yüklenebildiği anlamına gelmeyebilir. Cache durumu SDK’nın doğrulanmış API’leriyle ve dosya envanteriyle kontrollü biçimde incelenmelidir.

Bu projede kullanılan alias’lar:

- Embedding: `qwen3-embedding-0.6b`
- Chat: `qwen3-1.7b`

Kod offline-by-default tasarlanmıştır. Model erişiminde `allow_download=False` varsayılanı kullanılır. Cache eksikse uygulamanın kendiliğinden indirme başlatması yerine açık hata vermesi beklenir. İndirme izni yalnızca kullanıcının ayrıca onayladığı hazırlık adımında açılmalıdır.

## Runtime yaşam döngüsü

Foundry Local kullanımı şu kontrollü sırayı izler:

1. Foundry manager initialize edilir veya mevcut process-global manager yeniden kullanılır.
2. Model alias’ı katalogdan çözülür.
3. `model.is_cached` ile modelin cache durumu kontrol edilir.
4. Model cached değilse `allow_download=False` durumunda açıklayıcı hata üretilir ve
   download yapılmaz. Yalnızca açık izin varsa `model.download(...)` çağrılabilir.
5. `model.is_loaded` ile modelin bellekte yüklü olup olmadığı kontrol edilir.
6. Model yüklü değilse `model.load()` çağrılır ve wrapper bu modelin sahipliğini kaydeder.
7. Model türüne göre embedding veya chat client oluşturulur.
8. Cleanup sırasında yalnızca bu wrapper’ın yüklediği modeller unload edilir.

Uygulama `FoundryRuntime` katmanıyla lazy initialization, sahiplik ve cleanup yönetir.
Wrapper process-global Foundry manager’ı sahiplenmez veya kapatmaz. Cleanup, wrapper’ın
sahip olduğu modelleri unload eder ve kendi model/client referanslarını temizler. Başka
bir bileşen tarafından önceden yüklenmiş model bu wrapper tarafından unload edilmez.
Import işlemi tek başına model yüklememelidir. Uzun ömürlü süreçler model dosyalarını
veya belleği kullanımda tutabileceği için normal kapanış sonrasında Python, Foundry
veya ONNX süreçleri gerektiğinde salt okunur olarak kontrol edilir.

## Offline iddiasının sınırı

Modeller ve gerekli runtime bileşenleri ilk kez hazırlandıktan sonra amaç, normal embedding ve chat inference işlemlerini çevrimdışı yapmaktır. Ancak ağ adaptörü kapalı uçtan uca test gerçekleştirilmeden “mutlak offline” garantisi verilmez. Hazırlık, katalog discovery veya eksik bileşen işlemleri ağ gerektirebilir.

Shared cache kullanıldığında SDK lifecycle sırasında ortak `foundry.modelinfo.json`
metadata dosyası yeniden yazılabilir. Cache’i farklı SDK sürümleri veya eşzamanlı
uygulamalarla kullanmak değişiklik riskini artırır. Metadata ve model klasörleri
üzerinde işlem öncesi/sonrası hash, dosya sayısı ve boyut doğrulaması yapılması güvenli
bir yaklaşımdır. `allow_download=False`, ölçülmüş tam ağ izolasyonunun yerine geçmez.

Doğrulanmamış CLI veya SDK metodu tahmin edilerek çalıştırılmamalıdır. Önce kurulu sürümün yerel yardım ve metadata bilgisi incelenmeli, ağ gerektiren adım açıkça ayrılmalıdır.

Disk ve bellek kapasitesi model hazırlığından önce ölçülmelidir. Cache temizliği düşünülüyorsa hangi uygulamanın hangi modeli kullandığı belirlenmeli; çalışan proje için gerekli dosyalar genel bir temizlik varsayımıyla kaldırılmamalıdır.

## Sık sorulan sorular

**Paket kuruluysa model de hazır mıdır?** Hayır. SDK paketi ile model cache dosyaları farklı bileşenlerdir.

**`allow_download=False` ne sağlar?** Uygulamanın bu çağrı üzerinden eksik modeli otomatik indirmemesini sağlar; bütün sistem için ağ izolasyonu kanıtı değildir.

**Shared cache repository içinde mi olmalı?** Hayır. Büyük model dosyaları repository dışında tutulmalı ve commit edilmemelidir.

**Offline çalışmayı nasıl kesinleştiririm?** Cache ve runtime kontrollerinden sonra ağ adaptörü kapalıyken ayrı uçtan uca test yapılmalıdır.
