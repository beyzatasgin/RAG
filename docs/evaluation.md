# Evaluation

`evaluation/evaluation_cases.json`, tenis belgelerine dayalı answerable,
unanswerable, paraphrase, Türkçe karakter ve prompt-injection benzeri vakalar içerir.

```powershell
python evaluate.py --db-path runtime_data/rag.db --dataset evaluation/evaluation_cases.json --top-k 3 --min-score 0.2 --model-cache-dir '<shared-cache>' --output runtime_data/evaluation-results.json
```

## Metrikler

- Hit Rate / Recall@k: beklenen kaynak ilk k sonuç içinde mi?
- MRR: ilk beklenen kaynağın sırasının tersinin ortalaması
- Unanswerable no-result rate: cevapsız vakalarda boş retrieval oranı
- Source accuracy: vaka düzeyinde beklenen source/no-result başarısı
- Ortalama, p50 ve p95 retrieval latency

Bu metrikler generation kalitesi değildir. `expected_keywords` insan değerlendirme
rubriğine yardımcı olur; otomatik LLM judge kullanılmaz. Citation validity retrieval-only
çalışmada ölçülmez ve `null` raporlanır.

## İnsan değerlendirme rubriği

Her gerçek cevap groundedness, factual consistency, completeness, citation
correctness ve doğru refusal/no-result davranışı açısından kaynak metniyle incelenir.
Küçük modelin Week 3 smoke sırasında bir turnuva ayrıntısını yanlış eşlediği ve inline
citation üretmediği bilinen, gizlenmeyen sınırlamadır.

## Doğrulanmış sonuçlar

20 Ağustos 2026 tarihinde Windows x64, Python 3.13, yaklaşık 8 GiB RAM ve cached
`qwen3-embedding-0.6b` ile `top_k=3`, `min_score=0.2` kullanılarak ölçüldü:

| Metrik | Sonuç |
|---|---:|
| Vaka / answerable | 11 / 9 |
| Hit Rate@3 | 1.0000 |
| MRR | 0.8889 |
| Unanswerable no-result | 0.0000 |
| Source accuracy | 0.8182 |
| Ortalama latency | 874.77 ms |
| p50 / p95 | 843.32 / 1179.85 ms |

İki unanswerable vaka da retrieval sonucu döndürdü. Bu sonuç gizlenmedi veya dataset
sonradan değiştirilmedi; min-score 0.2'nin no-result ayrımı için yetersiz kaldığını
gösterir. Citation validity retrieval-only evaluation'da ölçülmedi.

### Benchmark

Aynı makinede tek process çalışması ölçüldü; cold/warm iddiası yapılmadı. Runtime ve
embedding model yükleme 10195.28 ms sürdü. Üç query embedding süresi sırasıyla
1078.01, 957.46 ve 805.52 ms; embedding dışı retrieval 10.36, 5.05 ve 5.30 ms oldu.
Prompt oluşturma 0.24 ms, tek chat generation 41800.98 ms; chat runtime ve generation
toplamı 49173.18 ms ölçüldü. DB 5 belge/5 chunk ve 155648 byte idi. Generation cevabı
kalite açısından puanlanmadı ve bilinen küçük-model yanlış eşlemesi sürdü.
