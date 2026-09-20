# Kutarya Cascade v0.1

[![CI](https://github.com/Kutarya/Kutarya-Cascade/actions/workflows/ci.yml/badge.svg)](https://github.com/Kutarya/Kutarya-Cascade/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![License: BSD-4-Clause](https://img.shields.io/badge/license-BSD--4--Clause-blue.svg)](LICENSE)

[English README](README_EN.md)

Kutarya Cascade, bir LLM çağrısından önce promptu deterministik olarak inceler,
kritik bilgiyi korur, yalnız güvenli görülen yerlerde yükü azaltır ve aynı
model üzerindeki baseline/lossless/safe yollarını gerçek ölçümlerle karşılaştırır.

Bu sürüm performans kazancı vaat etmez. Kazanç ya da kayıp, yalnız oluşturulan
ham JSON/CSV sonuçlarından raporlanır. Güvenlik denetimi geçmezse orijinal prompt
otomatik kullanılır.

## Durum

- Python çekirdeği ve CLI: çalışıyor.
- Unit + modelden bağımsız integration testleri: `44/44` geçti.
- Türkçe/İngilizce veri seti: 30 vaka.
- Mevcut llama.cpp runtime: build 10549, doğrulandı.
- Kutarya Us Qwen3-4B GGUF: beklenen konumda yok. Yerel geliştirme kaydına göre
  model/ModelLab artefaktları 19 Eylül 2026 temizliğinde silinmiş ve kaynak
  arşivine dahil edilmemiş. Bu nedenle gerçek inference benchmarkı
  çalıştırılmadı; sonuç uydurulmadı.

Güncel kanıt ve sınırlar [TEST_REPORT.md](TEST_REPORT.md) içindedir.

## Hızlı başlangıç

```powershell
git clone https://github.com/Kutarya/Kutarya-Cascade.git
cd Kutarya-Cascade
python -m pip install -e ".[metrics,test]"
python -m unittest discover -s tests -v
kutarya-cascade inspect "Asla 3 kg değerini değiştirme" --mode safe
```

## Mimari

```text
prompt
  -> PromptInspector
  -> IntegrityGuard (kritik artefakt envanteri)
  -> LosslessCompressor veya SafeCompressor
  -> tekrar IntegrityGuard
  -> güvenliyse sıkıştırılmış prompt, değilse orijinal prompt
  -> aynı llama.cpp / aynı generation ayarları
  -> JSON + CSV ham ölçüm
```

Temel modüller:

- `inspector.py`: dil, yapı, risk ve kritik artefakt çıkarımı.
- `integrity.py`: negation, sayı, tarih, para, birim, entity, quote, kod,
  JSON, operatör ve önemli talimatları sıralı çoklu küme olarak doğrular.
- `lossless.py`: korunan alanlar dışında yalnız gereksiz whitespace'i azaltır;
  restorasyon planıyla kaynak metni byte-for-byte geri kurar.
- `safe.py`: düşük/orta riskli düzyazıda sınırlı nezaket dolgusu ve bitişik tam
  tekrarları azaltır. Yüksek/kritik riskte işlem yapmaz.
- `pipeline.py`: fail-closed fallback davranışının tek giriş noktası.
- `runtime.py`: llama.cpp `/apply-template`, `/tokenize` ve streaming
  `/v1/chat/completions` istemcisi.
- `benchmark.py`: warm-up, çoklu tekrar, sıra karıştırma, kalite kıyaslama ve
  ham sonuç yazımı.

Tam davranış sözleşmesi [CASCADE_SPEC.md](CASCADE_SPEC.md) içindedir.

## Kurulum ve test

Python 3.10+ yeterlidir. Çekirdek yalnız standart kütüphane kullanır. Süreç RAM
ölçümü için `psutil` önerilir; yoksa ilgili alan `ölçülemedi` kalır.

```powershell
cd D:\Kutarya\Kutarya-Cascade
python -m pip install -e ".[metrics,test]"
python -m pytest
```

Harici paket kurmadan mevcut test takımı:

```powershell
$env:PYTHONPATH = "D:\Kutarya\Kutarya-Cascade\src"
python -m unittest discover -s tests -v
```

Prompt inceleme:

```powershell
python -m kutarya_cascade inspect "Asla 3 kg değerini değiştirme" --mode safe
```

Ortam kontrolü:

```powershell
python -m kutarya_cascade doctor
```

## Gerçek benchmark

Varsayılan komut mevcut dosyaları yerinden kullanır; modeli taşımaz, değiştirmez
ve indirmez:

```powershell
python -m kutarya_cascade benchmark `
  --model "D:\Kutarya\KutaryaModelLab\models\Qwen3-4B-Q6_K.gguf" `
  --llama-server "$env:APPDATA\kutarya-studio\yerel\motor\b10549\llama-server.exe" `
  --warmups 2 --repeats 3
```

Hazır bir aynı-model sunucusuna bağlanmak da mümkündür:

```powershell
python -m kutarya_cascade benchmark --server-url http://127.0.0.1:8912 --server-pid 1234
```

Her vaka için üç yol, aynı sistem promptu ve generation ayarlarıyla ölçülür:

1. `baseline`: orijinal prompt
2. `lossless`: yalnız reversible yapısal sıkıştırma
3. `safe`: risk kapılı semantik sıkıştırma veya otomatik fallback

Varsayılan olarak her mod iki kez warm-up görür ve her ölçüm üç kez tekrarlanır.
Üç modun sırası her tekrarda sabit seed ile karıştırılır. Prompt cache kapalıdır.

## Ölçülen alanlar

- Input token: chat template uygulandıktan sonra `/tokenize` sonucu.
- Compression ratio: aynı vaka/tekrardaki baseline token sayısına oran.
- TTFT: HTTP isteği başlangıcından ilk dolu content parçasına kadar duvar saati.
- Prefill: yalnız server `prompt_ms/prefill_ms` döndürürse; aksi halde
  `ölçülemedi`.
- Toplam latency: istek başlangıcından streaming bitişine kadar.
- Output token/s: server timing verisi; mümkün değilse `ölçülemedi`.
- RAM: `psutil` varsa llama-server süreç RSS başlangıç/tepe/farkı.
- VRAM: `nvidia-smi` toplam GPU kullanımı başlangıç/tepe/farkı. Bu ölçüm
  süreç-özel değildir ve ham kayıtta kapsamı açıkça yazılır.
- Kalite/doğruluk: vaka bazlı beklenen terim, regex, yasak terim ve exact-match
  sinyalleri. LLM-judge kullanılmaz.
- Critical retention: Integrity Guard sonucu.
- Fallback ve kalite regresyonu: ayrı alanlardır; regresyon başarısızlık sayılır.

Ölçülemeyen değer JSON'da `null`, CSV'de `ölçülemedi` olarak saklanır.

## Çıktılar

Başarılı gerçek koşu şunları üretir:

- `results/benchmark-YYYYMMDD-HHMMSS.json`
- `results/benchmark-YYYYMMDD-HHMMSS.csv`
- `results/llama-server.log`

JSON, prompt/çıktı/ölçüm/timing/fallback/kalite dahil tam ham kayıttır. CSV aynı
kayıtların düzleştirilmiş biçimidir. Daha iyi görünen vakaları seçen filtre yoktur.

## Bilinen sınırlar

- Safe Compressor v0.1 bilinçli olarak muhafazakârdır. Kod, JSON, yoğun kritik
  bilgi ve önemli talimatlarda çoğunlukla fallback beklenir.
- Entity çıkarımı kurallıdır; tam NER modeli değildir.
- Whitespace azalması karakter kazancı sağlasa bile tokenizer token kazancı
  sağlamayabilir. Rapor token tabanlı sonucu esas alır.
- Aynı model ve aynı ayarlar deterministikliği artırır fakat GPU/runtime
  jitter'ını yok etmez; bu yüzden tekrar ve sıra karıştırma vardır.
- Mevcut model dosyası geri gelmeden gerçek Qwen sonucu yoktur.

## Lisans ve zorunlu Kutarya atfı

Proje `BSD-4-Clause` lisansıyla yayımlanır. Kaynak ve binary dağıtımlarda lisans
bildirimi korunmalıdır. Yazılımın özelliklerinden veya kullanımından söz eden
tüm tanıtım materyallerinde şu İngilizce ifade görünmelidir:

> This product includes software developed by Kutarya.

Türkçe karşılığı ayrıca eklenebilir: “Bu ürün, Kutarya tarafından geliştirilen
yazılımı içerir.” Hukuken kontrol eden metin `LICENSE` dosyasındaki İngilizce
koşuldur. Ayrıntılı, kopyalanabilir bildirim `NOTICE` dosyasındadır.

Bu advertising/attribution koşulu GPL uyumluluğunu ve bazı ekosistemlerde
benimsenmeyi sınırlayabilir; bilinçli olarak Kutarya atfını zorunlu tutmak için
seçilmiştir.
