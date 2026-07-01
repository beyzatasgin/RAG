import sqlite3
import json
import os
from foundry_local_sdk import Configuration, FoundryLocalManager

def get_manager():
    config = Configuration(app_name="foundry_local_samples")
    FoundryLocalManager.initialize(config)
    return FoundryLocalManager.instance

def load_documents(data_folder="data"):
    docs = []
    for filename in os.listdir(data_folder):
        if filename.endswith(".txt"):
            filepath = os.path.join(data_folder, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            docs.append((filename, content))
    return docs

def chunk_document(filename, content):
    chunks = []
    paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
    for i, paragraph in enumerate(paragraphs):
        chunks.append({
            "source": filename,
            "chunk_id": i,
            "content": paragraph
        })
    return chunks

def setup_database():
    conn = sqlite3.connect("documents.db")
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS documents")
    cursor.execute("""
        CREATE TABLE documents (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            source    TEXT,
            chunk_id  INTEGER,
            content   TEXT,
            embedding TEXT
        )
    """)
    conn.commit()
    return conn, cursor

def main():
    print("=== Doküman Ingestion Başlıyor ===\n")

    # Model başlat
    manager = get_manager()
    model = manager.catalog.get_model("qwen3-embedding-0.6b")
    model.download(lambda p: print(f"\rModel indiriliyor: {p:.1f}%", end=""))
    print()
    model.load()
    client = model.get_embedding_client()
    print("✓ Embedding modeli hazır.\n")

    # Veritabanını hazırla
    conn, cursor = setup_database()
    print("✓ Veritabanı hazırlandı.\n")

    # Dokümanları yükle ve chunk'la
    docs = load_documents("data")
    all_chunks = []
    for filename, content in docs:
        chunks = chunk_document(filename, content)
        all_chunks.extend(chunks)
        print(f"✓ {filename} → {len(chunks)} chunk")

    print(f"\nToplam {len(all_chunks)} chunk embedding'e gönderilecek.\n")

    # Embedding üret ve SQLite'a kaydet
    for i, chunk in enumerate(all_chunks):
        result = client.generate_embedding(chunk["content"])
        embedding_vector = result.data[0].embedding
        embedding_json = json.dumps(embedding_vector)

        cursor.execute(
            "INSERT INTO documents (source, chunk_id, content, embedding) VALUES (?, ?, ?, ?)",
            (chunk["source"], chunk["chunk_id"], chunk["content"], embedding_json)
        )
        print(f"  [{i+1}/{len(all_chunks)}] '{chunk['content'][:50]}...' kaydedildi.")

    conn.commit()
    conn.close()
    model.unload()

    print(f"\n✓ Tüm chunk'lar veritabanına kaydedildi.")
    print("✓ documents.db güncellendi.")

if __name__ == "__main__":
    main()