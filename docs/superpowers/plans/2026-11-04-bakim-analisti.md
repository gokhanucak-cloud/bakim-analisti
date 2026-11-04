# Bakım Analisti Eklentisi — Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Hedef:** İki dosyadan (SMP99 duruş Excel'i + bakım arıza defteri CSV'si) Ro, MTTR/MTBF, Pareto ve bakım eşleşmesi hesaplayan bir Claude Code eklentisi. Eklenti bir Bakım Analisti ajanı, bir `/hat-analizi` komutu ve bir HTML rapor içerir.

**Mimari:** Hesaplar `skills/hat-analizi/scripts/` altındaki deterministik Python modüllerindedir: `veri.py` dosyaları okur, `hesap.py` hesaplar, `rapor.py` HTML üretir, `analiz.py` komut satırı arayüzüdür. Betik `sonuc.json` üretir. Ajan bu dosyayı okuyup `aksiyonlar.json` yazar, betik ikisinden `rapor.html` üretir.

**Teknoloji:** Python 3.11+, pandas, openpyxl, pytest. Claude Code eklenti formatı: `.claude-plugin/plugin.json`, `commands/`, `agents/`, `skills/`.

**Spec:** `docs/superpowers/specs/2026-11-02-bakim-analisti-design.md`. Uygulayıcı bu belgeyi de okur; sayısal kurallar oradan gelir.

## Genel kısıtlar

- Tüm kullanıcıya dönük metinler (hata mesajları, rapor, ajan) **Türkçe**.
- Hat parametreleri yalnızca `skills/hat-analizi/ayarlar.json` dosyasından okunur, kodda sabit değer yazılmaz. Değerler: `vardiya_hedefi: 519`, `ro_hedefi: 0.99`, `net_sure_dk: 435`, `ariza_esigi_dk: 5`, `anomali_orani: 0.8`, `eslesme_oncesi_saat: 2`, `kalicilik_gun: 7`, `pareto_kesim: 0.8`, `vardiyalar: {"Sabah": ["07:30","15:30"], "Aksam": ["15:30","23:30"]}`, `molalar_dk: {"yemek": 30, "cay": 15}`.
- Takt süresi = `net_sure_dk / vardiya_hedefi` (hesaplanır). Anomali eşiği = `net_sure_dk * anomali_orani` (348 dk).
- Duruş dosyasındaki `Süre` **dakikadır**.
- Gerçek veri dosyaları depoya girmez (`.gitignore` mevcut). Test verileri koddan üretilir.
- Rapor tek bir HTML dosyasıdır: dış kaynak/CDN yok, grafikler satır içi SVG.
- Bakım defterindeki çalışan adları (`Müdahale Eden`) `sonuc.json`'a ve rapora yazılmaz. Yalnızca `Kişi Sayısı` taşınır.
- Komut satırının çıkış kodları: başarı 0, `VeriHatasi` 2.

## İnceleme odağı

