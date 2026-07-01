# Yerel RAG Asistanı — Microsoft Foundry Local

Microsoft Foundry Local kullanarak tamamen çevrimdışı çalışan bir belge soru-cevap asistanı. Bu proje, RAG (Retrieval-Augmented Generation) mimarisiyle yerel bir LLM'i birleştirerek internet bağlantısı gerektirmeden dokümanlara dayalı cevaplar üretmeyi hedefler.

## Proje Mimarisi

Kullanıcı Sorusu → Sorgu Embedding'i (qwen3-embedding-0.6b) → Hibrit Arama (%70 Semantic + %30 Keyword) → SQLite'tan En Yakın Chunk'lar → Augmented Prompt → Yerel LLM (3. hafta) → Cevap

## Kullanılan Teknolojiler

- **Microsoft Foundry Local SDK (WinML)** — çevrimdışı LLM ve embedding modeli çalıştırma
- **qwen3-embedding-0.6b** — metin embedding modeli
- **Python 3.13** — ana geliştirme dili
- **SQLite** — doküman chunk'larını ve embedding vektörlerini saklama
- **NumPy** — cosine similarity hesabı

## Kurulum

pip install foundry-local-sdk-winml openai numpy

## Dosya Yapısı

foundry-rag-project/
├── main.py              # Uygulamanın ana giriş noktası, soru-cevap döngüsü
├── ingest.py            # Dokümanları chunk'layıp embed eder, SQLite'a kaydeder
├── retrieval.py         # Hibrit benzerlik araması (semantic + keyword)
├── embedding_test.py    # Embedding ve cosine similarity deneyi (1. hafta)
├── sqlite_test.py       # SQLite tablo oluşturma ve CRUD testi (1. hafta)
├── app.py               # İlk Foundry Local model testi (1. hafta)
├── data/                # Knowledge base dokümanları (tenis)
│   ├── tenis_temelleri.txt
│   ├── grand_slam.txt
│   ├── efsane_oyuncular.txt
│   ├── tenis_kurallari.txt
│   └── tenis_teknikleri.txt
└── requirements.txt     # Bağımlılıklar

## Kullanım

python ingest.py   # Önce dokümanları işle ve veritabanına kaydet
python main.py     # Soru-cevap arayüzünü başlat

