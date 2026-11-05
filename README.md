# Bakım Analisti

Motor montaj hattı için bir Claude Code eklentisi. İki dosyayı birlikte analiz eder:

- **SMP99 duruş Excel'i**: posta takip uygulamasının çıktısı (`Smp99_Donnees` sayfası)
- **Bakım arıza defteri CSV'si**: `;` ayraçlı, `İş Emri No` başlıklı dosya

Ürettikleri:

- Ro takibi (üretim ÷ 519)
- Posta ve vardiya bazında MTTR/MTBF (arıza ≥ 5 dk; mikro duruşlar ayrıca)
- Pareto ile darboğaz tespiti
- "Bakımın müdahalesi kalıcı çözüm oldu mu?" eşleştirmesi
- Bakım Analisti ajanının hazırladığı öncelikli aksiyon listesi
- Tek dosyalık bir HTML rapor

## Kurulum

Eklenti Python ile hesap yapar. Önce gerekli paketleri kurun:

```bash
pip install pandas openpyxl
```

Claude Code terminal oturumunda, istem satırına:

```
/plugin install bakim-analisti --marketplace gokhanucak-cloud/bakim-analisti
```

Ya da kabuktan:

```bash
claude plugin install bakim-analisti --marketplace gokhanucak-cloud/bakim-analisti
```

Masaüstü uygulamasında (`/plugin` çalışmıyorsa): istem kutusunun yanındaki **+** → **Plugins** →
**Add marketplace** ile `gokhanucak-cloud/bakim-analisti` ekleyin, ardından **Add plugin**.

Kurulumda önce `Add marketplace?` sorusu gelir (`y` ile onaylayın), sonra kapsam seçilir (Enter).

Geliştirirken depoyu klonlayıp doğrudan yükleyebilirsiniz:

```bash
claude --plugin-dir /yol/bakim-analisti
```

## Kullanım

1. İki dosyayı Claude Code oturumuna yükleyin (ya da çalışma klasörüne koyun).
2. `/hat-analizi` yazın. Dosya yollarını da verebilirsiniz: `/hat-analizi duruş.xlsx defter.csv`.
3. Rapor `bakim-analizleri/<YYYY-MM>/rapor.html` olarak üretilir. Ardından sorularınızla devam edin, örneğin:
   "OP311'deki yağ eşanjörü uyarısı için 5 Neden yap".

Komut satırından doğrudan da çalıştırılabilir:

```bash
python3 skills/hat-analizi/scripts/analiz.py hesapla --durus D.xlsx --bakim B.csv --cikti cikti/
python3 skills/hat-analizi/scripts/analiz.py rapor --sonuc cikti/sonuc.json --cikti cikti/
```

## Ayarlar

Vardiya saatleri, molalar (30 + 15 dk → net 435 dk), vardiya hedefi (519), Ro hedefi (%99), arıza eşiği (5 dk),
anomali oranı, eşleşme ve kalıcılık pencereleri ile Pareto kesimi `skills/hat-analizi/ayarlar.json`
dosyasındadır.

## Gizlilik

Bakım defterindeki çalışan adları okunmaz; sonuçlara ve rapora yazılmaz. Gerçek veri dosyaları ve
`bakim-analizleri/` klasörü `.gitignore` ile depo dışında tutulur.

## Geliştirme

```bash
pip install -r requirements-dev.txt
pytest                                          # birim testleri
BAKIM_DURUS=D.xlsx BAKIM_DEFTER=B.csv pytest    # + gerçek veri duman testi
claude plugin validate .
```
