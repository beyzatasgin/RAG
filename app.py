from foundry_local_sdk import Configuration, FoundryLocalManager

def main():
    config = Configuration(app_name="foundry_local_samples")
    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance

    # Donanım hızlandırma sağlayıcılarını indir ve kaydet
    manager.download_and_register_eps(progress_callback=lambda ep, p: print(f"\r{ep}: {p:.1f}%", end=""))
    print()

    # Küçük bir modeli seç ve indir
    model = manager.catalog.get_model("qwen2.5-0.5b")
    model.download(lambda p: print(f"\rİndiriliyor: {p:.2f}%", end=""))
    print()
    model.load()
    print("Model yüklendi ve hazır.")

    client = model.get_chat_client()
    messages = [{"role": "user", "content": "Altın oran nedir?"}]

    print("Asistan: ", end="", flush=True)
    for chunk in client.complete_streaming_chat(messages):
        if chunk.choices and chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print()

    model.unload()

if __name__ == "__main__":
    main()