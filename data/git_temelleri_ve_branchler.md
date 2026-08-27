# Git temelleri ve branch kullanımı

## Amaç

Bu belge, bir repository içindeki değişiklikleri anlamak, kontrollü stage etmek, commit oluşturmak ve branch’lerle güvenli çalışmak için temel Git akışını açıklar. Örnekler Windows PowerShell üzerinde repository kökünde çalıştırılır.

## Çalışma ağacını anlamak

İlk komut çoğu zaman `git status` olmalıdır:

```powershell
git status --short --branch
```

Bu çıktı aktif branch’i, değiştirilmiş dosyaları, yeni dosyaları ve staged değişiklikleri özetler. “Temiz çalışma ağacı”, takip edilen dosyalarda commit edilmemiş değişiklik bulunmadığı anlamına gelir. Ignore edilen runtime dosyaları kısa çıktıda görünmeyebilir.

Henüz stage edilmemiş içerik farkları için:

```powershell
git diff
git diff --stat
```

Stage edilmiş değişiklikleri görmek için farklı bir komut gerekir:

```powershell
git diff --cached
git diff --cached --name-status
```

## Kontrollü staging ve commit

`git add`, çalışma dosyasının o anki içeriğini bir sonraki commit için index’e alır. Geniş kapsam yerine amaçlanan yolları açıkça belirtmek yanlış dosya ekleme riskini azaltır:

```powershell
git add -- README.md src\example.py
git diff --cached --check
git diff --cached --name-status
```

Kontrol edilen değişiklikler commit edilir:

```powershell
git commit -m "docs: explain local setup"
```

Commit yerel Git geçmişine yazılır. Push ise yerel commitleri uzak repository’ye gönderir. Commit oluşturmak otomatik olarak push yapmaz.

## Branch oluşturma ve geçiş

Yeni işe başlamadan önce çalışma ağacının temiz ve başlangıç branch’inin güncel olduğunu doğrulayın. Yeni branch oluşturup geçmek için:

```powershell
git switch -c feat/example
git branch --show-current
```

Var olan bir branch’e geçmek için `git switch branch-adi` kullanılır. Aynı isimde branch zaten varsa yeniden oluşturma girişiminde bulunmadan önce mevcut branch’in amacı ve commitleri incelenmelidir.

Branch, paralel geliştirme çizgisidir. Merge, bir branch’in commitlerini diğer branch’in geçmişiyle birleştirir. Birleştirmeden önce test sonucu, değişiklik kapsamı ve olası conflict’ler kontrol edilmelidir. Conflict, iki geliştirme çizgisinin aynı içerik üzerinde Git’in otomatik karar veremediği değişiklikler yapmasıdır; çözüm insan incelemesi gerektirir.

Branch’in hangi committen ayrıldığını anlamak için log ve merge-base bilgileri salt okunur incelenebilir. Feature branch’in güncel ana branch’i içerdiği varsayılmamalıdır. Ekip yeni commitler eklediyse entegrasyon biçimi proje politikasına göre seçilmeli ve çalışma ağacı temizken uygulanmalıdır.

## Güvenli dosya geri alma

Henüz commit edilmemiş belirli bir dosya değişikliğini geri almak için hedefi açıkça yazın:

```powershell
git restore --worktree -- path\to\file.py
```

Bu komut yerel değişikliği kaybettirebileceği için önce `git status` ve
`git diff -- path\to\file.py` ile hedef dosyanın içeriğini inceleyin. Belirli bir eski
committeki dosyayı geri getirmek gerekiyorsa kaynak commit açıkça belirtilebilir:

```powershell
git restore --source=COMMIT_SHA -- path\to\file.py
```

`COMMIT_SHA` ve `path\to\file.py` örnek değerlerdir; kullanıcı güvenilir kaynak
commitini ve geri alınacak tekil dosya yolunu açıkça yazmalıdır.

Geniş ve geri döndürülemez görünen işlemler yerine tek dosya veya açık yol kapsamı tercih edilmelidir. Kullanıcıya ait bilinmeyen değişiklikler otomatik düzeltilmemelidir.

## Sık sorulan sorular

**`git diff` neden boş ama status değişiklik gösteriyor?** Değişiklik staged olabilir. `git diff --cached` çıktısını kontrol edin.

**Commit yaptıktan sonra GitHub’da neden görünmüyor?** Commit yereldir; uzak repository’ye aktarılması için ayrıca doğru branch’e push gerekir.

**Temiz çalışma ağacı neden önemlidir?** Branch değiştirme, merge ve kontrollü commit sırasında hangi değişikliğin hangi işe ait olduğunu ayırmayı kolaylaştırır.

**Yanlış dosyayı stage ettim; içeriği silmeden ne yapabilirim?** `git restore --staged -- dosya` ile yalnızca index durumunu geri alabilir, çalışma dosyasını koruyabilirsiniz.
