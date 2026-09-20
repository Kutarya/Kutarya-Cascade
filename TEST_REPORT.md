# Kutarya Cascade v0.1 — Test Raporu

Tarih: 20 Eylül 2026
Ortam: Windows, Python 3.12.10, NVIDIA GeForce GTX 1650 4 GB

## Sonuç özeti

| Katman | Sonuç |
|---|---|
| Unit + modelden bağımsız integration | **44 başarılı / 0 başarısız** |
| Türkçe/İngilizce veri seti doğrulaması | **30 vaka, 15 TR + 15 EN** |
| llama.cpp runtime | **build 10549 doğrulandı** |
| Kutarya Us Qwen3-4B model dosyası | **bulunamadı** |
| Gerçek baseline inference | **ölçülemedi** |
| Gerçek Cascade lossless inference | **ölçülemedi** |
| Gerçek Cascade safe inference | **ölçülemedi** |

Gerçek inference değerleri yoktur; teorik veya sahte performans sayısı bu rapora
yazılmamıştır.

## Çalıştırılan test komutu

```powershell
$env:PYTHONPATH='D:\Kutarya\Kutarya-Cascade\src'
python -m unittest discover -s tests -v
```

Son çıktı:

```text
Ran 44 tests
OK
```

Kapsam:

- Türkçe/İngilizce dil sezimi.
- Negation, sayı, tarih, para, birim, entity, quote, kod, JSON ve operatör
  çıkarımı.
- Kritik değeri değiştirme/silme/sıralama ihlallerinin reddi.
- Lossless exact round-trip ve kod/JSON byte koruması.
- Safe sıkıştırma, risk kapısı ve otomatik fallback.
- Kalite sinyalleri ve çıktı benzerliği.
- llama.cpp token/timing yanıt parser yardımcıları.
- Yerel sahte HTTP sunucusuyla health/props/template/tokenize/SSE streaming
  protokol entegrasyonu.
- Üç inference yolunun model doublesiyle uçtan uca çalışması.
- JSON/CSV ham sonuç yazımı ve ölçülemeyen alanların korunması.
- Veri setinde gerekli iki dil ve kategori kapsamı.

## Veri seti kapsamı

Her dilde 15 vaka vardır. Kategoriler: negation, number/unit, date/money, code,
JSON, math, instruction following, short, long, adversarial, quote, entity,
operator, repetition ve mixed critical.

Veri seti gerçek model çıktısına göre seçilmedi; model bulunamadığından hiçbir
vaka inference sonucuna bakılarak eklenmedi veya çıkarılmadı.

Model çağrısı yapmayan statik Cascade kontrolü:

| Kontrol | Sonuç |
|---|---:|
| İncelenen yol | 60 (30 lossless + 30 safe) |
| Integrity Guard geçen | 60/60 |
| Safe fallback | 25/30 |
| Lossless ortalama karakter azalması | %0,208 |
| Safe ortalama karakter azalması (fallback dahil) | %0,213 |

Bu oranlar tokenizer token azalması değildir. Özellikle mevcut veri setinde
v0.1'in güvenlik kapısı kazancı sınırlamıştır; model dosyası olmadan bunun TTFT
ve latency avantajına dönüşüp dönüşmediği söylenemez.

## Gerçek model kapısı

Beklenen eski model yolu:

```text
D:\Kutarya\KutaryaModelLab\models\Qwen3-4B-Q6_K.gguf
```

Eski doğrulanmış bilgi: Qwen3-4B Q6_K, 3.306.260.704 bayt. Bu bilgi yerel
geliştirme kaydındandır; dosya bugün mevcut değildir. `C:` ve `D:` sürücüleri,
kullanıcı profili ve Geri Dönüşüm Kutusu `.gguf`/Qwen kopyası için tarandı;
ikinci kopya bulunmadı. Aynı kayıt, 19 Eylül 2026 temizliğinde ModelLab
model/eğitim artefaktlarının silindiğini ve özel kaynak arşivine alınmadığını
kaydeder.

Kullanılabilir runtime:

```text
%APPDATA%\kutarya-studio\yerel\motor\b10549\llama-server.exe
version: 0.1.2-dev (build 10549, commit b2e5e9b28)
```

Modeli yeniden indirmeme, taşımama ve değiştirmeme talimatına uyuldu. Bu nedenle
runtime başlatılmadı ve aşağıdaki metriklerin tümü gerçek benchmark için
`ölçülemedi` durumundadır:

| Metrik | Baseline | Lossless | Safe |
|---|---:|---:|---:|
| Input token | ölçülemedi | ölçülemedi | ölçülemedi |
| Compression ratio | ölçülemedi | ölçülemedi | ölçülemedi |
| TTFT | ölçülemedi | ölçülemedi | ölçülemedi |
| Prefill | ölçülemedi | ölçülemedi | ölçülemedi |
| Total latency | ölçülemedi | ölçülemedi | ölçülemedi |
| Output token/s | ölçülemedi | ölçülemedi | ölçülemedi |
| RAM | ölçülemedi | ölçülemedi | ölçülemedi |
| VRAM | ölçülemedi | ölçülemedi | ölçülemedi |
| Model-output quality | ölçülemedi | ölçülemedi | ölçülemedi |
| Model-output critical retention | ölçülemedi | ölçülemedi | ölçülemedi |
| Fallback oranı | ölçülemedi | ölçülemedi | ölçülemedi |

## Kanıt sınırı

44/44 sonucu sıkıştırma çekirdeği ve benchmark orkestrasyonunun test doublesiyle
çalıştığını kanıtlar. Aynı Qwen modelinde performans kazancı, kalite korunumu,
RAM/VRAM farkı veya gerçek fallback oranını kanıtlamaz. Bunlar yalnız model
dosyası tekrar yerel olarak sağlandığında gerçek komutla ölçülebilir.

## Model geri geldiğinde kabul kapısı

1. `python -m kutarya_cascade doctor` model + runtime için çıkış kodu 0 vermeli.
2. Tam 30 vaka, 3 yol, 2 warm-up ve 3 tekrar çalışmalı.
3. JSON ve CSV kayıt sayısı `30 × 3 × 3 = 270` olmalı.
4. Kritik retention ihlali ve baseline kalite regresyonu başarısızlık sayılmalı.
5. Eksik prefill/RAM/VRAM alanları tahmin edilmemeli.
6. Kategori bazlı avantaj yalnız token azalması + latency azalması + sıfır
   Cascade başarısızlığı birlikte varsa yazılmalı.
