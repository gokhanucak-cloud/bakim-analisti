---
name: hat-analizi
description: Motor montaj hattının SMP99 duruş Excel'i (Smp99_Donnees sayfası) ve bakım arıza defteri CSV'si analiz edilirken, Ro / MTTR / MTBF / Pareto / darboğaz / kalıcı çözüm soruları yanıtlanırken ya da bu dosyalardan rapor üretilirken kullan.
---

# Hat Analizi

Hesaplar her zaman bu skill'in betiğiyle yapılır; sayılar elle ya da tahminle üretilmez.
Betik: `scripts/analiz.py` (bu dosyanın klasörüne göre). Python 3.11+, `pandas`, `openpyxl` gerekir.

## Komutlar

```bash
python3 <skill>/scripts/analiz.py hesapla --durus DURUS.xlsx --bakim DEFTER.csv   # → bakim-analizleri/<dönem ayı>/
python3 <skill>/scripts/analiz.py hesapla --klasor <yükleme klasörü> --cikti ...   # dosyaları içerikten bulur
python3 <skill>/scripts/analiz.py rapor --sonuc .../sonuc.json --aksiyonlar .../aksiyonlar.json --cikti ...
```

Çıkış kodu 2 = girdi ya da aksiyon listesi hatası; mesaj stderr'dedir (Türkçe), kullanıcıya aynen aktar.

## Hat parametreleri (`ayarlar.json`)

Sabah 07:30–15:30, Akşam 15:30–23:30 · mola 30 + 15 dk → net **435 dk/vardiya** · hedef **519 motor/vardiya** ·
Ro hedefi **%99** · takt ≈ 0,838 dk/motor · arıza eşiği **5 dk** · anomali eşiği 348 dk.

## Kurallar (betiğin uyguladıkları)

- **Ro** = vardiya üretimi ÷ 519. Vardiya üretimi = o vardiyadaki en yüksek "Kapanıştaki imalat sayısı"
  (son duruştan sonraki üretim görünmez; Ro biraz düşük çıkabilir).
- Üretimi 0 olan vardiya **çalışılmayan vardiya**: analiz dışı.
- Üretim varken 348 dk'yı aşan duruş **veri anomalisi** (sıkışmış alarm / bypass): MTTR/MTBF/Pareto dışı, ayrı listelenir.
- **Arıza** ≥ 5 dk, **mikro duruş** < 5 dk. MTTR = Σ arıza süresi ÷ arıza sayısı;
  MTBF = (çalışılan vardiya × 435 − Σ arıza süresi) ÷ arıza sayısı.
- Duruş dosyasındaki **Ekip** sütunu kullanılmaz (kullanıcı kararı); ekip bazında analiz yapma.
- **Pareto**: kaybın %80'ine kadar olan postalar müdahale önceliği. `baskin_tur` = arıza mı mikro mu ağırlıklı.
- **Motor açığı** = Σ max(0, 519 − üretim). Posta/neden `kayip_motor` = açığın kayıp dakikası payı (tahmin).
- **Bakım eşleşmesi** (koruyucu bakım hariç): aynı postada [başlama − 2 saat, bitiş] içindeki duruşlardan en çok
  kayıplı neden = hedef neden. Önceki 7 gün ile sonraki 7 gün tekrarı:
  Kalıcı (sonra 0) · Kısmi (sonra ≤ önce/2) · Kalıcı değil · Eşleşmedi (pencerede duruş yok) ·
  Takipte (sonraki 7 gün dönem dışında) · Duruş verisi yok (posta duruş dosyasında hiç yok: AGV, BAP, kitting…).
- **Kayıtsız kronik**: ilk 10 posta–neden çiftinden, duruş dosyasının döneminde aynı postada hiç arıza iş emri açılmamış olanlar.

## sonuc.json anahtarları

`ozet` (ortalama_ro, hedefi_tutan_oran, calisilan_vardiya, gercek_kayip_motor, ariza_sayisi, mttr_dk, mtbf_dk,
mikro_sayisi, toplam_kayip_dk, anomali_sayisi) · `vardiya_ro` (vardiya başına) · `gun_ro` (gün başına) · `pareto_posta` · `pareto_neden` (ilk 10) ·
`kirilim_posta` (ilk 15) · `kirilim_vardiya` (Sabah/Akşam; `ortalama_ro` dahil) · `mikro` (ilk 10 posta–neden) · `bakim_eslesme` ·
`kayitsiz_kronikler` · `koruyucu_bakim` · `anomaliler` · `calisilmayan_vardiyalar` · `uyarilar` · `donem` · `ayarlar`.

## aksiyonlar.json şeması

Liste; her madde şu alanların hepsini içerir:

| alan | tür |
|---|---|
| `oncelik` | sayı (1 = en önemli) |
| `posta` | metin (örn. "OP311") |
| `sorun` | metin |
| `kanit` | metin, sonuc.json'daki sayılarla |
| `aksiyon_turu` | `hızlı düzeltme` · `kalıcı çözüm` · `koruyucu bakım` · `otonom bakım` · `veri-sensör kontrolü` |
| `onerilen_aksiyon` | metin |
| `beklenen_kazanc_motor_vardiya` | sayı |
| `sorumlu_onerisi` | metin (mekanik / elektrik / elektronik / proses …) |

## Takip sorularında ham veriye bakmak

```bash
python3 -c "
import sys; sys.path.insert(0, '<skill>/scripts')
from veri import durus_oku
df, _ = durus_oku('DURUS.xlsx')
print(df[df.posta == 'OP311'].groupby('neden').sure_dk.agg(['count', 'sum']).sort_values('sum').tail(10))
"
```

Sütunlar: `baslangic, bitis, sure_dk, posta, zon, modul, neden, vardiya, sayac, tarih`.
Bakım defteri için `bakim_oku`: `is_emri, ariza_tipi, posta, ariza_tanimi, ariza_nedeni, yapilan_mudahale,
baslama, bitis, mudahale_dk, durus_dk, kisi_sayisi`. Çalışan adları bilerek okunmaz; rapora ya da sohbete ad yazma.
