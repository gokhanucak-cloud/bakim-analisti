# Bakım Analisti — Claude Code Eklentisi Tasarımı

- **Tarih:** 2026-11-02
- **Durum:** Onay bekliyor
- **Kullanıcı:** Motor bakım atölye şefi (HB MOTOR, MM11 motor montaj hattı)

## 1. Amaç

Motor montaj hattındaki arızaları azaltmak, mümkünse sıfırlamak. Eklenti iki dosyayı elle yükleyerek analiz eder:

1. **Duruş dosyası:** Posta takip uygulamasının (SMP99) Excel çıktısı.
2. **Bakım arıza defteri:** Bakım ekiplerinin arıza uygulamasından alınan CSV.

Analiz şunları üretir:

- Ro takibi
- Posta ve vardiya bazında MTTR/MTBF
- Pareto analiziyle darboğaz tespiti
- "Bakım ne yaptı, kalıcı çözüm oldu mu?" eşleştirmesi
- Önceliklendirilmiş aksiyon listesi

Sonuçlar standart bir rapor olarak sunulur. Ardından Bakım Analisti ajanıyla sohbet ederek detaya inilir.

**Başarı ölçütü:** Aynı dosyalar her çalıştırmada aynı sayıları verir. Rapor, şefin "nereye, hangi aksiyonla müdahale edeceğim" sorusunu tek sayfada yanıtlar.

## 2. Hat parametreleri (`ayarlar.json`, değiştirilebilir)

| Parametre | Değer |
|---|---|
| 1. vardiya (Sabah) | 07:30–15:30 |
| 2. vardiya (Akşam) | 15:30–23:30 |
| Molalar | 30 dk yemek + 15 dk çay, vardiya başına |
| Net çalışma süresi | 480 − 45 = **435 dk/vardiya** |
| Vardiya hedefi | **519 motor** |
| Ro hedefi | **%99** |
| Takt süresi | 435 ÷ 519 ≈ 0,838 dk/motor (hesaplanır) |
| Arıza eşiği | **5 dk**: altı mikro duruş, 5 dk ve üstü arıza |
| Anomali eşiği | Net sürenin %80'i = **348 dk** |
| Eşleşme penceresi | İş emri başlangıcından 2 saat öncesiyle bitiş saati arası |
| Kalıcılık penceresi | 7 gün öncesi / 7 gün sonrası |
| Pareto kesimi | Kümülatif kaybın %80'i |

## 3. Mimari (Yaklaşım A: hesap motoru + ajan)

Hesaplar her zaman deterministik bir Python betiğinde yapılır. Ajan sayı hesaplamaz: betiğin çıktısını yorumlar, aksiyon önerir ve soruları yanıtlar.

```
bakim-analisti/
├── .claude-plugin/plugin.json      # eklenti tanımı
├── commands/hat-analizi.md         # /hat-analizi komutu
├── agents/bakim-analisti.md        # Bakım Analisti ajanı
├── skills/hat-analizi/
│   ├── SKILL.md                    # kurallar, dosya formatları, iş akışı
│   ├── ayarlar.json                # hat parametreleri
│   └── scripts/
│       ├── analiz.py               # komut satırı: hesapla / rapor
│       ├── veri.py                 # dosya okuma ve temizleme
│       ├── hesap.py                # KPI, Pareto, eşleştirme
│       └── rapor.py                # HTML rapor (satır içi SVG grafikler)
├── tests/                          # pytest
└── README.md
```

### Akış

1. Kullanıcı iki dosyayı yükler ve `/hat-analizi [duruş dosyası] [bakım dosyası]` yazar. Yollar verilmezse, yükleme klasöründeki en son `.xlsx` (SMP99 başlığı aranır) ve `.csv` (bakım defteri başlığı aranır) dosyaları içerik kontrolüyle seçilir.
2. `analiz.py hesapla --durus X --bakim Y --cikti klasor/` çalışır ve `sonuc.json` üretir.
3. Bakım Analisti ajanı `sonuc.json`'u okur ve `aksiyonlar.json`'u yazar.
4. `analiz.py rapor --sonuc sonuc.json --aksiyonlar aksiyonlar.json` çalışır ve `rapor.html` üretir. Ortam destekliyorsa rapor paylaşılabilir bir sayfa olarak yayınlanır.
5. Ajan sohbette kısa bir özet verir: ilk 3 öncelik ve Ro durumu. Kullanıcı sorularla devam eder. Ajan gerekirse `sonuc.json`'a ya da ham veriye bakarak yanıtlar.

