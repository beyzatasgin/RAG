# Python kurulumu ve sanal ortam kullanımı

## Amaç

Bu belge, Windows ve PowerShell kullanan başlangıç seviyesindeki öğrencilerin doğru Python yorumlayıcısını seçmesini ve projeye özel bir sanal ortam kullanmasını açıklar. Amaç, paketleri global Python ortamına kurmadan tekrarlanabilir ve izole bir çalışma alanı oluşturmaktır.

## Python sürümünü ve yolunu kontrol etme

Bir bilgisayarda birden fazla Python kurulumu bulunabilir. Önce hangi sürümün ve executable dosyasının kullanılacağını belirleyin. PowerShell üzerinde şu salt okunur komutlar yararlıdır:

```powershell
py -0p
python --version
where.exe python
Get-Command python -All
```

`py -0p`, Python Launcher tarafından bulunan yorumlayıcıları yollarıyla listeler. `python --version` yalnızca o anda PATH üzerinden seçilen sürümü gösterir. Proje için desteklenen sürümü README ve bağımlılık dosyalarıyla karşılaştırın. Microsoft Store yönlendirmesi gerçek bir kurulum gibi görünebildiği için tam executable yolunu doğrulamak önemlidir.

## Projeye özel venv oluşturma

Komutu proje kökünde çalıştırın. Aşağıdaki Windows PowerShell örneği `.venv` adlı ortamı oluşturur:

```powershell
python -m venv .venv
```

Belirli bir yorumlayıcı seçmek gerekiyorsa genel `python` komutu yerine doğrulanmış tam yolu kullanın. Oluşturma tamamlandıktan sonra ortamı PowerShell oturumunda etkinleştirebilirsiniz:

```powershell
.\.venv\Scripts\Activate.ps1
```

Komut isteminin başında `(.venv)` görünmesi faydalı bir işarettir, fakat tek başına kesin kanıt değildir. Aşağıdaki kontroller seçilen yorumlayıcıyı doğrular:

```powershell
python -c "import sys; print(sys.executable)"
python -m pip --version
```

## Aktivasyon olmadan çalışma

Aktivasyon zorunlu değildir. Otomasyonlarda ve hata ayıklarken proje yorumlayıcısını açıkça çağırmak daha güvenlidir:

```powershell
& '.\.venv\Scripts\python.exe' --version
& '.\.venv\Scripts\python.exe' -m pip check
```

Bu yöntem, açık PowerShell oturumunda başka bir Conda veya global Python ortamı aktif olsa bile hangi interpreter’ın kullanılacağını netleştirir.

## Conda base ve proje venv farkı

Conda `base`, Conda kurulumunun genel yönetim ortamıdır. `.venv` ise yalnızca bu projeye ait standart Python sanal ortamıdır. İkisi aynı amaçla kullanılmamalıdır. Conda açıkken `.venv` oluşturmak bazen beklenmeyen interpreter seçimine yol açabilir. Önce `CONDA_PREFIX` ve `VIRTUAL_ENV` değişkenlerinin durumunu kontrol edin, sonra proje için seçilen executable ile ilerleyin.

Paketleri global ortama kurmak başka projelerin sürümlerini bozabilir ve “benim bilgisayarımda çalışıyor” sorununu büyütür. Kurulumdan önce `sys.executable` ve pip yolunu doğrulamak bu riski azaltır.

IDE kullanılıyorsa terminalde doğru ortamın seçilmesi yeterli olmayabilir. Editörün Python interpreter ayarı ayrıca proje içindeki `.venv` executable dosyasını göstermelidir. Terminal ile IDE farklı yorumlayıcı kullanıyorsa kod bir yerde çalışırken diğer yerde import hatası verebilir. Tanı koyarken her iki ortamda da executable yolunu karşılaştırın. Ortam klasörünü başka bilgisayara taşımak yerine bağımlılık dosyalarından yeniden oluşturmak daha güvenlidir.

## Ortamdan çıkma

Aktif sanal ortamdan çıkmak için:

```powershell
deactivate
```

Bu komut ortam klasörünü silmez; yalnızca geçerli terminal oturumunun PATH ayarını geri alır. Ortamı yeniden kullanmak için tekrar aktive edin veya tam yorumlayıcı yolunu çağırın.

## Sık sorulan sorular

**`.venv` Git’e eklenmeli mi?** Hayır. Ortam yeniden üretilebilir ve işletim sistemine özgü dosyalar içerir. `.gitignore` içinde tutulmalıdır.

**Aktivasyon komutu çalışmıyorsa ne yapmalıyım?** Önce `.venv\Scripts\python.exe` dosyasının varlığını kontrol edin. Global PowerShell güvenlik ayarlarını değiştirmek yerine yorumlayıcıyı tam yoluyla çalıştırabilirsiniz.

**Doğru ortamda olduğumu nasıl anlarım?** `sys.executable` çıktısı proje içindeki `.venv\Scripts\python.exe` yolunu göstermeli, `python -m pip --version` aynı ortamı işaret etmelidir.
