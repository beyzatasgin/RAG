# RAG sistemi nasıl çalışır?

## Amaç

Bu belge, projenin belge yüklemeden kaynaklı cevap üretimine kadar gerçek RAG akışını başlangıç seviyesinde açıklar. RAG, dil modelinin cevabını proje belgelerinden getirilen bağlamla destekler; modelin yeniden eğitilmesi değildir.

## Belge keşfi ve chunking

Ingestion işlemi seçilen dizindeki UTF-8 `.txt` ve `.md` dosyalarını deterministik sırayla keşfeder. Her dosyanın byte içeriğinden SHA-256 hesaplanır. Aynı kaynak ve aynı hash daha önce işlendiğinde gereksiz embedding üretimi atlanabilir.

Uzun metin tek parça hâlinde modele verilmez. `chunking.py`, varsayılan olarak en fazla 800 karakterlik ve 100 karakter overlap içeren parçalar üretir. Algoritma mümkün olduğunda paragraf ve kelime sınırlarını tercih eder. Overlap, parça sınırında kalan bağlamın tamamen kaybolmasını azaltır; fazla overlap ise DB boyutunu ve tekrarları artırır.

## Embedding ve SQLite storage

Her chunk yerel embedding modeli `qwen3-embedding-0.6b` ile sayısal bir vektöre dönüştürülür. Embedding, metinlerin anlamsal yakınlığını karşılaştırmak için kullanılır; insan tarafından okunabilir bir özet değildir.

Normalize SQLite şemasında kaynak belge metadata’sı, chunk içerikleri ve embedding vektörleri ilişkili tablolarda saklanır. Model alias’ı ve vektör boyutu da kaydedilir. Sorgu modeliyle saklanan embedding modeli veya boyutu uyuşmazsa karşılaştırma reddedilir. Böylece anlamsız skorların sessizce kullanılması önlenir.

## Semantic ve keyword retrieval

Kullanıcı sorusu aynı embedding modeliyle vektöre dönüştürülür. Retriever, soru vektörü ile saklanan chunk vektörleri arasında cosine similarity hesaplar. Küçük eğitim veri setinde vektörler NumPy ile bellekte tam taranır.

Semantic skor tek başına kullanılmaz. Proje, soru kelimelerinin içerikte bulunmasını ölçen keyword skoruyla hybrid sonuç üretir:

```text
combined = %70 semantic + %30 keyword
```

Sonuçlar combined skora göre sıralanır; `top_k` sonuç sayısını, `min_score` kabul eşiğini belirler. Eşitliklerde kaynak adı ve chunk index’i deterministik sıralama sağlar.

## Grounded prompt ve generation

Seçilen chunk’lar context bütçesine sığacak şekilde `[K1]`, `[K2]` gibi etiketlerle prompta eklenir. Sistem talimatı, yerel chat modelinden yalnızca verilen bağlamı kullanmasını ve kaynak etiketlerini uydurmamasını ister. Chat modeli bu grounded prompt üzerinden cevap üretir.

Model metni güvenilir metadata kaynağı değildir. Uygulamadaki “Kullanılan kaynaklar” listesi model cevabından çıkarılmaz; gerçekten prompta giren retrieval sonuçlarının source ve chunk metadata’sından oluşturulur. Model bilinmeyen bir etiket üretirse bu etiket doğrulanmış kaynak listesine eklenmez.

Hiçbir chunk eşik üzerinde bulunmazsa no-result kısa devresi çalışır. Chat modeli çağrılmaz ve belgelerde bilgi bulunamadığını belirten deterministik cevap döner. Bu davranış, bağlam yokken modelin genel bilgisinden cevap uydurmasını azaltır.

## RAG’in sınırları

RAG hallucination riskini azaltır fakat ortadan kaldırmaz. Küçük yerel model doğru kaynaklar getirilse bile ayrıntıları yanlış eşleyebilir veya inline citation üretmeyebilir. Kullanıcı model cevabını doğrulanmış kaynak metinleriyle kontrol etmelidir. Retrieval kalitesi, generation doğruluğu ve citation doğruluğu ayrı ölçümlerdir.

## Sık sorulan sorular

**RAG modeli eğitir mi?** Hayır. İlgili belge parçalarını çalışma zamanında prompta ekler.

**Kaynak listesi model tarafından mı yazılır?** Hayır. Liste retrieval metadata’sından doğrulanır.

**Semantic arama neden keyword skoruyla birleştirilir?** Anlamsal benzerlik ile açık terim eşleşmesini birlikte değerlendirmek küçük teknik koleksiyonlarda daha açıklanabilir sonuç sağlayabilir.

**Sonuç bulunmazsa ne olur?** Generation çağrısı yapılmadan no-result cevabı döner.
