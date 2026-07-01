import sqlite3
import json
import numpy as np
from foundry_local_sdk import Configuration, FoundryLocalManager

def cosine_similarity(vec1, vec2):
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def get_manager():
    config = Configuration(app_name="foundry_local_samples")
    FoundryLocalManager.initialize(config)
    return FoundryLocalManager.instance

def keyword_score(query, content):
    """Sorgudaki kelimelerin içerikte geçme oranını hesaplar."""
    query_words = set(query.lower().split())
    content_lower = content.lower()
    matches = sum(1 for word in query_words if word in content_lower)
    return matches / len(query_words) if query_words else 0

def get_top_chunks(query, client, top_k=3):
    # Sorguyu embed et
    result = client.generate_embedding(query)
    query_vec = result.data[0].embedding

    # SQLite'tan tüm chunk'ları çek
    conn = sqlite3.connect("documents.db")
    cursor = conn.cursor()
    rows = cursor.execute(
        "SELECT id, source, content, embedding FROM documents"
    ).fetchall()
    conn.close()

    # Hibrit skor: %70 semantic + %30 keyword
    scored = []
    for row in rows:
        doc_id, source, content, embedding_json = row
        doc_vec = json.loads(embedding_json)
        semantic = cosine_similarity(query_vec, doc_vec)
        keyword = keyword_score(query, content)
        hybrid = 0.7 * semantic + 0.3 * keyword
        scored.append((hybrid, source, content))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]

def main():
    print("=== Retrieval Testi ===\n")

    manager = get_manager()
    model = manager.catalog.get_model("qwen3-embedding-0.6b")
    model.download(lambda p: print(f"\rModel indiriliyor: {p:.1f}%", end=""))
    print()
    model.load()
    client = model.get_embedding_client()
    print("✓ Embedding modeli hazır.\n")

    queries = [
        "Wimbledon hangi zeminde oynanır?",
        "Forehand ve backhand nedir?",
        "Djokovic kaç Grand Slam kazandı?",
        "Deuce kuralı nedir?",
        "teniste vuruşlar",
    ]

    for query in queries:
        print(f"Sorgu: '{query}'")
        results = get_top_chunks(query, client, top_k=2)
        for i, (score, source, content) in enumerate(results):
            print(f"  [{i+1}] ({score:.4f}) [{source}] {content[:70]}...")
        print()

    model.unload()

if __name__ == "__main__":
    main()
