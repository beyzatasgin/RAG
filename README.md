# Yerel RAG Asistanı — Microsoft Foundry Local

Microsoft Foundry Local kullanarak tamamen çevrimdışı çalışan bir belge soru-cevap asistanı. Bu proje, RAG (Retrieval-Augmented Generation) mimarisiyle yerel bir LLM'i birleştirerek internet bağlantısı gerektirmeden dokümanlara dayalı cevaplar üretmeyi hedefler.

## Proje Mimarisi

Kullanıcı Sorusu → Sorgu Embedding'i (Foundry Local) → Cosine Similarity → SQLite'tan En Yakın Chunk'lar → Augmented Prompt → Yerel LLM (Foundry Local) → Cevap

## Kullanılan Teknolojiler

- Microsoft Foundry Local SDK — çevrimdışı LLM ve embedding modeli çalıştırma
- Python 3.13 — ana geliştirme dili
- SQLite — doküman chunk'larını ve embedding vektörlerini saklama
- NumPy — cosine similarity hesabı

## Kurulum

pip install foundry-local-sdk-winml openai numpy

## Dosya Yapısı

foundry-rag-project/
├── main.py              # Uygulamanın ana giriş noktası
├── ingest.py            # Dokümanları chunk'layıp SQLite'a kaydeder (2. hafta)
├── retrieval.py         # Benzerlik araması yapar (2. hafta)
├── embedding_test.py    # Embedding ve cosine similarity deneyi
├── sqlite_test.py       # SQLite tablo oluşturma ve CRUD testi
├── data/                # Dokümanların konulacağı klasör
└── requirements.txt     # Bağımlılıklar
