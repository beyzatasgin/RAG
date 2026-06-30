import numpy as np
from foundry_local_sdk import Configuration, FoundryLocalManager

def cosine_similarity(vec1, vec2):
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def main():
    config = Configuration(app_name="foundry_local_samples")
    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance

    # Embedding modelini indir ve yükle
    model = manager.catalog.get_model("qwen3-embedding-0.6b")
    model.download(lambda p: print(f"\rİndiriliyor: {p:.1f}%", end=""))
    print()
    model.load()
    print("Embedding modeli hazır.\n")

    client = model.get_embedding_client()

    # Test cümleleri
    sentences = [
        "Python programlama dili çok kullanışlıdır.",
        "Python yazılım geliştirmede popüler bir dil.",
        "Bugün hava çok güzel ve güneşli.",
        "Yapay zeka ve makine öğrenmesi geleceği şekillendiriyor.",
    ]

    print("Embedding'ler üretiliyor...")
    embeddings = []
    for s in sentences:
        result = client.generate_embedding(s)
        embeddings.append(result.data[0].embedding)
        print(f"  ✓ '{s[:40]}...' → {len(result.data[0].embedding)} boyutlu vektör")

    # Sorgu
    query = "Python ile kod yazmayı seviyorum."
    print(f"\nSorgu: '{query}'")
    query_result = client.generate_embedding(query)
    query_vec = query_result.data[0].embedding

    # Benzerlik hesapla
    print("\nBenzerlik skorları:")
    scores = []
    for i, s in enumerate(sentences):
        score = cosine_similarity(query_vec, embeddings[i])
        scores.append((score, s))
        print(f"  {score:.4f} → '{s}'")

    best = max(scores, key=lambda x: x[0])
    print(f"\nEn benzer cümle: '{best[1]}' (skor: {best[0]:.4f})")

    model.unload()

if __name__ == "__main__":
    main()