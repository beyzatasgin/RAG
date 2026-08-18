# 🎾 Yerel RAG Asistanı — Microsoft Foundry Local

Microsoft Foundry Local ile tamamen yerel çalışacak bir tenis bilgi asistanının geliştirme projesi. Mevcut aşama; yerel embedding, SQLite depolama ve hibrit retrieval prototipini içerir. Grounded prompt, yerel LLM ile cevap üretimi ve kaynaklı kullanıcı arayüzü sonraki aşamalarda eklenecektir.

> Aşağıdaki ekran görüntüleri tamamlanması hedeflenen kullanıcı arayüzünü göstermektedir; Streamlit arayüzü henüz bu depoda uygulanmamıştır.

<img width="844" height="574" alt="image" src="https://github.com/user-attachments/assets/3f64129d-ae16-4e88-ba3e-a56c29098239" />
<img width="914" height="418" alt="image" src="https://github.com/user-attachments/assets/43bdf5f5-b32d-4311-b073-e7e3f4e6194f" />

---

##  RAG Nedir?

RAG (Retrieval-Augmented Generation), büyük dil modellerini harici bilgi kaynaklarıyla zenginleştiren bir mimaridir. Genel bir LLM'e özel bir soru sorulduğunda model ya yanlış cevap verir ya da bilgi uydurmaya çalışır (hallucination). RAG bu problemi üç adımla çözer:

1. **Retrieve** — Kullanıcı sorusuna en alakalı doküman parçalarını bul
2. **Augment** — Bu parçaları modele bağlam olarak ekle
3. **Generate** — Model bağlamı kullanarak doğru cevabı üretsin

Bu projede retrieval adımı yerel olarak prototiplenmiştir. Augment ve Generate adımları henüz ana uygulama akışına eklenmemiştir.

---

##  Proje Mimarisi

Kullanıcı Sorusu
↓
Sorgu Embedding'i (qwen3-embedding-0.6b)
↓
Hibrit Arama: %70 Semantic (cosine similarity) + %30 Keyword
↓
SQLite'tan En Yakın 3-5 Chunk
↓
Augmented Prompt → Yerel LLM (sonraki aşama)
↓
Kaynak Gösterimli Cevap (sonraki aşama)

### Hibrit Arama Neden?
Sadece semantic (embedding) araması kısa sorgularda yetersiz kalabiliyor. Örneğin "teniste vuruşlar" gibi kısa bir sorguda embedding tek başına doğru chunk'ları getiremiyor. Bu yüzden basit keyword eşleşmesini de %30 ağırlıkla birleştirdik.

---

##  Kullanılan Teknolojiler

| Teknoloji | Kullanım Amacı |
|-----------|---------------|
| Microsoft Foundry Local SDK (WinML) | Çevrimdışı LLM ve embedding modeli çalıştırma |
| qwen3-embedding-0.6b | Metin embedding modeli (1024 boyutlu vektör) |
| qwen3-1.7b | Sonraki aşamada soru-cevap için hedeflenen yerel chat modeli |
| Streamlit | Sonraki aşamada eklenecek web tabanlı sohbet arayüzü |
| SQLite | Chunk'ları ve embedding vektörlerini saklama |
| NumPy | Cosine similarity hesabı |
| Python 3.13 | Ana geliştirme dili |

---

##  Kurulum

### Gereksinimler
- Windows 10/11
- Python 3.11+
- İnternet bağlantısı (yalnızca ilk model indirme için)

### Adımlar

```bash
# 1. Repoyu klonla
git clone https://github.com/beyzatasgin/RAG.git
cd RAG

# 2. Bağımlılıkları kur
pip install -r requirements.txt

# Yalnızca güvenli otomatik testler için
pip install -r requirements-dev.txt
```

---
## Dosya Yapısı

```
foundry-rag-project/
├── main.py              # CLI tabanlı retrieval döngüsü
├── ingest.py            # Dokümanları chunk'layıp embed eder, SQLite'a kaydeder
├── retrieval.py         # Hibrit benzerlik araması (semantic + keyword)
├── retrieval_utils.py   # Model ve veritabanından bağımsız skor fonksiyonları
├── tests/               # Yan etkisiz otomatik testler
├── embedding_test.py    # Embedding ve cosine similarity deneyi (1. hafta)
├── sqlite_test.py       # SQLite tablo oluşturma ve CRUD testi (1. hafta)
├── app.py               # İlk Foundry Local model testi (1. hafta)
├── documents.db         # Chunk'ların ve embedding vektörlerinin saklandığı SQLite veritabanı
├── data/                # Knowledge base dokümanları (tenis)
│   ├── tenis_temelleri.txt
│   ├── tenis_teknikleri.txt
│   ├── tenis_kurallari.txt
│   ├── grand_slam.txt
│   └── efsane_oyuncular.txt
├── requirements.txt     # Uygulama bağımlılıkları
└── requirements-dev.txt # Otomatik test bağımlılıkları
```
---

##  Kullanım

### 1. Dokümanları işle ve veritabanına kaydet
```bash
python ingest.py
```
Bu komut `data/` klasöründeki tüm `.txt` dosyalarını okur, chunk'lara böler, embedding üretir ve `documents.db`'ye kaydeder.

> **Dikkat:** `ingest.py`, mevcut `documents` tablosunu silip yeniden oluşturur. Mevcut verileri korumak istiyorsanız bu komutu çalıştırmadan önce veritabanını yedekleyin.

### 2. CLI retrieval prototipi
```bash
python main.py
```

Bu komut ilgili doküman parçalarını ve kaynak dosyalarını listeler; henüz LLM cevabı üretmez.

### 3. Güvenli otomatik testler
```powershell
python -m pytest tests -p no:cacheprovider -q
```

Bu testler model başlatmaz, ağ kullanmaz ve `documents.db` dosyasını açmaz. `app.py`, `embedding_test.py`, `retrieval.py`, `ingest.py` ve `sqlite_test.py` ise manuel/model entegrasyon betikleridir; model indirebilir veya kalıcı veriyi değiştirebilir ve otomatik test komutuna dahil değildir.

### 4. Web arayüzü

Streamlit arayüzü henüz uygulanmamıştır. `app_ui.py` ve kaynaklı grounded cevap akışı sonraki geliştirme aşamasının kapsamındadır.

---

##  Knowledge Base

Proje şu an tenis sporuna ait 5 doküman içermektedir:

| Dosya | İçerik |
|-------|--------|
| tenis_temelleri.txt | Tenisin temel kuralları, kort türleri, format bilgisi |
| tenis_teknikleri.txt | Forehand, backhand, servis, vole, topspin, slice gibi vuruş teknikleri |
| tenis_kurallari.txt | Sayım sistemi, deuce, servis kuralları, tiebreak, hawkeye |
| grand_slam.txt | Dört büyük turnuva, zemin bilgileri, Golden Slam |
| efsane_oyuncular.txt | Federer, Nadal, Djokovic, Serena Williams ve diğerleri |

Farklı bir konuya geçmek için `data/` klasöründeki dosyaları değiştirip `ingest.py`'yi yeniden çalıştırmak yeterlidir.

---

##  Geliştirici

**Beyza Taşgın** — Sakarya Üniversitesi Bilgisayar Mühendisliği  
Microsoft Staj Projesi — Yaz 2026  

