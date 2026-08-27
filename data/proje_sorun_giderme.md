# Proje sorunlarını güvenli sırayla giderme

## Amaç

Bu belge, yerel RAG projesinde sorun çıktığında rastgele değişiklik yapmak yerine izlenebilir bir kontrol sırası sunar. Ayrıntılı kurulum ve kavramlar diğer destek belgelerinde bulunur; burada amaç doğru kanıtı toplayıp hangi aşamada durulacağını belirlemektir.

## 1. Repository ve ortamı doğrula

Önce doğru klasör, branch ve çalışma ağacı kontrol edilir:

```powershell
Get-Location
git branch --show-current
git status --short --branch
Test-Path .git\index.lock
```

Beklenmeyen kullanıcı değişiklikleri veya index lock varsa otomatik düzeltme yapmayın. Git adımları için `git_temelleri_ve_branchler.md` belgesine bakın.

Ardından gerçek Python executable yolunu doğrulayın:

```powershell
& '.\.venv\Scripts\python.exe' -c "import sys; print(sys.executable)"
```

Yanlış interpreter veya aktif olmayan venv, `ModuleNotFoundError` hatasının yaygın nedenidir. Ortam oluşturma ve seçim için `python_kurulum_ve_venv.md` kullanılmalıdır.

## 2. Paket tutarlılığını kontrol et

Paketleri yeniden kurmadan önce mevcut durumu okuyun:

```powershell
& '.\.venv\Scripts\python.exe' -m pip check
& '.\.venv\Scripts\python.exe' -m pip list
```

Eksik modülün aynı `.venv` içinde bulunup bulunmadığını `pip show` ile kontrol edin. Sürüm veya interpreter uyuşmazlığı için `pip_ve_requirements.md` belgesindeki sırayı izleyin. Paket kurmak ağ ve disk kullanabilir; teşhis ile kurulumu ayrı adımlar olarak ele alın.

## 3. Belirtiyi doğru belgeye yönlendir

Ayrıntılı teknik açıklamayı burada tekrarlamak yerine önce belirtiyi sınıflandırın. İlk
kontrol yalnızca kanıt toplamalı; dosya silme, süreç sonlandırma, indirme veya DB yazma
işlemi başlatmamalıdır.

| Belirti | İlk güvenli kontrol | Ayrıntılı belge |
| --- | --- | --- |
| `ModuleNotFoundError` | Aktif interpreter ve venv yolunu kontrol et | `python_kurulum_ve_venv.md`, `pip_ve_requirements.md` |
| Paket uyumsuzluğu | Proje yorumlayıcısıyla `python -m pip check` çalıştır | `pip_ve_requirements.md` |
| `database is locked` | Yazma yapan süreç ve açık bağlantıları belirle | `sqlite_temelleri_ve_hatalar.md` |
| Model cache içinde değil | Alias, cache yolu ve download iznini kontrol et | `foundry_local_offline_kullanim.md` |
| Belge indekslenmemiş | Kaynak dizini, UTF-8 ve ingestion özetini kontrol et | `rag_sistemi_nasil_calisir.md` |
| Yanlış retrieval sonucu | Sorgu, `top_k`, `min_score` ve kaynak kapsamını kontrol et | `rag_sistemi_nasil_calisir.md` |
| Streamlit başlamıyor | Aktif ortamı, paketi ve port kullanımını kontrol et | Bu belgedeki UI bölümü |
| Disk veya RAM yetersiz | İşlemi durdur ve kapasiteyi ölç | `foundry_local_offline_kullanim.md` |

Ölçüm beklenmeyen DB boyutu veya hash değişimi, bütünlük sorunu ya da belirsiz aktif
yazma süreci gösterirse işlemi durdurun. Önce geri alma kaynağını ve yedek hedefini
belirleyin; ancak bundan sonra kapsamı açık ve kullanıcı tarafından onaylanmış işlem
planı hazırlayın. Runtime DB üzerinde deneme amaçlı elle SQL çalıştırmayın ve sahibi
bilinmeyen süreçleri otomatik sonlandırmayın.

## 4. Streamlit başlangıç sorunları

Streamlit başlamıyorsa doğru `.venv`, kurulu sürüm, terminal hata çıktısı ve kullanılan port incelenir. Portu başka süreç kullanıyorsa önce süreç sahibi belirlenir; bilinmeyen süreç kapatılmaz. UI açılıyor fakat cevap üretmiyorsa DB, model cache ve runtime hataları ayrı ayrı değerlendirilmelidir.

## Sık sorulan sorular

**İlk kontrol ne olmalı?** Doğru klasör, temiz Git durumu ve doğru Python executable yolu.

**Ne zaman durup yedek almalıyım?** DB integrity hatası, beklenmeyen hash/boyut değişimi, kapsam dışı dosya değişikliği veya belirsiz aktif yazma süreci görüldüğünde.

**Her hatada paketleri yeniden kurmalı mıyım?** Hayır. Önce interpreter, `pip check` ve paket konumunu doğrulayın.

**Model bulunamadığında indirmeyi açmalı mıyım?** Yalnızca ağ, disk ve cache hedefi açıkça onaylanan ayrı hazırlık adımında.
