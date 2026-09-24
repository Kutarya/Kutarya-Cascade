# Kutarya Cascade v0.1 — Test Raporu

**Tarih:** 20 Eylül 2026  
**Ortam:** Windows, Python 3.12.10, NVIDIA GeForce GTX 1650 4 GB

## Sonuç

| Katman | Durum |
|---|---|
| Birim ve modelden bağımsız entegrasyon testleri | **44 başarılı / 0 başarısız** |
| Türkçe/İngilizce veri seti | **30 vaka (15 TR, 15 EN)** |
| llama.cpp runtime protokolü | **build 10549 ile doğrulandı** |
| Qwen3-4B GGUF model dosyası | **Bulunamadı** |
| Gerçek baseline/lossless/safe inference | **Ölçülemedi** |

Gerçek inference çalıştırılmadığı için bu rapor performans kazancı içermez.

## Test komutu

```powershell
$env:PYTHONPATH='D:\Kutarya\Kutarya-Cascade\src'
python -m unittest discover -s tests -v
```

```text
Ran 44 tests
OK
```

## Test kapsamı

- Türkçe ve İngilizce dil tespiti.
- Olumsuzluk, sayı, tarih, para, birim, varlık, alıntı, kod, JSON ve operatör çıkarımı.
- Kritik öğe silme, değiştirme ve sıralama ihlallerinin reddi.
- Lossless exact round-trip ve kod/JSON koruması.
- Safe dönüşüm, risk kapısı ve fallback davranışı.
- Kalite sinyalleri ve çıktı benzerliği.
- llama.cpp health, props, template, tokenize ve SSE streaming protokolleri.
- Üç inference yolunun test doubles ile uçtan uca çalışması.
- JSON/CSV ham sonuç üretimi ve eksik ölçümlerin korunması.
- Veri setinin dil ve kategori kapsamı.

## Statik doğrulama

| Kontrol | Sonuç |
|---|---:|
| İncelenen yol | 60 (30 lossless, 30 safe) |
| Integrity Guard doğrulaması | 60/60 |
| Safe fallback | 25/30 |
| Lossless ortalama karakter azalması | %0,208 |
| Safe ortalama karakter azalması | %0,213 |

Bu değerler token azalması değildir. Gerçek model olmadan TTFT veya toplam gecikme etkisi çıkarılamaz.

## Gerçek model durumu

Gerekli Qwen3-4B GGUF dosyası test ortamında bulunmadığından llama.cpp inference süreci başlatılmadı. Modelin indirilmesi, taşınması veya yeniden oluşturulması bu test kapsamına dahil değildi.

Aşağıdaki alanların tamamı gerçek benchmark için ölçülemedi:

- giriş token sayısı ve sıkıştırma oranı,
- TTFT, prefill ve toplam gecikme,
- çıktı token hızı,
- RAM ve VRAM,
- model çıktısı kalitesi,
- kritik öğe korunumu,
- fallback oranı.

## Kanıt sınırı

44/44 sonucu çekirdek işlevlerin ve benchmark orkestrasyonunun kontrollü test ortamında çalıştığını gösterir. Gerçek model performansı, kalite korunumu ve kaynak kullanımı hakkında kanıt oluşturmaz.

## Gerçek benchmark kabul ölçütleri

1. `python -m kutarya_cascade doctor` model ve runtime için başarılı olmalıdır.
2. 30 vaka, 3 yol, 2 warm-up ve 3 tekrar çalıştırılmalıdır.
3. JSON ve CSV kayıt sayısı `30 × 3 × 3 = 270` olmalıdır.
4. Kritik öğe ihlali ve baseline altı kalite başarısızlık sayılmalıdır.
5. Eksik ölçümler tahmin edilmemelidir.
6. Performans sonucu yalnız token, gecikme ve kalite verileri birlikte değerlendirilerek raporlanmalıdır.
