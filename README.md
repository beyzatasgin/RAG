# 🎾 Yerel RAG Asistanı — Microsoft Foundry Local

Microsoft Foundry Local kullanarak tamamen çevrimdışı çalışan bir tenis bilgi asistanı. RAG (Retrieval-Augmented Generation) mimarisiyle yerel bir LLM'i birleştirerek internet bağlantısı gerektirmeden dokümanlara dayalı cevaplar üretiyor.

<img width="844" height="574" alt="image" src="https://github.com/user-attachments/assets/3f64129d-ae16-4e88-ba3e-a56c29098239" />
<img width="914" height="418" alt="image" src="https://github.com/user-attachments/assets/43bdf5f5-b32d-4311-b073-e7e3f4e6194f" />

---

##  RAG Nedir?

RAG (Retrieval-Augmented Generation), büyük dil modellerini harici bilgi kaynaklarıyla zenginleştiren bir mimaridir. Genel bir LLM'e özel bir soru sorulduğunda model ya yanlış cevap verir ya da bilgi uydurmaya çalışır (hallucination). RAG bu problemi üç adımla çözer:

1. **Retrieve** — Kullanıcı sorusuna en alakalı doküman parçalarını bul
2. **Augment** — Bu parçaları modele bağlam olarak ekle
3. **Generate** — Model bağlamı kullanarak doğru cevabı üretsin

Bu projede tüm bu işlemler internet bağlantısı olmadan, yerel makinede çalışır.

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
Augmented Prompt → Yerel LLM (qwen3-1.7b, Foundry Local)
↓
Kaynak Gösterimli Cevap

### Hibrit Arama Neden?
Sadece semantic (embedding) araması kısa sorgularda yetersiz kalabiliyor. Örneğin "teniste vuruşlar" gibi kısa bir sorguda embedding tek başına doğru chunk'ları getiremiyor. Bu yüzden keyword eşleşmesini de (Türkçe çekim ekleri için stem matching dahil) %30 ağırlıkla birleştirdik.

---

##  Kullanılan Teknolojiler

| Teknoloji | Kullanım Amacı |
|-----------|---------------|
| Microsoft Foundry Local SDK (WinML) | Çevrimdışı LLM ve embedding modeli çalıştırma |
| qwen3-embedding-0.6b | Metin embedding modeli (1024 boyutlu vektör) |
| qwen3-1.7b | Soru-cevap için yerel chat modeli |
| Streamlit | Web tabanlı sohbet arayüzü |
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
pip install foundry-local-sdk-winml openai numpy streamlit
```

---
## Dosya Yapısı

```
foundry-rag-project/
├── app_ui.py            # Streamlit web arayüzü (ana uygulama)
├── main.py              # CLI tabanlı soru-cevap döngüsü
├── ingest.py            # Dokümanları chunk'layıp embed eder, SQLite'a kaydeder
├── retrieval.py         # Hibrit benzerlik araması (semantic + keyword)
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
└── requirements.txt     # Bağımlılıklar
---

##  Kullanım

### 1. Dokümanları işle ve veritabanına kaydet
```bash
python ingest.py
```
Bu komut `data/` klasöründeki tüm `.txt` dosyalarını okur, chunk'lara böler, embedding üretir ve `documents.db`'ye kaydeder.

### 2. Web arayüzünü başlat
```bash
streamlit run app_ui.py
```
Tarayıcıda `http://localhost:8501` adresinde sohbet arayüzü açılır.

### 3. CLI arayüzü (alternatif)
```bash
python main.py
```

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

