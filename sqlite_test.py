import sqlite3
import json

# Veritabanı bağlantısı kur (dosya yoksa otomatik oluşturur)
conn = sqlite3.connect("documents.db")
cursor = conn.cursor()

# Tablo oluştur
cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        source  TEXT,
        embedding TEXT
    )
""")
conn.commit()
print("✓ Tablo oluşturuldu.")

# Örnek veriler ekle (embedding'i şimdilik boş bırakıyoruz, 2. haftada dolduracağız)
sample_docs = [
    ("Python, nesne yönelimli bir programlama dilidir.", "python_notlari.txt"),
    ("RAG, retrieval ve generation adımlarını birleştirir.", "rag_ozet.txt"),
    ("SQLite, sunucusuz çalışan hafif bir veritabanıdır.", "sqlite_notlari.txt"),
]

cursor.executemany(
    "INSERT INTO documents (content, source, embedding) VALUES (?, ?, ?)",
    [(content, source, None) for content, source in sample_docs]
)
conn.commit()
print(f"✓ {len(sample_docs)} satır eklendi.")

# Verileri geri oku
print("\nKayıtlar:")
for row in cursor.execute("SELECT id, source, content FROM documents"):
    print(f"  [{row[0]}] {row[1]} → {row[2]}")

# Belirli bir kaydı sorgula
print("\nİD'si 2 olan kayıt:")
row = cursor.execute("SELECT * FROM documents WHERE id = 2").fetchone()
print(f"  id={row[0]}, source={row[2]}, content={row[1]}")

conn.close()
print("\n✓ Bağlantı kapatıldı.")