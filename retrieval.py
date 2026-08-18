import sqlite3
import json
from retrieval_utils import cosine_similarity, hybrid_score, keyword_score

def get_manager():
    from foundry_local_sdk import Configuration, FoundryLocalManager

    config = Configuration(app_name="foundry_local_samples")
    FoundryLocalManager.initialize(config)
    return FoundryLocalManager.instance

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
        hybrid = hybrid_score(semantic, keyword)
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
