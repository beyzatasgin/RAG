from foundry_local_sdk import Configuration, FoundryLocalManager
from retrieval import get_top_chunks

def main():
    print("Yerel RAG Asistanı başlatılıyor...\n")

    config = Configuration(app_name="foundry_local_samples")
    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance

    # Embedding modeli
    emb_model = manager.catalog.get_model("qwen3-embedding-0.6b")
    emb_model.download(lambda p: print(f"\rEmbedding modeli indiriliyor: {p:.1f}%", end=""))
    print()
    emb_model.load()
    emb_client = emb_model.get_embedding_client()
    print("✓ Embedding modeli hazır.\n")

    # Soru-cevap döngüsü
    print("Sorunuzu yazın (çıkmak için 'q'):\n")
    while True:
        query = input("Soru: ").strip()
        if query.lower() == "q":
            break
        if not query:
            continue

        results = get_top_chunks(query, emb_client, top_k=3)
        print("\nİlgili bilgiler:")
        for i, (score, source, content) in enumerate(results):
            print(f"  [{i+1}] ({score:.4f}) [{source}]\n       {content}\n")

    emb_model.unload()
    print("Çıkılıyor...")

if __name__ == "__main__":
    main()