1. **Arıza metinlerinde `<`, `&`, `"` karakterleri** (örnek: "-1...5 BAR <...>"). Rapor bunları kaçışlamalı, HTML bozulmamalı. → Görev 6, `test_html_kacis`.
2. **Dosyalar ters ya da yanlış verilmesi** (CSV'nin `--durus` olarak verilmesi, başlığı tanınmayan dosya). Beklenen başlıkları listeleyen Türkçe `VeriHatasi`, çıkış kodu 2. → Görev 1 `test_yanlis_dosya_turu`, Görev 5 `test_cli_hata_kodu`.
3. **Bakım defterinde boş/bozuk tarih veya OP No.** Satır atlanır, uyarı sayısı `sonuc["uyarilar"]`'a yazılır, analiz sürer. → Görev 1 `test_bakim_bozuk_satir`.
4. **İki dosyanın dönemleri örtüşmüyor.** Örtüşmeyen iş emirleri eşleştirmeye girmez, uyarı eklenir. → Görev 4 `test_donem_disi_is_emri`.
5. **Arıza sayısı 0 olan posta/ekip.** MTTR/MTBF `None` (raporda "—"), sıfıra bölme hatası olmaz. → Görev 2 `test_ariza_yoksa_none`.

---

## Dosya yapısı

```
bakim-analisti/
├── .claude-plugin/plugin.json
├── commands/hat-analizi.md
├── agents/bakim-analisti.md
├── skills/hat-analizi/
│   ├── SKILL.md
│   ├── ayarlar.json
│   └── scripts/{analiz.py, veri.py, hesap.py, rapor.py}
├── tests/{conftest.py, test_veri.py, test_hesap.py, test_eslesme.py, test_cli.py, test_rapor.py, test_gercek_veri.py}
├── requirements.txt          # pandas, openpyxl
├── requirements-dev.txt      # pytest
├── pytest.ini                # pythonpath = skills/hat-analizi/scripts
└── README.md
```

---

### Görev 1: Ayarlar ve veri okuma (`veri.py`)

**Dosyalar:**
- Oluştur: `skills/hat-analizi/ayarlar.json`, `skills/hat-analizi/scripts/veri.py`, `requirements.txt`, `requirements-dev.txt`, `pytest.ini`
- Test: `tests/conftest.py`, `tests/test_veri.py`

**Arayüzler:**
- Üretir:
  - `class VeriHatasi(Exception)`
  - `ayarlari_yukle(yol: Path | None = None) -> dict`: varsayılan olarak betiğin yanındaki `../ayarlar.json`; hesaplanan `takt_dk` ve `anomali_esigi_dk` anahtarlarını ekler.
  - `op_kimligi_zon(zon: str) -> str`
  - `op_kimligi_bakim(op_no: str) -> str`
  - `durus_oku(yol: Path) -> tuple[pd.DataFrame, list[str]]`: sütunlar `baslangic` (datetime), `bitis` (datetime), `sure_dk` (float), `posta` (str), `zon` (str), `modul` (str), `neden` (str), `vardiya` ("Sabah"/"Aksam"), `ekip` (Int64), `sayac` (int), `tarih` (date). İkinci değer uyarı listesidir.
  - `bakim_oku(yol: Path) -> tuple[pd.DataFrame, list[str]]`: sütunlar `is_emri`, `ariza_tipi`, `posta`, `ariza_tanimi`, `ariza_nedeni`, `yapilan_mudahale`, `baslama` (datetime), `bitis` (datetime), `mudahale_dk` (float), `durus_dk` (float), `kisi_sayisi` (int).
  - `dosya_bul(klasor: Path) -> tuple[Path, Path]`: içerik kontrolüyle en yeni (durus_xlsx, bakim_csv) çiftini bulur.
- `conftest.py` fikstürleri: `durus_xlsx(tmp_path, satirlar: list[dict]) -> Path` (6 meta satırı + 7. satırda başlık, `Smp99_Donnees` sayfası) ve `bakim_csv(tmp_path, satirlar: list[dict]) -> Path` (BOM'lu UTF-8, `;` ayraç, tümü tırnaklı). Gerçek dosyalardaki sütun adlarıyla birebir aynı.

- [ ] **Adım 1: Kurulum.** `pip install -r requirements.txt -r requirements-dev.txt`. `pytest.ini` içine `pythonpath = skills/hat-analizi/scripts` ve `testpaths = tests` yaz.
- [ ] **Adım 2: Başarısız testleri yaz** (`tests/test_veri.py`):

```python
@pytest.mark.parametrize("zon,beklenen", [
    (" 6611 - OP311_Z1", "OP311"), ("6209 - OP425_Zone3_1", "OP425"),
    ("6404 - OP550", "OP550"), (" 6411 - Konv_Z1", "Konv_Z1")])
def test_op_kimligi_zon(zon, beklenen): assert op_kimligi_zon(zon) == beklenen

@pytest.mark.parametrize("op,beklenen", [
    ("MM11 170", "OP170"), ("MM11 AGV", "MM11 AGV"), ("MM11 BAP 1230", "MM11 BAP 1230")])
def test_op_kimligi_bakim(op, beklenen): assert op_kimligi_bakim(op) == beklenen

def test_ayarlar_hesaplanan_degerler():
    a = ayarlari_yukle()
    assert a["net_sure_dk"] == 435 and a["anomali_esigi_dk"] == 348
    assert a["takt_dk"] == pytest.approx(435 / 519)

def test_durus_oku_alanlar(durus_xlsx):     # 2 satır + Posta'sı boş 1 özet satırı
    df, uyarilar = durus_oku(yol)
    assert len(df) == 2 and df.iloc[0].posta == "OP311"
    assert df.iloc[0].vardiya == "Sabah" and df.iloc[0].sure_dk == pytest.approx(0.067)

def test_durus_birim_uyarisi(durus_xlsx):  # Süre ≠ (Son−Saat) dk olan satırlar
    _, uyarilar = durus_oku(yol); assert any("birim" in u for u in uyarilar)

def test_bakim_oku_ad_tasimaz(bakim_csv):
    df, _ = bakim_oku(yol)
    assert "Müdahale Eden" not in df.columns and df.iloc[0].posta == "OP170"

def test_bakim_bozuk_satir(bakim_csv):     # 1 satırın Başlama Tarihi boş
    df, uyarilar = bakim_oku(yol)
    assert len(df) == 1 and any("atlandı" in u for u in uyarilar)

def test_yanlis_dosya_turu(bakim_csv):
    with pytest.raises(VeriHatasi, match="Smp99_Donnees"): durus_oku(bakim_csv_yolu)

def test_eksik_sutun(durus_xlsx):          # 'Zon' sütunu yok
    with pytest.raises(VeriHatasi, match="Zon"): durus_oku(yol)

def test_dosya_bul(tmp_path, durus_xlsx, bakim_csv):  # rastgele adlar, ilgisiz bir .csv daha
    assert dosya_bul(tmp_path) == (durus_yolu, bakim_yolu)
```

- [ ] **Adım 3: Testlerin başarısız olduğunu doğrula.** `pytest tests/test_veri.py -v` → ImportError/FAIL.
- [ ] **Adım 4: `veri.py`'yi uygula.**
  - Duruş: `pd.read_excel(yol, sheet_name="Smp99_Donnees", header=6)`; başlık sayfası yoksa ya da açılamıyorsa `VeriHatasi`.
  - `Saat` biçimi `%d.%m.%Y %H:%M:%S`, `Son` datetime gelir.
  - Birim kontrolü: `Son − Saat` farkı (dk) ile `Süre` arasındaki medyan mutlak fark 0,1 dk'yı geçerse uyarı ekle.
  - Bakım: `pd.read_csv(sep=";", encoding="utf-8-sig", dtype=str)`, tarih biçimi `%d.%m.%Y %H:%M`.
  - `dosya_bul`: `.xlsx`'te `Smp99_Donnees` sayfası, `.csv`'de ilk satırda `"İş Emri No"` aranır; adaylardan değişiklik zamanı en yeni olan seçilir. Aday yoksa `VeriHatasi`.
- [ ] **Adım 5: Testlerin geçtiğini doğrula.** `pytest tests/test_veri.py -v` → tümü PASS.
- [ ] **Adım 6: Commit.** `git add -A && git commit -m "feat: ayarlar ve veri okuma"`

---

### Görev 2: Vardiya özeti, ayıklama, KPI ve kırılımlar (`hesap.py`)

**Dosyalar:** Oluştur `skills/hat-analizi/scripts/hesap.py`; test `tests/test_hesap.py`

**Arayüzler:**
- Kullanır: Görev 1'deki `durus_oku` DataFrame'i ve `ayarlari_yukle` sözlüğü. Testler DataFrame'i doğrudan kurar (fikstür `durus_df(satirlar)`).
- Üretir:
  - `vardiya_ozeti(durus: pd.DataFrame, ayar: dict) -> pd.DataFrame`: her (tarih, vardiya) için bir satır; sütunlar `tarih`, `vardiya`, `ekip` (vardiyadaki en sık ekip), `uretim` (max sayaç), `ro` (uretim / 519), `calisildi` (uretim > 0).
  - `ayikla(durus, vardiyalar, ayar) -> tuple[pd.DataFrame, pd.DataFrame]`: (temiz, anomaliler). Çalışılmayan vardiyaların satırları ikisinde de yer almaz; anomaliler = `sure_dk > anomali_esigi_dk`. `temiz`'e `tur` sütunu eklenir: `"ariza"` (≥ 5 dk) veya `"mikro"`.
  - `kpi(temiz: pd.DataFrame, vardiya_sayisi: int, ayar) -> dict`: anahtarlar `ariza_sayisi`, `ariza_dk`, `mttr_dk`, `mtbf_dk`, `mikro_sayisi`, `mikro_dk`, `toplam_kayip_dk`, `kayip_motor`. Arıza yoksa `mttr_dk` ve `mtbf_dk` `None`.
  - `kirilim(temiz, vardiyalar, ayar, alan: Literal["posta","vardiya","ekip"]) -> list[dict]`: her eleman `{alan: değer, **kpi(...)}`, `toplam_kayip_dk`'ya göre azalan. `vardiya_sayisi` posta için tüm çalışılan vardiyalar; vardiya/ekip için o vardiya/ekibe ait çalışılan vardiyalar.
  - `ro_ozeti(vardiyalar, ayar) -> dict`: `ortalama_ro`, `hedefi_tutan_oran`, `calisilan_vardiya`, `calisilmayan: list[dict]`, `vardiya_ro: list[dict]` (tarih ISO metin, vardiya, ekip, uretim, ro).

- [ ] **Adım 1: Başarısız testleri yaz:**

```python
def test_vardiya_ozeti_ro(durus_df):            # Sabah sayaçları 100, 514 → uretim 514
    v = vardiya_ozeti(df, ayar); assert v.iloc[0].uretim == 514
    assert v.iloc[0].ro == pytest.approx(514 / 519)

def test_calisilmayan_vardiya_cikarilir(durus_df):  # sayaç hep 0 olan vardiya
    temiz, anom = ayikla(df, vardiya_ozeti(df, ayar), ayar)
    assert (temiz.tarih == gun0).sum() == 0 and len(anom) == 0

def test_anomali_ayrilir(durus_df):             # üretimli vardiyada 430 dk'lık duruş
    temiz, anom = ayikla(...); assert len(anom) == 1 and temiz.sure_dk.max() < 348

def test_esik_5dk_ariza(durus_df):              # 4.99 → mikro, 5.0 → ariza
    assert list(temiz.tur) == ["mikro", "ariza"]

def test_kpi_formulleri():                      # 2 vardiya; arızalar 10 ve 20 dk; mikrolar 1 ve 2 dk
    k = kpi(temiz, 2, ayar)
    assert k["mttr_dk"] == 15 and k["mtbf_dk"] == pytest.approx((2*435 - 30) / 2)
    assert k["toplam_kayip_dk"] == 33 and k["kayip_motor"] == pytest.approx(33 / (435/519))

def test_ariza_yoksa_none():                    # yalnızca mikro duruşlar
    k = kpi(temiz, 1, ayar); assert k["mttr_dk"] is None and k["mtbf_dk"] is None

def test_kirilim_ekip_vardiya_sayisi():         # Ekip 1 → 1 vardiya, Ekip 2 → 2 vardiya
    e = {r["ekip"]: r for r in kirilim(temiz, v, ayar, "ekip")}
    assert e[2]["mtbf_dk"] == pytest.approx((2*435 - 10) / 1)

def test_ro_ozeti_hedef_orani():                # ro'lar 0.995, 0.98 → oran 0.5
    assert ro_ozeti(v, ayar)["hedefi_tutan_oran"] == 0.5
```

- [ ] **Adım 2: Başarısız olduğunu doğrula.** `pytest tests/test_hesap.py -v` → FAIL.
- [ ] **Adım 3: Fonksiyonları uygula.** pandas `groupby` kullan; `calisildi` olmayan vardiyaları `merge` ile filtrele.
- [ ] **Adım 4: Geçtiğini doğrula.** `pytest tests/test_hesap.py -v` → PASS.
- [ ] **Adım 5: Commit.** `feat: Ro, ayıklama, MTTR/MTBF ve kırılımlar`

---

### Görev 3: Pareto ve mikro duruş analizi (`hesap.py`)

**Dosyalar:** Değiştir `hesap.py`; test `tests/test_hesap.py`

**Arayüzler:**
- Üretir:
  - `pareto(temiz, anahtar: list[str], ayar, ilk: int | None = None) -> list[dict]`: her eleman anahtar alanları + `toplam_kayip_dk`, `adet`, `ariza_dk`, `mikro_dk`, `kayip_motor`, `yuzde`, `kumulatif_yuzde`, `oncelik` (bool), `baskin_tur` (`"ariza"` | `"mikro"`, hangisinin dakikası büyükse).
  - `mikro_analiz(temiz, calisilan_saat: float, ilk: int = 10) -> list[dict]`: posta+neden bazında `adet`, `mikro_dk`, `saatte_adet`.

- [ ] **Adım 1: Başarısız testleri yaz:**

```python
def test_pareto_kesim():   # kayıplar A=50, B=30, C=15, D=5 → kümülatif 50, 80, 95, 100
    p = pareto(temiz, ["posta"], ayar)
    assert [r["posta"] for r in p if r["oncelik"]] == ["A", "B"]
    assert p[1]["kumulatif_yuzde"] == pytest.approx(80.0)

def test_pareto_ilk_eleman_her_zaman_oncelik():  # tek posta kaybın %90'ı
    assert pareto(...)[0]["oncelik"] is True

def test_baskin_tur():     # A: 1 arıza 6 dk + 10 mikro toplam 20 dk → "mikro"
    assert pareto(...)[0]["baskin_tur"] == "mikro"

def test_pareto_neden_ilk():
    assert len(pareto(temiz, ["posta", "neden"], ayar, ilk=10)) <= 10

def test_mikro_saatte_adet():  # 29 mikro duruş, 14.5 saat
    assert mikro_analiz(temiz, 14.5)[0]["saatte_adet"] == pytest.approx(2.0)
```

- [ ] **Adım 2: Başarısız olduğunu doğrula.**
- [ ] **Adım 3: Uygula.** Öncelik kuralı: bir satır, kendisinden **önceki** kümülatif yüzde `pareto_kesim × 100`'den küçükse önceliktir. Bu kural ilk satırı her zaman önceliğe alır, 80'i tam tutturan satırı da dahil eder.
- [ ] **Adım 4: Geçtiğini doğrula.**
- [ ] **Adım 5: Commit.** `feat: Pareto ve mikro duruş analizi`

---

### Görev 4: Bakım eşleşmesi ve kayıtsız kronikler (`hesap.py`)

**Dosyalar:** Değiştir `hesap.py`; test `tests/test_eslesme.py`

**Arayüzler:**
- Kullanır: Görev 1'deki `bakim_oku` çıktısı, Görev 2'deki `temiz`, Görev 3'teki `pareto` çıktısı.
- Üretir:
  - `bakim_eslestir(bakim, temiz, ayar, donem: tuple[pd.Timestamp, pd.Timestamp]) -> tuple[list[dict], list[str]]`: her iş emri için `is_emri`, `posta`, `ariza_tipi`, `ariza_tanimi`, `ariza_nedeni`, `yapilan_mudahale`, `baslama` (ISO), `hedef_neden` (str | None), `once` (int), `sonra` (int | None), `sinif` (`"Kalıcı"`, `"Kısmi"`, `"Kalıcı değil"`, `"Eşleşmedi"`, `"Takipte"`). İkinci değer uyarılar. `ariza_tipi == "Koruyucu Bakım"` olanlar listede yer almaz.
  - `kayitsiz_kronikler(pareto_neden: list[dict], bakim) -> list[dict]`: dönemde aynı postada hiç iş emri (koruyucu bakım dahil değil) açılmamış posta–neden çiftleri.
  - `koruyucu_bakim_ozeti(bakim) -> dict`: `adet`, `posta_sayisi`.

- [ ] **Adım 1: Başarısız testleri yaz** (gün 1–20 dönemi; iş emri gün 10 09:00–09:30, OP170):

```python
def test_hedef_neden_en_cok_kayip():  # pencerede (07:00–09:30) "röle" 12 dk, "sensör" 3 dk
    assert e[0]["hedef_neden"] == "röle"

def test_kalici():        # "röle" önce 4 kez (gün 3–9), sonra 0  → "Kalıcı"
def test_kismi():         # önce 4, sonra 2                        → "Kısmi"
def test_kalici_degil():  # önce 4, sonra 3                        → "Kalıcı değil"
def test_eslesmedi():     # pencerede OP170 duruşu yok             → "Eşleşmedi", hedef_neden None
def test_takipte():       # iş emri gün 15 (bitiş + 7 gün > dönem sonu) → "Takipte", sonra None
def test_koruyucu_bakim_haric():
    assert all(r["ariza_tipi"] != "Koruyucu Bakım" for r in e)

def test_donem_disi_is_emri():  # iş emri dönem başlangıcından önce
    e, uy = bakim_eslestir(...); assert e == [] and any("dönem" in u for u in uy)

def test_kayitsiz_kronik():     # pareto: (OP311, "YAG ESANJORU NOK"), (OP170, "röle"); bakımda sadece OP170
    assert [k["posta"] for k in kayitsiz_kronikler(p, bakim)] == ["OP311"]
```

- [ ] **Adım 2: Başarısız olduğunu doğrula.**
- [ ] **Adım 3: Uygula.** Önce penceresi `[baslama − 7 gün, baslama)`, sonra penceresi `(bitis, bitis + 7 gün]`. Takipte koşulu: `bitis + 7 gün > donem[1]`. Kısmi koşulu: `sonra <= once / 2`. `once == 0` iken `sonra == 0` ise Kalıcı, `sonra > 0` ise Kalıcı değil.
- [ ] **Adım 4: Geçtiğini doğrula.**
- [ ] **Adım 5: Commit.** `feat: bakım eşleşmesi ve kayıtsız kronik duruşlar`

---

### Görev 5: `analiz_et`, komut satırı `hesapla` ve gerçek veri duman testi

**Dosyalar:** Değiştir `hesap.py`; oluştur `scripts/analiz.py`; test `tests/test_cli.py`, `tests/test_gercek_veri.py`

**Arayüzler:**
- Üretir:
  - `analiz_et(durus, bakim, ayar, uyarilar: list[str]) -> dict`: `sonuc.json` yapısı. Üst düzey anahtarlar: `surum` (1), `donem` {`baslangic`, `bitis`}, `ayarlar`, `ozet` (`ro_ozeti` + hat `kpi`), `vardiya_ro`, `pareto_posta`, `pareto_neden` (ilk 10), `kirilim_posta` (ilk 15), `kirilim_vardiya`, `kirilim_ekip`, `mikro` (ilk 10), `bakim_eslesme`, `kayitsiz_kronikler`, `koruyucu_bakim`, `anomaliler` (tarih, vardiya, posta, neden, sure_dk), `calisilmayan_vardiyalar`, `uyarilar`. Tüm değerler JSON'a yazılabilir (tarihler ISO metin, NaN → `null`).
  - Komut satırı: `python analiz.py hesapla [--durus X] [--bakim Y] [--klasor K] --cikti DIR`. Yol verilmezse `dosya_bul(--klasor)`. `DIR/sonuc.json` yazar, stdout'a tek satırlık Türkçe özet basar (dönem, ortalama Ro, ilk öncelikli posta). `VeriHatasi`'nda stderr'e mesaj yazar ve 2 ile çıkar.

- [ ] **Adım 1: Başarısız testleri yaz:**

```python
def test_cli_hesapla(tmp_path, durus_xlsx, bakim_csv):
    r = subprocess.run([sys.executable, ANALIZ, "hesapla", "--durus", d, "--bakim", b, "--cikti", tmp_path/"o"], ...)
    assert r.returncode == 0
    s = json.loads((tmp_path/"o"/"sonuc.json").read_text("utf-8"))
    assert {"ozet", "pareto_posta", "bakim_eslesme", "anomaliler"} <= s.keys() and s["surum"] == 1

def test_cli_hata_kodu(tmp_path, bakim_csv):    # CSV --durus olarak verilmiş
    r = subprocess.run([... "--durus", b, "--bakim", b ...]); assert r.returncode == 2 and "Smp99_Donnees" in r.stderr

def test_json_ad_icermez(...):                   # bakım fikstüründe "Oktay ÇEŞMECİ" geçiyor
    assert "ÇEŞMECİ" not in (tmp_path/"o"/"sonuc.json").read_text("utf-8")
```

`tests/test_gercek_veri.py`: `BAKIM_DURUS` ve `BAKIM_DEFTER` ortam değişkenleri yoksa `pytest.skip`. Varsa:

```python
assert toplam_satir == 14296
assert {(c["tarih"], c["vardiya"]) for c in s["calisilmayan_vardiyalar"]} == {
    ("2026-10-17","Sabah"), ("2026-10-17","Aksam"), ("2026-10-27","Aksam"),
    ("2026-10-28","Aksam"), ("2026-10-29","Aksam")}
assert ro_bul(s, "2026-10-05", "Sabah")["uretim"] == 521
assert max(s["kirilim_posta"], key=lambda r: r["ariza_sayisi"] + r["mikro_sayisi"])["posta"] == "OP311"
assert all(a["sure_dk"] > 348 for a in s["anomaliler"]) and any(a["posta"] == "OP550" for a in s["anomaliler"])
```

(`toplam_satir` için `analiz_et` çıktısına `ozet.ham_satir` eklenir.)

- [ ] **Adım 2: Başarısız olduğunu doğrula.**
- [ ] **Adım 3: Uygula.** `analiz.py`, `sys.path`'e kendi klasörünü ekler, `argparse` alt komutlarını kullanır. `donem` duruş verisinin min/max'ıdır. `pandas`/`openpyxl` içe aktarılamazsa `pip install -r requirements.txt` önerisiyle 2 ile çıkar. Tarihi ayrıştırılamayan duruş satırları atlanır ve sayıları uyarıya yazılır. Tüm uyarılar (`durus_oku`, `bakim_oku`, `bakim_eslestir`) `uyarilar`'da toplanır.
- [ ] **Adım 4: Geçtiğini doğrula.** `pytest -v`. Ardından gerçek veriyle çalıştır:
  `BAKIM_DURUS=/root/.claude/uploads/.../960b7059-SMP_EK_M.xlsx BAKIM_DEFTER=/root/.claude/uploads/.../3f0c2cdf-bakim_ariza_defteri_2026-11-02_1.csv pytest tests/test_gercek_veri.py -v` → PASS.
- [ ] **Adım 5: Commit.** `feat: analiz_et ve hesapla komutu`

---

### Görev 6: HTML rapor (`rapor.py`) ve `rapor` komutu

**Dosyalar:** Oluştur `scripts/rapor.py`; değiştir `analiz.py`; test `tests/test_rapor.py`

**Arayüzler:**
- Kullanır: Görev 5'teki `sonuc.json` yapısı.
- Üretir:
  - `AKSIYON_ALANLARI = ("oncelik","posta","sorun","kanit","aksiyon_turu","onerilen_aksiyon","beklenen_kazanc_motor_vardiya","sorumlu_onerisi")`
  - `AKSIYON_TURLERI = ("hızlı düzeltme","kalıcı çözüm","koruyucu bakım","otonom bakım","veri-sensör kontrolü")`
  - `aksiyon_dogrula(aksiyonlar: list[dict]) -> list[str]`: hata mesajları; boş liste geçerli demektir.
  - `rapor_olustur(sonuc: dict, aksiyonlar: list[dict] | None) -> str`: tam HTML.
  - Komut satırı: `python analiz.py rapor --sonuc S [--aksiyonlar A] --cikti DIR` → `DIR/rapor.html`. Doğrulama hatası varsa mesajları basar ve 2 ile çıkar.

- [ ] **Adım 1: Başarısız testleri yaz** (fikstür `ornek_sonuc`: Görev 5'in fikstür verisiyle üretilmiş sözlük):

```python
def test_bolumler(ornek_sonuc):
    h = rapor_olustur(ornek_sonuc, ornek_aksiyonlar)
    for b in ["Özet", "Ro Trendi", "Darboğaz", "MTTR / MTBF", "Mikro Duruşlar",
              "Bakım Eşleşmesi", "Aksiyon Listesi", "Veri Anomalileri"]: assert f">{b}<" in h

def test_html_kacis(ornek_sonuc):   # ariza_tanimi = 'BASINÇ <-1...5 BAR> & "test"'
    h = rapor_olustur(...); assert "<-1...5" not in h and "&lt;-1...5 BAR&gt; &amp;" in h

def test_dis_kaynak_yok(ornek_sonuc):
    h = rapor_olustur(ornek_sonuc, None)
    assert "http://" not in h and "https://" not in h and "<svg" in h

def test_aksiyonsuz_rapor(ornek_sonuc):
    assert "Aksiyon listesi henüz hazırlanmadı" in rapor_olustur(ornek_sonuc, None)

def test_none_tire(ornek_sonuc):    # mttr_dk None olan posta
    assert "—" in rapor_olustur(...)

def test_aksiyon_dogrula():
    assert aksiyon_dogrula([gecerli]) == []
    assert any("aksiyon_turu" in m for m in aksiyon_dogrula([{**gecerli, "aksiyon_turu": "dua"}]))
    assert any("posta" in m for m in aksiyon_dogrula([{k: v for k, v in gecerli.items() if k != "posta"}]))

def test_cli_rapor(tmp_path, ...):  # hesapla → rapor, returncode 0, rapor.html var
```

- [ ] **Adım 2: Başarısız olduğunu doğrula.**
- [ ] **Adım 3: Uygula.**
  - Tüm metinler `html.escape` ile kaçışlanır.
  - CSS değişkenleri `:root`'ta, koyu tema `@media (prefers-color-scheme: dark)` ile verilir. Tablolar dar ekranda `overflow-x:auto` kapsayıcıda durur. `@media print` desteklenir.
  - SVG yardımcıları:
    - `_cubuk_grafik(etiketler, degerler, hedef: float | None, renkler) -> str`: Ro trendi için; %99 hedef çizgisi var, Sabah ve Akşam ayrı renkte.
    - `_pareto_grafik(satirlar) -> str`: çubuk + kümülatif çizgi + %80 kesim çizgisi.
  - Bakım eşleşmesi bölümü "Kalıcı değil" ve "Kısmi" satırlarını öne alır. Kayıp motor tahmininin yanına ara stok notu düşülür.
- [ ] **Adım 4: Geçtiğini doğrula.** Gerçek veriyle `hesapla` + `rapor` çalıştır ve `rapor.html`'i Playwright ile 390 px ve 1280 px genişlikte ekran görüntüsü alarak gözle kontrol et: yatay sayfa kaydırması yok, grafikler görünüyor.
- [ ] **Adım 5: Commit.** `feat: HTML rapor`

---

### Görev 7: Eklenti parçaları (manifest, komut, ajan, skill, README) ve uçtan uca deneme

**Dosyalar:** Oluştur `.claude-plugin/plugin.json`, `commands/hat-analizi.md`, `agents/bakim-analisti.md`, `skills/hat-analizi/SKILL.md`, `README.md`

**Arayüzler:**
- Kullanır: `analiz.py hesapla|rapor` komut satırı, `sonuc.json` anahtarları, `AKSIYON_ALANLARI`/`AKSIYON_TURLERI`.
- Yollar eklenti köküne göre `${CLAUDE_PLUGIN_ROOT}/skills/hat-analizi/scripts/analiz.py` ile verilir.

- [ ] **Adım 1: `plugin.json`:** `{"name": "bakim-analisti", "version": "0.1.0", "description": "Motor montaj hattı duruş ve bakım analizleri: Ro, MTTR/MTBF, Pareto, kalıcı çözüm takibi"}`.
- [ ] **Adım 2: `SKILL.md`.** Frontmatter `name: hat-analizi` ve "SMP99 duruş Excel'i ve bakım arıza defteri CSV'si analiz edilirken kullan" anlamında bir açıklama. Gövdede:
  - spec §4–5'in kuralları (özet halinde),
  - komut satırı kullanımı,
  - `sonuc.json` anahtarlarının bir satırlık açıklamaları,
  - `aksiyonlar.json` şeması (alanlar + izinli türler),
  - "sayıları yalnızca `sonuc.json`'dan al" kuralı,
  - takip sorularında ham veriye bakmak için örnek bir pandas komutu (`veri.durus_oku` ile).
- [ ] **Adım 3: `agents/bakim-analisti.md`.**
  - Frontmatter: `name: bakim-analisti`, Türkçe `description` (hat analizi, MTTR/MTBF, kök neden, aksiyon önerisi istendiğinde), `tools: Read, Write, Bash, Glob, Grep`.
  - Gövdede spec §6'daki rol, hat parametreleri (`ayarlar.json`'dan okunduğu notuyla), kurallar ve yöntemler (TPM, otonom bakım, 5 Neden, Ishikawa) yer alır.
  - Kanıtsız öneri yasağı ve aksiyon listesi kuralları: en fazla 10 madde, öncelik Pareto ve kayıp motora göre, her maddede sayısal kanıt.
  - Mikro duruş ağırlıklı postalara proses/sensör/otonom bakım aksiyonu, arıza ağırlıklılara kalıcı çözüm/koruyucu bakım; "Kalıcı değil" iş emirlerine 5 Neden önerisi; kayıtsız kroniklere iş emri açılması önerisi.
- [ ] **Adım 4: `commands/hat-analizi.md`.**
  - Frontmatter: `description`, `argument-hint: [duruş.xlsx] [bakım.csv]`.
  - Akış:
    1. Argüman yoksa `--klasor` olarak yükleme klasörü (`~/.claude/uploads` altında en yenisi) ya da çalışma klasörü kullanılır.
    2. `hesapla` çalışır, çıktı `bakim-analizleri/<YYYY-MM>/` klasörüne yazılır.
    3. `bakim-analisti` ajanı `sonuc.json`'u okur ve `aksiyonlar.json` yazar.
    4. `rapor` çalışır. Doğrulama hatası varsa ajan aksiyonları düzeltir.
    5. Ortam destekliyorsa rapor paylaşılabilir sayfa olarak yayınlanır.
    6. Sohbette Türkçe kısa özet verilir: Ro, ilk 3 öncelik ve rapor yolu.
- [ ] **Adım 5: Doğrula.** `claude plugin validate /home/user/bakim-analisti` → hata yok.
- [ ] **Adım 6: `README.md`.** Kurulum (`pip install -r requirements.txt`, `claude --plugin-dir`), kullanım, ayarlar ve gizlilik notu (gerçek veriler depoya girmez).
- [ ] **Adım 7: Uçtan uca deneme.**
  - Gerçek Ekim dosyalarıyla `hesapla` → ajan rolüyle `aksiyonlar.json` → `rapor` akışını çalıştır.
  - `aksiyon_dogrula` boş dönmeli, rapor 8 bölümü içermeli.
  - Ajanın aksiyonlarındaki her sayı `sonuc.json`'da bulunmalı (elle kontrol).
  - `pytest -v` tümü PASS.
- [ ] **Adım 8: Commit.** `feat: eklenti manifesti, Bakım Analisti ajanı, /hat-analizi komutu`
