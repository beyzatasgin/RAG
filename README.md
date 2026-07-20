# Yerel RAG Asistanı — Microsoft Foundry Local

Microsoft Foundry Local kullanarak tamamen çevrimdışı çalışan bir tenis bilgi asistanı. RAG (Retrieval-Augmented Generation) mimarisiyle yerel bir LLM'i birleştirerek internet bağlantısı gerektirmeden dokümanlara dayalı cevaplar üretiyor.

<img width="844" height="574" alt="image" src="https://github.com/user-attachments/assets/3f64129d-ae16-4e88-ba3e-a56c29098239" />

<img width="914" height="418" alt="image" src="https://github.com/user-attachments/assets/43bdf5f5-b32d-4311-b073-e7e3f4e6194f" />


## Proje Mimarisi

Kullanıcı Sorusu → Sorgu Embedding'i (qwen3-embedding-0.6b) → Hibrit Arama (%70 Semantic + %30 Keyword) → SQLite'tan En Yakın Chunk'lar → Augmented Prompt → Yerel LLM (qwen3-1.7b) → Cevap

## Kullanılan Teknolojiler

- **Microsoft Foundry Local SDK (WinML)** — çevrimdışı LLM ve embedding modeli çalıştırma
- **qwen3-embedding-0.6b** — metin embedding modeli
- **qwen3-1.7b** — soru-cevap için yerel chat modeli
- **Streamlit** — web tabanlı sohbet arayüzü
- **SQLite** — doküman chunk'larını ve embedding vektörlerini saklama
- **NumPy** — cosine similarity hesabı
- **Python 3.13** — ana geliştirme dili

## Kurulum

pip install foundry-local-sdk-winml openai numpy streamlit


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
```


# Kullanım

## 1. Dokümanları işle ve veritabanına kaydet
python ingest.py

## 2. Web arayüzünü başlat
streamlit run app_ui.py

## veya CLI arayüzünü başlat
python main.py


## Geliştirici

**Beyza Taşgın** — Sakarya Üniversitesi Bilgisayar Mühendisliği
Microsoft Staj Projesi — Yaz 2026

