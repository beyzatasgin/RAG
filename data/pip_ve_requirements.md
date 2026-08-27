# pip ve requirements dosyaları

## Amaç

Bu belge, Python paketlerinin doğru yorumlayıcıya kurulmasını, proje bağımlılıklarının requirements dosyalarıyla yönetilmesini ve yaygın ortam uyuşmazlıklarının güvenli biçimde teşhis edilmesini açıklar. Komutlar Windows PowerShell üzerinde proje sanal ortamı kullanıldığı varsayılarak verilmiştir.

## Neden `python -m pip` kullanılmalı?

Sistemde birden fazla Python ve pip bulunabilir. Yalnızca `pip` yazıldığında PATH üzerindeki başka bir kuruluma ait araç çalışabilir. Aşağıdaki biçim pip’i seçilen yorumlayıcının modülü olarak başlatır:

```powershell
& '.\.venv\Scripts\python.exe' -m pip --version
```

Çıktıdaki Python sürümü ve paket yolu `.venv` ile uyumlu olmalıdır. Bu kontrol, paket kurulmuş görünmesine rağmen uygulamanın `ModuleNotFoundError` vermesi gibi sorunları önler.

## Requirements dosyalarının görevleri

`requirements.txt`, uygulamanın çalışması için doğrudan gereken runtime paketlerini içerir. `requirements-dev.txt`, pytest gibi geliştirme ve test araçlarını belirtir. `requirements-lock.txt` ise doğrulanmış ortamın doğrudan ve dolaylı paketlerini kesin sürümleriyle kaydeder.

Geliştirme ortamında ayrı dosyalar şu sırayla kurulabilir:

```powershell
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
& '.\.venv\Scripts\python.exe' -m pip install -r requirements-dev.txt
```

Doğrulanmış ortamı mümkün olduğunca aynı sürümlerle kurmak için lock dosyası tercih edilebilir:

```powershell
& '.\.venv\Scripts\python.exe' -m pip install -r requirements-lock.txt
```

Kurulum ağ erişimi gerektirebilir. Tam çevrimdışı kurulum ancak gerekli dağıtım dosyaları daha önce güvenilir bir yerel cache veya wheel klasöründe bulunuyorsa mümkündür.

## Sürüm pinleme

`paket==1.2.3` kesin sürüm pinidir. Bu yaklaşım tekrarlanabilirliği artırır. Geniş aralıklar yeni sürümlerin otomatik seçilmesine izin verir, fakat doğrulanmamış uyumsuzluk getirebilir. Runtime dosyası küçük ve anlaşılır tutulabilir; lock dosyası dolaylı bağımlılıkları da içerdiği için daha uzundur.

Requirements dosyaları elle güncellenirken paketin Windows, Python sürümü ve sistem mimarisiyle uyumu doğrulanmalıdır. Sadece sürüm numarasını yükseltmek güvenli bir güncelleme kanıtı değildir.

## Kurulu paketleri inceleme

Aşağıdaki komutlar paket değiştirmez:

```powershell
& '.\.venv\Scripts\python.exe' -m pip show streamlit
& '.\.venv\Scripts\python.exe' -m pip list
& '.\.venv\Scripts\python.exe' -m pip check
```

`pip show` tek paketin sürümünü ve konumunu gösterir. `pip list` ortam envanteridir. `pip check`, kurulu paketlerin bildirdiği sürüm gereksinimleri arasında çelişki bulunup bulunmadığını denetler. Başarılı sonuç uygulamanın bütün davranışlarını garanti etmez; yine de temel bağımlılık tutarlılığı için önemlidir.

## Yaygın uyuşmazlıklar

Paket doğru ortam yerine global Python’a kurulmuş olabilir. Python sürümü paket tarafından desteklenmeyebilir veya farklı mimari için hazırlanmış bir dağıtım seçilmiş olabilir. Önce `sys.executable`, sonra pip sürümü ve paket konumu kontrol edilmelidir. Sorunu anlamadan tekrar tekrar kurulum yapmak ortamı daha belirsiz hale getirebilir.

Pip indirme cache’i kurulu paketlerden ayrıdır. Resmî `pip cache` komutlarıyla cache temizlemek `.venv` içindeki paketleri kaldırmaz; ancak gelecekte aynı paketlerin yeniden indirilmesini gerektirebilir. Disk kazanımı ile çevrimdışı yeniden kurulum ihtiyacı birlikte değerlendirilmelidir.

Kurulumdan sonra requirements dosyalarının kendiliğinden güncellendiği varsayılmamalıdır. Ortam envanteri ile repository’deki dosyalar farklıysa fark önce incelenmeli, yalnızca doğrulanmış sürümler kontrollü bir değişiklik olarak kaydedilmelidir.

## Sık sorulan sorular

**Paket kurulu olduğu halde neden import edilemiyor?** Büyük olasılıkla kurulum ve uygulama farklı yorumlayıcılarla çalışıyordur. İki komutta da `sys.executable` yolunu karşılaştırın.

**Lock dosyası neden büyük?** Doğrudan paketlerin yanında onların doğrulanmış dolaylı bağımlılıklarını da içerir.

**`pip check` başarılıysa her şey hazır mı?** Hayır. Bu sonuç yalnızca bildirilen paket gereksinimlerinin tutarlı olduğunu gösterir; uygulama testleri ayrıca çalıştırılmalıdır.
