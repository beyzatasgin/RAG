# GitHub iş akışı ve temel sorunlar

## Amaç

Bu belge, yerel Git repository’si ile GitHub üzerindeki uzak repository arasındaki ilişkiyi ve temel ekip akışını açıklar. Git sürüm kontrol aracıdır; GitHub ise Git repository’lerini barındıran ve pull request gibi iş birliği özellikleri sunan bir hizmettir.

## Clone ve remote

`clone`, uzak repository’nin commit geçmişini ve çalışma dosyalarını yeni bir yerel
klasöre alır. Aşağıdaki `REPOSITORY_ADRESI` değeri gerçek repository URL’siyle
değiştirilmelidir:

```powershell
git clone 'REPOSITORY_ADRESI'
```

Repository adresi projeye göre değişir; kişisel kimlik doğrulama bilgileri komuta veya dokümana eklenmemelidir. Mevcut repository’nin remote kayıtlarını salt okunur görmek için:

```powershell
git remote -v
```

Yaygın remote adı `origin` olsa da bu zorunlu değildir. Fetch ve push adreslerinin beklenen repository’yi gösterdiğini doğrulayın.

## Fetch, pull ve push

`fetch`, uzak commit ve branch bilgilerini indirir fakat çalışma branch’inizi otomatik birleştirmez:

```powershell
git fetch origin
```

Bu işlem ağ gerektirir. Ardından yerel branch ile uzak takip branch’i karşılaştırılabilir. `pull`, genel olarak fetch sonrasında uzak değişiklikleri geçerli branch’e entegre eder. Çalışma ağacı kirliyken veya entegrasyon yöntemi anlaşılmadan pull yapmak conflict çözümünü zorlaştırabilir.

`push`, yerel commitleri uzak repository’ye gönderir:

```powershell
git push -u origin feat/example
```

`-u`, yerel branch ile uzak branch arasında upstream ilişkisi kurar. Sonraki `git status` çıktısı ahead/behind durumunu gösterebilir. Push, dosyaların güncel çalışma hâlini değil, oluşturulmuş commitleri gönderir.

## Pull request akışı

Tipik ekip akışı şu şekildedir:

1. Güncel ana branch üzerinden feature branch oluşturulur.
2. Küçük ve doğrulanmış commitler hazırlanır.
3. Feature branch uzak repository’ye push edilir.
4. GitHub üzerinde ana branch’e yönelik pull request açılır.
5. Kod incelemesi ve otomatik kontroller tamamlanır.
6. Onaylanan değişiklikler repository politikasına göre merge edilir.

Pull request bir Git komutu değil, değişikliğin tartışılması ve birleştirilmesi için GitHub iş akışıdır.

## Push rejected ve upstream sorunları

Push reddedilmesinin yaygın nedeni uzak branch’in yerel branch’te bulunmayan yeni commitler içermesidir. Önce `git fetch`, sonra branch farkı ve ekip politikası incelenmelidir. Yanlış remote, korumalı branch veya eksik yetki de reddedilmeye yol açabilir. Sorunu görmeden geçmişi zorla değiştiren bir yöntem kullanılmamalıdır.

Upstream bulunmadığında `git status` uzak karşılaştırma göstermez. `git branch -vv` branch’lerin takip ilişkisini salt okunur biçimde gösterir. İlk push sırasında doğru remote ve branch adıyla `-u` kullanmak bu ilişkiyi kurabilir.

## Merge conflict kavramı

Conflict, yerel ve uzak değişikliklerin aynı satırlar veya dosya işlemleri için farklı sonuçlar istemesidir. Önce etkilenen dosyalar incelenmeli, doğru içerik bilinçli biçimde seçilmeli ve ilgili testler çalıştırılmalıdır. Başka kullanıcıya ait değişiklikler tahminle silinmemelidir.

Kimlik doğrulama bilgileri `.env`, kaynak kodu, remote adresi veya commit mesajında paylaşılmamalıdır. Yanlışlıkla eklenen gizli bir değeri yalnızca son dosyadan silmek geçmişteki kopyayı ortadan kaldırmayabilir; bu durumda repository yöneticisinin güvenlik süreci izlenmelidir.

## Sık sorulan sorular

**GitHub olmadan Git kullanılabilir mi?** Evet. Yerel commit, branch ve diff işlemleri GitHub’dan bağımsızdır.

**`fetch` dosyalarımı değiştirir mi?** Uzak referansları günceller; geçerli çalışma branch’ini doğrudan birleştirmez.

**Push neden ana branch’e kabul edilmiyor?** Branch koruması doğrudan push yerine pull request ve kontroller gerektiriyor olabilir.

**Upstream’i nasıl görürüm?** `git branch -vv` veya `git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}'` kullanılabilir.