Çıktı klasörü: `bakim-analizleri/<analiz-dönemi>/` (örnek: `bakim-analizleri/2026-10/`).

## 4. Veri formatları ve hazırlık

### 4.1 Duruş dosyası (SMP99 Excel)
- Sayfa: `Smp99_Donnees`. Başlık 7. satırda, satır 1–6 meta bilgi.
- Kullanılan sütunlar: `Saat` (başlangıç, `dd.mm.yyyy HH:MM:SS`), `Son` (bitiş), `Süre`, `Zon`, `Modül`, `Durus nedeni`, `Posta` (Sabah/Aksam), `Ekip` (1/2/3), `Kapanistaki imalat sayisi`.
- **Süre birimi dakikadır.** Başlıkta "1/100 dk" yazsa da `Son − Saat` farkıyla doğrulandı. Betik bu doğrulamayı her çalıştırmada örneklem üzerinde tekrar yapar; tutarsızlık varsa uyarı verir.
- `Posta` boş olan satırlar atılır (bunlar özet satırlarıdır).
- **Posta (istasyon) kimliği:** `Zon` içindeki `OP(\d+)` numarası, örneğin `6611 - OP311_Z1` → `OP311`. OP numarası yoksa zon adı kullanılır (örnek: `Konv_Z1`).
- **Vardiya anahtarı:** (tarih, Sabah/Akşam). Akşam vardiyası 23:30'da biter, yani tarih aynı gün kalır.

