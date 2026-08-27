# SQLite temelleri ve sık hatalar

## Amaç

Bu belge, SQLite veritabanının temel çalışma biçimini ve dosyaya zarar vermeden uygulanabilecek ilk teşhis adımlarını açıklar. SQLite ayrı bir sunucu gerektirmez; veriler çoğunlukla tek bir dosyada tutulur. Bu kolaylık, dosyanın normal bir metin belgesi gibi güvenle kopyalanıp değiştirilebileceği anlamına gelmez.

## Connection ve transaction

Uygulama, DB dosyasına bir connection açarak SQL çalıştırır. Veri değiştiren işlemler transaction içinde ele alınmalıdır. Başarı durumunda `commit`, hata durumunda `rollback` uygulanır. Python’da bağlantının kapsamını açık tutmak ve iş bitince kapatmak lock sorunlarını azaltır.

Birden fazla tablo arasındaki ilişki foreign key ile korunabilir. SQLite bağlantısında foreign key denetiminin etkin olduğundan emin olunmalıdır:

```sql
PRAGMA foreign_keys = ON;
```

Kullanıcı değerlerini SQL metnine birleştirmek yerine parametreli sorgu kullanılır:

```python
connection.execute(
    "SELECT * FROM documents WHERE source = ?",
    (source_name,),
)
```

Bu yöntem tırnaklama hatalarını azaltır ve sorgu yapısıyla kullanıcı verisini ayırır.

## Salt okunur inceleme

Bir DB’yi teşhis ederken yanlışlıkla oluşturma veya yazma riskini azaltmak için SQLite read-only URI kullanılabilir:

```python
import sqlite3
from contextlib import closing

database_uri = "file:runtime_data/rag.db?mode=ro"

with closing(sqlite3.connect(database_uri, uri=True)) as connection:
    connection.execute("PRAGMA query_only = ON")
    integrity = connection.execute("PRAGMA integrity_check").fetchone()
    print(integrity)
```

`mode=ro` dosyayı salt okunur açar ve dosya yoksa yeni DB oluşturmak yerine bağlantı
hatası verir. `PRAGMA query_only = ON`, bağlantı seviyesinde ek yazma koruması sağlar.
`closing` bloğundan çıkıldığında connection kesin olarak kapatılır. Örnekte çalıştırılan
bütünlük sorgusunun beklenen sonucu `ok` değeridir. Bu kontrol uygulama verisinin
anlamsal olarak doğru olduğunu değil, SQLite yapısının tutarlı göründüğünü belirtir.

## `database is locked` hatası

Bu hata başka bir connection veya sürecin uyumsuz bir yazma kilidi tuttuğunu gösterebilir. Önce çalışan uygulamalar ve uzun süren transaction’lar belirlenmelidir. Süreci zorla sonlandırmak veya DB dosyasını aktif bağlantı sırasında değiştirmek veri kaybı riski taşır. İşlemi durdurun, hangi uygulamanın yazdığını doğrulayın ve normal uygulama kapanışını tercih edin.

Kilit hatası her zaman bozuk DB anlamına gelmez. Çok uzun transaction, kapanmayan connection veya aynı dosyaya eşzamanlı yazma girişimi de neden olabilir. Hata mesajı ve zaman bilgisi kaydedilmelidir.

## WAL ve journal dosyaları

SQLite çalışma sırasında `-wal`, `-shm` veya `-journal` uzantılı geçici yardımcı dosyalar oluşturabilir. Bunlar aktif transaction’ın parçası olabilir. Ana DB’den ayrı ve gereksiz dosyalar oldukları varsayılarak silinmemelidir. Önce bütün bağlantıların güvenli biçimde kapandığı doğrulanmalıdır.

## DB dosyasını Git’e ekleme riski

Binary DB dosyaları küçük bir değişiklikte tamamen değişmiş görünebilir, merge edilemez ve testlerin yanlışlıkla kalıcı veriye yazmasına yol açabilir. Yeniden üretilebilen runtime DB’ler `.gitignore` kapsamında tutulmalıdır. Kaynak belgeler, şema kodu ve kontrollü migration’lar version control için daha uygundur. Küçük test fixture DB’leri ancak açık bir gerekçe ve salt-okunur test davranışı varsa takip edilmelidir.

DB üzerinde bakım yapmadan önce dosya yolu, boyut, değiştirilme zamanı ve güvenilir hash kaydedilebilir. Yedek gerekiyorsa aktif bağlantılar kapatıldıktan sonra kapsamı açık bir plan uygulanmalıdır. Yedeğin gerçekten okunabilir olduğu ayrıca doğrulanmadan asıl dosya üzerinde riskli işlem yapılmamalıdır.

## Sık sorulan sorular

**DB dosyasını metin düzenleyiciyle açabilir miyim?** İçeriğini değiştirmeyin. SQLite uyumlu araç veya salt-okunur bağlantı kullanın.

**Integrity sonucu `ok` ise lock sorunu çözülmüş müdür?** Hayır. Bütünlük ve eşzamanlı erişim farklı konulardır.

**Aktif uygulama varken DB’yi değiştirebilir miyim?** Hayır. Önce bağlantıların kontrollü kapandığını ve güvenli bir geri alma kaynağı bulunduğunu doğrulayın.

**Runtime DB neden Git dışında tutulur?** Kullanıcı verisi, embeddingler ve çalışma zamanı değişiklikleri kaynak kod commitlerinden ayrılmalıdır.
