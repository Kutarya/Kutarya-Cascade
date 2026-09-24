# Kutarya Cascade v0.1 — Teknik Belirtim

## 1. Kapsam

Cascade, istem dönüşümlerinde kritik bilgilerin korunmasını deterministik kontrollerle doğrular. Dönüşüm doğrulanamazsa özgün istem kullanılır. Bu kontrol, model çıktısının doğruluğunu garanti etmez; çıktı kalitesi ayrıca baseline ile karşılaştırılmalıdır.

Temel kural:

```text
candidate doğrulanmazsa sent_prompt == original_prompt
```

## 2. Prompt Inspector

Inspector harici model kullanmadan aşağıdaki öğeleri konumları ve özgün değerleriyle tespit eder:

| Tür | Kapsam |
|---|---|
| Olumsuzluk | Türkçe ve İngilizce olumsuzluk kalıpları |
| Sayı | İşaretli, ondalık ve yüzde biçimleri |
| Tarih | ISO ve gün/ay/yıl biçimleri |
| Para ve birim | Yaygın para, süre, veri, uzunluk ve ağırlık biçimleri |
| Varlık | Büyük harfli çok sözcüklü adlar |
| Alıntı | Tek, çift ve tipografik tırnak blokları |
| Kod ve JSON | Fenced/inline kod ve ayrıştırılabilir JSON |
| Operatör | Karşılaştırma, boolean ve aritmetik operatörler |
| Talimat | Güçlü Türkçe ve İngilizce emir kalıpları |

Risk skoru yalnız dönüşüm kapısı olarak kullanılır; kalite ölçütü değildir.

## 3. Integrity Guard

Özgün ve aday metindeki kritik öğelerin normalize edilmiş değerleri, tekrar sayıları ve sıraları karşılaştırılır. Eksik, eklenmiş, değiştirilmiş veya yeniden sıralanmış öğe varsa aday reddedilir.

## 4. Lossless Compressor

Lossless yolu korumasız düz metinde:

- yinelenen yatay boşlukları azaltır,
- satır kenarı boşluklarını kaldırır,
- ikiden fazla ardışık boş satırı ikiye indirir.

Kod, inline kod, JSON ve alıntılar değiştirilmez. Restorasyon planı özgün Python string'ini tam olarak yeniden kurabilmelidir.

## 5. Safe Compressor

Safe yolu:

1. İstemi inceler.
2. Risk `high` veya `critical` ise özgün istemi kullanır.
3. Lossless dönüşümünü uygular.
4. Sınırlı nezaket dolgularını kaldırır.
5. Yalnız bitişik ve tamamen aynı cümleleri tekilleştirir.
6. Integrity Guard doğrulamasını tekrarlar.
7. Aday boşsa, kazanç sağlamıyorsa veya doğrulama başarısızsa özgün isteme döner.

v0.1; serbest özetleme, yeniden yazma, eşanlamlı değiştirme veya başka bir LLM ile sıkıştırma yapmaz.

## 6. Fallback kodları

| Kod | Açıklama |
|---|---|
| `risk_gate:high` | Yüksek kritik bilgi yoğunluğu |
| `risk_gate:critical` | Kod, JSON veya çok yoğun kritik bilgi |
| `integrity_guard` | Kritik öğe doğrulaması başarısız |
| `empty_candidate` | Aday metin boş |
| `no_gain` | Aday özgün metinden kısa değil |
| `restore_failed` | Kayıpsız restorasyon doğrulanamadı |

## 7. Benchmark kuralları

- Aynı model dosyası ve llama.cpp süreci kullanılır.
- Sistem istemi ve üretim ayarları tüm yollarda aynıdır.
- Varsayılanlar: `temperature=0`, `top_p=1`, `top_k=40`, `seed=42`.
- Prompt cache kapalıdır.
- Her yol için warm-up uygulanır.
- Her vaka varsayılan olarak üç kez ölçülür.
- Yol sırası sabit seed ile karıştırılır.
- Ham kayıtlar filtrelenmeden JSON ve CSV'ye yazılır.
- Aday kalite skoru baseline değerinden düşükse regresyon kaydedilir.

## 8. Ölçümler

TTFT istemci duvar saatidir. Prefill yalnız sunucu timing alanı sağlarsa kaydedilir. RAM süreç RSS değeridir. VRAM ölçümü `nvidia-smi` toplam GPU kullanımına dayanır ve süreç dışı yüklerden etkilenebilir. Ölçülemeyen değerler tahmin edilmez.

## 9. Başarısızlık koşulları

Aşağıdaki durumlardan biri Cascade başarısızlığıdır:

- Kritik öğe korunmamıştır.
- Safe veya lossless kalite skoru baseline değerinin altındadır.
- Dönüştürülmüş istem gerekli çıktı kısıtını kaybetmiştir.

Token azalması veya gecikme iyileşmesi ölçülmeden yalnız karakter sayısına dayanarak performans iddiası yapılamaz.
