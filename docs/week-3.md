# Hafta 3 — Grounded ve kaynaklı yerel RAG

## Retrieve → Augment → Generate

`main.py`, kullanıcı sorusunu önce yerel embedding modeline gönderir. Week 2
`Retriever` servisi SQLite içindeki chunk'ları semantic/keyword skorlarıyla sıralar.
`prompt_builder.py` yalnızca bütçeye sığan sonuçları bağlama ekler ve Foundry Local
chat modeli bu bağlamdan cevap üretir. Bulut API'si veya API anahtarı kullanılmaz.

## Grounding ve kaynak doğrulaması

Sistem promptu modele yalnızca sağlanan belge bağlamını kullanmasını, tahmin
yürütmemesini ve bilgi yoksa `Belgelerde bu bilgi bulunamadı.` demesini söyler.
Belgelerdeki talimatlar veri olarak sınırlandırılır. Context bölümleri `[K1]`,
`[K2]` şeklinde etiketlenir; dosya adı ve chunk index içerir.

Model metnindeki citation'lar güven kaynağı değildir. `citations.py` onları izinli
etiketlerle karşılaştırır. Kullanıcıya gösterilen “Kullanılan kaynaklar” listesi
model metninden değil, prompta gerçekten giren retrieval metadata'sından üretilir.
Model inline citation üretmezse uygulama bunu ayrıca bildirir; model cevabını
değiştirmez veya otomatik `[K1]` eklemez. Bu yaklaşım hallucination riskini azaltır
fakat tamamen ortadan kaldırmaz.

## Prompt bütçesi ve injection farkındalığı

Varsayılan context bütçesi 7000 karakterdir. Retrieval sırası korunur; sığmayan
chunk atlanır, ilk chunk gerekirse etiketi korunarak kısaltılır. Kullanıcı sorusu
ve belgeler statik sistem talimatına eklenmez; ayrı kullanıcı mesajında işaretli
veri bloklarında taşınır. Bu bir savunma katmanıdır, mutlak güvenlik garantisi
değildir.

## Runtime ve bellek yaklaşımı

Yaklaşık 8 GiB RAM için embedding ve chat modelleri aynı anda bellekte tutulmaz.
Bir soruda retrieval, embedding runtime kapanmadan tamamlanır; cleanup sonrasında
ayrı chat runtime açılır. Sonuç yoksa chat runtime hiç açılmaz. Download varsayılan
olarak kapalıdır. Bu seçim daha düşük tepe bellek karşılığında interaktif sorular
arasında model yükleme süresini artırabilir.

SDK 1.2.4 streaming çağrısı doğrulanmış mesaj şekliyle kullanılır. Üretim sınırları
istemcinin desteklediği `settings.max_tokens` ve `settings.temperature` alanlarından
uygulanır; desteklenmeyen çağrı parametresi eklenmez.

## CLI

```powershell
& '.\.venv\Scripts\python.exe' main.py `
  --db-path 'runtime_data\rag.db' `
  --question 'Grand Slam turnuvaları hangileridir?' `
  --top-k 3 --min-score 0.2 `
  --model-cache-dir 'C:\Users\Beyza\.foundry_local_samples\cache\models' `
  --app-data-dir 'C:\Users\Beyza\.local-rag-assistant' `
  --logs-dir 'C:\Users\Beyza\.local-rag-assistant\logs' `
  --debug
```

`--question` olmadan interaktif mod açılır; `çık`, `exit`, `quit`, Ctrl+C veya EOF
temiz kapanır. `--allow-download` yalnızca açıkça verildiğinde cache eksiği için
indirmeye izin verir.

## Test yaklaşımı ve sınırlamalar

Unit testler fake retriever/chat client kullanır; SDK initialize etmez, model
yüklemez ve ağ kullanmaz. Prompt sırası/bütçesi, no-result kısa devresi, reasoning
temizliği, source deduplication, citation doğrulama ve CLI hata yolları test edilir.

Full-scan vector search küçük eğitim veri seti içindir. Kaynakların gösterilmesi
model cevabının doğru olduğunu garanti etmez. Küçük yerel model doğru belgeler
getirilse bile ayrıntıları yanlış eşleyebilir ve her cevapta inline citation
üretmeyebilir. Kullanıcı cevabı “Kullanılan kaynaklar” bölümündeki metinlerle kontrol
etmelidir. Streamlit/web UI Hafta 4 kapsamıdır.

Doğrulanmış gerçek smoke sırasında retrieval ve generation uçtan uca çalışmış,
`grand_slam.txt` doğru kaynak olarak gösterilmiş ve reasoning kullanıcıdan ayrılmıştır.
Bununla birlikte model Australian Open ayrıntısını yanlış eşlemiş ve geçerli inline
citation üretmemiştir. Bu sonuç Week 3'ün belgelenmiş model sınırlamasıdır. Daha büyük
bir model, answer validation ve ikinci-pass verification olası sonraki geliştirmelerdir.

Week 3 kabul tanımı model doğruluğu garantisi değildir: offline embedding/chat
pipeline'ı çalışır, doğrulanmış retrieval kaynakları gösterilir, no-result kısa
devresi chat çağrısını önler ve model sınırlamaları kullanıcıya açıkça bildirilir.

## Öğrenme çıktıları

- Retrieval sonucunu güvenli ve sınırlı bir prompta dönüştürmek
- Model citation'ı ile doğrulanmış uygulama metadata'sını ayırmak
- Yetersiz bağlamı generation çağrısı yapmadan yönetmek
- Yerel model yaşam döngüsünü düşük bellek için aşamalandırmak
- Gerçek modeli fake'lerle hızlı ve yan etkisiz test etmek