### 4.2 Bakım arıza defteri (CSV)
- UTF-8 (BOM'lu), ayraç `;`, tırnaklı alanlar.
- Kullanılan sütunlar: `İş Emri No`, `Arıza Tipi`, `Sebep`, `Ana Etken`, `Makine Tesis No`, `OP No`, `Arıza Tanımı`, `Arıza Nedeni`, `Yapılan Müdahale`, `Başlama Tarihi`, `Bitiş Tarihi` (`dd.mm.yyyy HH:MM`), `Toplam Müdahale Süresi`, `Duruş Süresi`, `Müdahale Eden`, `Kişi Sayısı`.
- **Posta kimliği:** `OP No` içindeki `MM11 (\d+)` → `OP<n>`. Sayısal olmayanlar (örnek: `MM11 AGV`, `MM11 MOP1`) olduğu gibi tutulur ve eşleşmez.
- `Arıza Tipi = Koruyucu Bakım` olan kayıtlar eşleştirmeye girmez. Koruyucu bakım sayıları ayrıca raporlanır.

### 4.3 Ayıklama kuralları
1. **Vardiya üretimi** = o vardiyadaki en yüksek `Kapanistaki imalat sayisi`.
2. Üretimi 0 olan vardiya **çalışılmayan vardiya** sayılır ve tüm hesaplardan çıkarılır. Raporda listelenir.
3. Üretim yapılan vardiyada 348 dakikayı aşan duruş **veri anomalisi** sayılır (sıkışmış alarm, bypass edilmiş posta). MTTR/MTBF/Pareto'ya girmez, raporda ayrı listelenir.

**Bilinen sınırlama:** Son duruştan sonra üretilen motorlar sayaçta görünmez, bu yüzden Ro biraz düşük çıkabilir. İleride gerçek vardiya üretimi ayrı bir girdi olarak eklenebilir.

## 5. Hesaplar

| KPI | Formül | Kırılımlar |
|---|---|---|
| Ro | vardiya üretimi ÷ 519 | vardiya, gün, Sabah/Akşam, dönem ortalaması; hedefi tutan vardiya oranı |
| Arıza sayısı | Süre ≥ 5 dk duruş adedi | posta, vardiya, hat |
| MTTR | Σ arıza süresi ÷ arıza sayısı | posta, vardiya, hat |
| MTBF | (çalışılan vardiya sayısı × 435 − Σ arıza süresi) ÷ arıza sayısı | posta, vardiya, hat |
| Mikro duruş | Süre < 5 dk: adet, Σ süre, adet ÷ çalışılan saat | posta, neden |
| Toplam kayıp | Σ süre (arıza + mikro) | posta, neden |
| Kayıp motor (tahmini) | toplam kayıp ÷ takt süresi | posta, neden |

- Vardiya kırılımında "çalışılan vardiya sayısı" o vardiyaya ait çalışılan vardiyalardır. Hat ve posta bazında tüm çalışılan vardiyalar kullanılır.
- Arıza sayısı 0 ise MTTR/MTBF "—" gösterilir (sonsuz/tanımsız).
- Kayıp motor bir tahmindir: ara stoklar nedeniyle bir posta duruşu hattı her zaman durdurmaz. Raporda bu not düşülür.

### 5.1 Darboğaz (Pareto)
- Postalar toplam kayba göre azalan sıralanır, kümülatif yüzde hesaplanır. %80'e kadar olanlar **müdahale önceliği** sayılır.
- Aynı analiz `Durus nedeni` için de yapılır (posta + neden birlikte, ilk 10).
- Her öncelikli posta için kaybın türü belirtilir: ağırlıklı **arıza** (bakım/kalıcı çözüm konusu) ya da ağırlıklı **mikro duruş** (proses/ayar/sensör/otonom bakım konusu).

### 5.2 Bakım eşleşmesi
Koruyucu bakım dışındaki her iş emri için:

1. **Eşleşen duruşlar:** Aynı postada, `[Başlama − 2 saat, Bitiş]` aralığında başlayan duruşlar. En çok süre kaybettiren `Durus nedeni` iş emrinin **hedef nedeni** sayılır.
2. Hedef nedenin aynı postada iş emrinden **önceki 7 gün** ve **bitişten sonraki 7 gün** içindeki tekrar sayısı karşılaştırılır. Yalnızca çalışılan vardiyalar sayılır, anomaliler hariç tutulur.
3. Sınıflandırma:
   - **Kalıcı:** sonraki tekrar = 0
   - **Kısmi:** sonraki ≤ önceki ÷ 2
   - **Kalıcı değil:** sonraki > önceki ÷ 2
   - **Eşleşmedi:** pencerede duruş yok
4. Bitişten sonra 7 günlük veri yoksa (dönem sonu) sınıf "**Takipte**" olur.

**Ters yön:** Pareto'nun ilk 10 posta–neden çiftinden dönem içinde aynı postada hiç iş emri açılmamış olanlar "**kayıt açılmamış kronik duruş**" olarak listelenir.

## 6. Bakım Analisti ajanı

- **Rol:** Montaj hattı bakımında deneyimli bir analist. TPM, otonom bakım, koruyucu bakım, 5 Neden ve Ishikawa yöntemlerini bilir. Dil Türkçe.
- **Bağlam:** Bölüm 2'deki hat parametreleri. Hesap kuralları skill'den gelir.
- **Kurallar:**
  - Sayı hesaplamaz, sayıları `sonuc.json`'dan alır.
  - Veride olmayan bilgiyi uydurmaz. Varsayımları "varsayım" diye belirtir.
  - Her öneriyi bir veriye dayandırır (posta, neden, adet, dakika).
- **Aksiyon listesi** (`aksiyonlar.json`), her madde için: `oncelik` (1..n), `posta`, `sorun`, `kanit` (sayılarla), `aksiyon_turu` (hızlı düzeltme / kalıcı çözüm / koruyucu bakım / otonom bakım / veri-sensör kontrolü), `onerilen_aksiyon`, `beklenen_kazanc_motor_vardiya`, `sorumlu_onerisi` (mekanik/elektrik/elektronik/proses).
- **Sohbet:** "OP311'de neden bu kadar duruş var?", "Ekip 2'nin MTTR'si neden yüksek?", "Bu arıza için 5 Neden yap" gibi soruları sonuç dosyası ve ham veriyle yanıtlar.

## 7. Rapor (`rapor.html`)

Tek dosyadan oluşur. Dış kaynak (CDN) kullanmaz, grafikler satır içi SVG'dir. Telefon ekranında da okunur ve yazdırılabilir.

1. **Özet:** Dönem, çalışılan vardiya sayısı, ortalama Ro ve %99 hedefi, hedefi tutan vardiya oranı, toplam kayıp (dk ve motor), hat MTTR/MTBF, arıza ve mikro duruş adetleri.
2. **Ro trendi:** Vardiya bazında çubuk grafik, %99 çizgisi, Sabah/Akşam renk ayrımı.
3. **Darboğaz Pareto'su:** Posta Pareto grafiği (çubuk + kümülatif çizgi) ve ilk 10 posta–neden tablosu.
4. **MTTR/MTBF:** Posta tablosu (ilk 15) ile vardiya karşılaştırması.
5. **Mikro duruşlar:** İlk 10 posta–neden; adet, dakika, saatteki sıklık.
6. **Bakım eşleşmesi:** Sınıf dağılımı, "kalıcı değil" ve "kısmi" listesi (iş emri, arıza tanımı, yapılan müdahale, önce/sonra) ve kayıt açılmamış kronik duruşlar.
7. **Aksiyon listesi:** Ajanın `aksiyonlar.json` içeriği.
8. **Veri anomalileri:** Çalışılmayan vardiyalar, sıkışmış alarmlar, uyarılar (örneğin eşleşmeyen OP numaraları).

## 8. Hata yönetimi
- Dosya bulunamazsa ya da formatı tanınmazsa beklenen başlıklar listelenerek açık bir Türkçe hata verilir.
- Beklenen bir sütun eksikse hangi sütun olduğu söylenir ve analiz durur.
- Tarih ayrıştırılamayan satırlar atlanır; sayısı uyarı olarak rapora yazılır.
- İki dosyanın dönemleri örtüşmüyorsa uyarı verilir, eşleştirme yalnızca örtüşen aralıkta yapılır.
- `pandas` veya `openpyxl` yoksa kurulum komutu gösterilir.

## 9. Test
- **Birim testleri (pytest):** Küçük, elle hazırlanmış örnek veriyle; beklenen değerler elle hesaplanır.
  - OP numarası çıkarma (her iki dosya formatı)
  - Çalışılmayan vardiya ve anomali ayıklama
  - Ro, MTTR, MTBF formülleri (arıza sayısı 0 dahil)
  - Pareto kümülatif kesimi
  - Eşleşme sınıfları (kalıcı / kısmi / kalıcı değil / eşleşmedi / takipte)
- **Gerçek veri duman testi:** Ekim 2026 dosyalarıyla çalışır. Bilinen gerçekler doğrulanır:
  - 14.296 duruş satırı
  - 5 çalışılmayan vardiya (17 Ekim Sabah ve Akşam; 27, 28 ve 29 Ekim Akşam)
  - OP311'in en sık duran posta olması
  - 5 Ekim Sabah üretiminin 521 olması
- Gerçek veri dosyaları depoya eklenmez (kişisel ad ve sicil bilgileri içerir).

**Karar (2026-11-05):** Duruş dosyasındaki "Ekip" sütunu kullanılmaz. Gerçek veride her vardiyada üç ekip numarası birlikte görülüyor ve anlamı belirsiz.

**Karar (2026-11-05):** OP311 ve OP312 postaları kapsam dışıdır (`ayarlar.json` → `kapsam_disi_postalar`). Duruşları ve iş emirleri duruş/bakım analizlerine alınmaz; Ro ve motor açığı hattın tamamından hesaplanır.

## 10. Kapsam dışı (şimdilik)
- Dosyaların otomatik çekilmesi (uygulama API'si, paylaşılan klasör)
- Canlı panel (mod)
- Dönemler arası trend karşılaştırması: ilk sürümden sonra eklenebilir; `sonuc.json` buna uygun saklanır.
- Marketplace üzerinden ekiple paylaşım: eklenti hazır olunca, isteğe bağlı olarak yapılır.
