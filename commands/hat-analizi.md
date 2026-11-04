---
description: Duruş Excel'i ve bakım defteriyle hat analizi yap, aksiyon listesi ve HTML rapor üret
argument-hint: "[duruş.xlsx] [bakım.csv]"
---

Motor montaj hattı analizini Türkçe yürüt. Argümanlar: `$ARGUMENTS`

Betik: `${CLAUDE_PLUGIN_ROOT}/skills/hat-analizi/scripts/analiz.py` (yol açılmamışsa `**/hat-analizi/scripts/analiz.py`
dosyasını bul). Önce `hat-analizi` skill'ini yükle.

1. **Girdiler.** İki yol verildiyse `--durus` ve `--bakim` olarak kullan. Verilmediyse `--klasor` ile ara: önce
   `~/.claude/uploads/` altındaki en son değişen klasör, bulamazsan çalışma klasörü. Hangi dosyaları kullandığını
   kullanıcıya söyle.
2. **Hesapla.** `python3 <betik> hesapla ... --cikti bakim-analizleri/<YYYY-MM>` (dönem ayı; bilinmiyorsa önce
   geçici bir klasöre yaz, `sonuc.json`'daki `donem.baslangic`'tan ayı al). Çıkış kodu 2 ise mesajı aynen aktar
   ve dur. `pandas`/`openpyxl` eksikse kurulum komutunu öner.
3. **Aksiyonlar.** `bakim-analisti` ajanına `sonuc.json` yolunu ver; aynı klasöre `aksiyonlar.json` yazsın.
4. **Rapor.** `python3 <betik> rapor --sonuc ... --aksiyonlar ... --cikti <aynı klasör>`. Doğrulama hatası
   olursa ajana düzelttir ve tekrar çalıştır.
5. **Paylaş.** Ortam sayfa yayınlamayı (Artifact) destekliyorsa `rapor.html`'i özel bir sayfa olarak yayınla;
   değilse dosya yolunu ver.
6. **Özet.** Sohbette kısa bir özet: ortalama Ro ve hedefi tutan vardiya oranı, motor açığı, ilk 3 öncelik
   (posta, sorun, aksiyon), dikkat edilmesi gereken veri uyarıları. Ardından "Bir postayı ya da arızayı
   detaylandırmamı ister misiniz?" diye sor.
