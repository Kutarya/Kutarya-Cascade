# Katkı Rehberi

Katkı göndermeden önce:

1. Değişiklik için ayrı bir branch oluşturun.
2. Davranış değişikliği varsa ilgili testleri ekleyin veya güncelleyin.
3. `python -m unittest discover -s tests -v` komutunu çalıştırın.
4. Performans iddialarını ham JSON/CSV ölçümleriyle destekleyin.
5. Kritik öğe ihlallerini, fallback durumlarını ve ölçülemeyen alanları açıkça belirtin.

Pull request açıklamasında değişikliğin amacı, kapsamı, riskleri ve çalıştırılan testler yer almalıdır. İlgisiz değişiklikleri aynı pull request içinde birleştirmeyin.

Katkı gönderilmesi, katkının depo lisansı altında dağıtılmasını kabul ettiğiniz anlamına gelir. Kutarya atıf koşulu katkılarda ve türetilmiş dağıtımlarda korunmalıdır. Ayrıntılar için [LICENSE](LICENSE) ve [NOTICE](NOTICE) dosyalarına bakın.
