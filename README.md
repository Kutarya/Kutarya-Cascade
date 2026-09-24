# Kutarya Cascade v0.1

[![CI](https://github.com/Kutarya/Kutarya-Cascade/actions/workflows/ci.yml/badge.svg)](https://github.com/Kutarya/Kutarya-Cascade/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![License: BSD-4-Clause](https://img.shields.io/badge/license-BSD--4--Clause-blue.svg)](LICENSE)

[English](README_EN.md)

Kutarya Cascade; LLM istemlerini model çağrısından önce inceleyen, kritik bilgileri koruyan ve güvenli durumlarda istem boyutunu azaltan deneysel bir Python aracıdır. Baseline, lossless ve safe yollarını aynı model ve üretim ayarlarıyla karşılaştırmak için ölçüm altyapısı sağlar.

Proje, ölçülmemiş performans kazançları iddia etmez. Integrity Guard doğrulaması başarısız olursa özgün istem kullanılır.

## Durum

- Python çekirdeği ve komut satırı arayüzü kullanılabilir durumdadır.
- Birim ve modelden bağımsız entegrasyon testleri: **44/44 başarılı**.
- Test veri seti: **30 vaka (15 Türkçe, 15 İngilizce)**.
- llama.cpp protokol entegrasyonu test edilmiştir.
- Gerçek Qwen3-4B benchmarkı, gerekli yerel GGUF dosyası bulunmadığı için çalıştırılmamıştır.

Ayrıntılı doğrulama sonuçları için [TEST_REPORT.md](TEST_REPORT.md) dosyasına bakın.

## Kurulum

```bash
git clone https://github.com/Kutarya/Kutarya-Cascade.git
cd Kutarya-Cascade
python -m pip install -e ".[metrics,test]"
python -m unittest discover -s tests -v
```

İstem inceleme:

```bash
kutarya-cascade inspect "Asla 3 kg değerini değiştirme" --mode safe
```

Ortam kontrolü:

```bash
python -m kutarya_cascade doctor
```

## Çalışma yapısı

```text
İstem
  -> PromptInspector
  -> IntegrityGuard
  -> LosslessCompressor veya SafeCompressor
  -> IntegrityGuard
  -> doğrulanmış aday ya da özgün istem
  -> llama.cpp
  -> JSON ve CSV ölçümleri
```

- `inspector.py`: dil, yapı, risk ve kritik öğe tespiti.
- `integrity.py`: olumsuzluk, sayı, tarih, para, birim, varlık, alıntı, kod, JSON, operatör ve talimat doğrulaması.
- `lossless.py`: geri döndürülebilir yapısal sadeleştirme.
- `safe.py`: düşük ve orta riskli düz metinlerde sınırlı sadeleştirme.
- `pipeline.py`: doğrulama ve güvenli geri dönüş akışı.
- `runtime.py`: llama.cpp istemcisi.
- `benchmark.py`: tekrarlı ölçüm ve ham sonuç üretimi.

Davranış sözleşmesi [CASCADE_SPEC.md](CASCADE_SPEC.md) dosyasındadır.

## Benchmark

```powershell
python -m kutarya_cascade benchmark `
  --model "D:\path\to\model.gguf" `
  --llama-server "D:\path\to\llama-server.exe" `
  --warmups 2 --repeats 3
```

Benchmark üç yolu karşılaştırır:

1. `baseline`: özgün istem
2. `lossless`: geri döndürülebilir yapısal sadeleştirme
3. `safe`: risk kontrollü sadeleştirme veya özgün isteme dönüş

Ölçülebilen alanlar arasında giriş token sayısı, sıkıştırma oranı, TTFT, toplam gecikme, çıktı token hızı, RAM/VRAM kullanımı, kalite sinyalleri, kritik öğe korunumu ve fallback oranı bulunur. Ölçülemeyen değerler JSON'da `null`, CSV'de `ölçülemedi` olarak kaydedilir.

## Sınırlar

- Safe Compressor v0.1 bilinçli olarak muhafazakârdır.
- Kod, JSON ve kritik bilgi yoğun istemlerde fallback beklenir.
- Kural tabanlı varlık tespiti tam bir NER sistemi değildir.
- Karakter azalması, token veya gecikme azalmasını garanti etmez.
- Gerçek model sonuçları olmadan performans iddiası yapılamaz.

## Lisans

Proje BSD-4-Clause lisansı altında yayımlanır. Kaynak ve binary dağıtımlarda lisans bildirimi korunmalıdır. Yazılımın özelliklerinden veya kullanımından söz eden tanıtım materyallerinde aşağıdaki ifade yer almalıdır:

> This product includes software developed by Kutarya.

Ayrıntılar için [LICENSE](LICENSE) ve [NOTICE](NOTICE) dosyalarına bakın.
