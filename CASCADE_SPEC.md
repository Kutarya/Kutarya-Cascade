# Kutarya Cascade v0.1 — Teknik Sözleşme

## 1. Amaç ve güven sınırı

Cascade bir doğruluk oracle'ı değildir. Promptu küçültmeye çalışırken kritik
verinin değişmediğini deterministik kontrollerle kanıtlar; kanıtlayamazsa
orijinali yollar. Bir sıkıştırmanın Integrity Guard'ı geçmesi, model cevabının
doğru olacağını garanti etmez. Cevap kalitesi ayrıca baseline ile ölçülür.

Temel invariant:

```text
candidate güvenli değilse sent_prompt == original_prompt
```

## 2. Prompt Inspector

Inspector dış model çağırmaz. Aşağıdaki artefaktları konum ve özgün değerle
çıkarır:

| Tür | Koruma yöntemi |
|---|---|
| Negation | Türkçe/İngilizce olumsuzluk sözlüğü, Unicode-aware sınırlar |
| Sayı | işaretli, ondalık, yüzde biçimleri |
| Tarih | ISO ve gün/ay/yıl biçimleri |
| Para | sembol ve TL/TRY/USD/EUR/GBP biçimleri |
| Birim | süre, veri, elektrik, uzunluk, ağırlık ve token/s biçimleri |
| Entity | büyük harfli çok sözcüklü adlar |
| Quote | tek/çift/typographic tırnak blokları |
| Kod | fenced ve inline kod |
| JSON | `json.JSONDecoder` ile gerçekten parse edilen object/array |
| Operatör | eşitlik, karşılaştırma, boolean ve aritmetik operatörler |
| Talimat | satır başındaki güçlü Türkçe/İngilizce emir kalıpları |

Risk skoru artefakt türlerinin açıklanabilir ağırlıklı toplamıdır. Kod/JSON,
olumsuz talimat ve kısa kritik prompt ek risk getirir. Skor yalnız sıkıştırma
kapısıdır; kalite skoru değildir.

## 3. Integrity Guard

Her tür için özgün ve aday metindeki normalize edilmiş değerlerin:

1. çoklu kümesi,
2. tekrar sayısı,
3. sırası

karşılaştırılır. Eksik, eklenmiş veya yeniden sıralanmış kritik değer varsa
sonuç başarısızdır. JSON, kod ve quote içeriği tek parça olarak korunduğu için
iç değişiklik doğrudan yakalanır.

## 4. Lossless Compressor

Lossless yolu yalnız korumasız düzyazıda:

- yinelenen yatay whitespace'i bire indirir,
- satır kenarı whitespace'ini kaldırır,
- ikiden fazla ardışık boş satırı ikiye indirir.

Kod, inline code, JSON ve quote byte-for-byte kopyalanır. Her kaldırma işlemi
aday indeks ve kaldırılan bayt dizisi olarak restorasyon planına yazılır.
`restore()` özgün Python string'ini tam kuramazsa çalışma hatası verir. Model
restorasyon planını almaz; plan denetlenebilirlik içindir. Model yalnız kritik
artefakt denetiminden geçen sade metni görür.

## 5. Risk-aware Safe Compressor

Safe yol sırasıyla:

1. Promptu inceler.
2. Risk `high` veya `critical` ise hiç değiştirmeden fallback yapar.
3. Lossless dönüşümü uygular.
4. Sınırlı nezaket dolgularını (`lütfen`, `please` vb.) kaldırır.
5. Yalnız bitişik ve normalize edildiğinde tamamen aynı cümleyi tekilleştirir.
6. Integrity Guard'ı tekrar çalıştırır.
7. Aday boşsa, kazanç yoksa veya guard başarısızsa orijinale döner.

Bu sürüm serbest özetleme, cümle yeniden yazma, eşanlamlı değiştirme veya başka
bir LLM ile prompt sıkıştırma yapmaz.

## 6. Fallback nedenleri

| Kod | Anlam |
|---|---|
| `risk_gate:high` | kritik bilgi yoğunluğu yüksek |
| `risk_gate:critical` | kod/JSON veya çok yoğun kritik bilgi |
| `integrity_guard` | kritik artefakt eksik/ek/farklı sırada |
| `empty_candidate` | aday boş kaldı |
| `no_gain` | aday özgünden kısa değil |
| `restore_failed` | lossless exact restorasyon doğrulanmadı |

## 7. Benchmark adaleti

- Tek model dosyası ve tek llama.cpp süreci kullanılır.
- Sistem promptu ve generation ayarları üç yolda aynıdır.
- `temperature=0`, `top_p=1`, `top_k=40`, `seed=42` varsayılandır.
- `cache_prompt=false` kullanılır.
- Her mod warm-up görür.
- Her vaka en az iki, varsayılan üç kez ölçülür.
- Mod sırası her tekrar içinde sabit seed ile karıştırılır.
- Baseline ve aday kalite sinyali aynı vaka/tekrar grubunda karşılaştırılır.
- Adayın kalite skoru baseline'dan düşükse `quality_regression=true` ve
  `cascade_failure=true` olur.
- Ham kayıtlar elenmeden JSON/CSV'ye yazılır.

## 8. Ölçüm tanımları

`TTFT` istemci duvar saatidir. `prefill_ms` yalnız llama.cpp timing alanı
sağlarsa doldurulur; TTFT'den tahmin edilmez. RAM süreç RSS'dir; psutil yoksa
ölçülmez. VRAM `nvidia-smi` toplam GPU ölçümüdür ve başka süreçlerden
etkilenebilir. Bu sınırlama her kaydın `gpu_scope` alanındadır.

## 9. Başarısızlık tanımı

Aşağıdakilerden biri Cascade başarısızlığıdır:

- kritik artefakt korunmadı,
- safe/lossless kalite skoru aynı tekrar baseline skorunun altına düştü,
- sıkıştırılmış yol gerekli çıktı kısıtını kaybetti.

Latency artışı güvenlik başarısızlığı değildir fakat “avantaj sağladı” olarak
raporlanmaz. Token azalması yoksa yalnız karakter azalmasına bakılarak performans
iddiası yazılmaz.
