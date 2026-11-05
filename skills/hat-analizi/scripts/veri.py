"""Ayarları ve iki girdi dosyasını (SMP99 duruş Excel'i, bakım arıza defteri CSV'si) okur."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

AYAR_YOLU = Path(__file__).resolve().parent.parent / "ayarlar.json"
DURUS_SAYFA = "Smp99_Donnees"
DURUS_BASLIK_SATIRI = 6  # 0 tabanlı: 7. satır
DURUS_SUTUNLARI = ["Saat", "Son", "Süre", "Zon", "Modül", "Durus nedeni", "Posta",
                   "Kapanistaki imalat sayisi"]
BAKIM_SUTUNLARI = ["İş Emri No", "Arıza Tipi", "OP No", "Arıza Tanımı", "Arıza Nedeni",
                   "Yapılan Müdahale", "Başlama Tarihi", "Bitiş Tarihi",
                   "Toplam Müdahale Süresi", "Duruş Süresi", "Kişi Sayısı"]


class VeriHatasi(Exception):
    """Girdi dosyası okunamadığında ya da beklenen biçimde olmadığında."""


def ayarlari_yukle(yol: Path | None = None) -> dict:
    with open(yol or AYAR_YOLU, encoding="utf-8") as f:
        ayar = json.load(f)
    ayar["takt_dk"] = ayar["net_sure_dk"] / ayar["vardiya_hedefi"]
    ayar["anomali_esigi_dk"] = ayar["net_sure_dk"] * ayar["anomali_orani"]
    return ayar


def op_kimligi_zon(zon: str) -> str:
    zon = str(zon).strip()
    m = re.search(r"OP(\d+)", zon)
    if m:
        return f"OP{int(m.group(1))}"
    return zon.split(" - ", 1)[-1].strip()


def op_kimligi_bakim(op_no: str) -> str:
    op_no = str(op_no).strip()
    m = re.fullmatch(r"MM11\s+(\d+)", op_no)
    return f"OP{int(m.group(1))}" if m else op_no


def _eksik_kontrol(df: pd.DataFrame, gerekli: list[str], dosya: str) -> None:
    eksik = [c for c in gerekli if c not in df.columns]
    if eksik:
        raise VeriHatasi(f"{dosya} dosyasında beklenen sütun(lar) yok: {', '.join(eksik)}. "
                         f"Beklenen sütunlar: {', '.join(gerekli)}")


def durus_oku(yol: Path) -> tuple[pd.DataFrame, list[str]]:
    yol = Path(yol)
    try:
        ham = pd.read_excel(yol, sheet_name=DURUS_SAYFA, header=DURUS_BASLIK_SATIRI)
    except Exception as e:  # dosya Excel değil ya da sayfa yok
        raise VeriHatasi(f"Duruş dosyası okunamadı ({yol.name}): '{DURUS_SAYFA}' sayfası olan bir "
                         f"SMP99 Excel çıktısı bekleniyor (başlık 7. satırda). Beklenen sütunlar: "
                         f"{', '.join(DURUS_SUTUNLARI)}. Ayrıntı: {e}") from e
    _eksik_kontrol(ham, DURUS_SUTUNLARI, "Duruş")
    uyarilar: list[str] = []
    ham = ham[ham["Posta"].notna()].copy()

    baslangic = pd.to_datetime(ham["Saat"], format="%d.%m.%Y %H:%M:%S", errors="coerce")
    bozuk = baslangic.isna()
    if bozuk.any():
        uyarilar.append(f"Duruş dosyasında tarihi okunamayan {int(bozuk.sum())} satır atlandı.")
    ham, baslangic = ham[~bozuk], baslangic[~bozuk]

    df = pd.DataFrame({
        "baslangic": baslangic,
        "bitis": pd.to_datetime(ham["Son"], errors="coerce"),
        "sure_dk": pd.to_numeric(ham["Süre"], errors="coerce").fillna(0.0).astype(float),
        "zon": ham["Zon"].astype(str).str.strip(),
        "modul": ham["Modül"].astype(str).str.strip(),
        "neden": ham["Durus nedeni"].fillna("").astype(str).str.strip(),
        "vardiya": ham["Posta"].astype(str).str.strip(),
        "sayac": pd.to_numeric(ham["Kapanistaki imalat sayisi"], errors="coerce")
                   .fillna(0).astype(int),
    }).reset_index(drop=True)
    df.insert(3, "posta", df["zon"].map(op_kimligi_zon))
    df["tarih"] = df["baslangic"].dt.date

    fark = ((df["bitis"] - df["baslangic"]).dt.total_seconds() / 60 - df["sure_dk"]).abs().dropna()
    if len(fark) and fark.median() > 0.1:
        uyarilar.append("Süre birimi kontrolü: 'Süre' değerleri başlangıç–bitiş farkıyla (dakika) "
                        "uyuşmuyor. Dosyadaki süre birimini kontrol edin.")
    return df, uyarilar


def bakim_oku(yol: Path) -> tuple[pd.DataFrame, list[str]]:
    yol = Path(yol)
    try:
        ham = pd.read_csv(yol, sep=";", encoding="utf-8-sig", dtype=str).fillna("")
    except Exception as e:
        raise VeriHatasi(f"Bakım defteri okunamadı ({yol.name}): ';' ayraçlı UTF-8 CSV bekleniyor. "
                         f"Beklenen sütunlar: {', '.join(BAKIM_SUTUNLARI)}. Ayrıntı: {e}") from e
    _eksik_kontrol(ham, BAKIM_SUTUNLARI, "Bakım defteri")
    uyarilar: list[str] = []
    baslama = pd.to_datetime(ham["Başlama Tarihi"], format="%d.%m.%Y %H:%M", errors="coerce")
    bitis = pd.to_datetime(ham["Bitiş Tarihi"], format="%d.%m.%Y %H:%M", errors="coerce")
    bozuk = baslama.isna() | bitis.isna() | (ham["OP No"].str.strip() == "")
    if bozuk.any():
        uyarilar.append(f"Bakım defterinde tarihi ya da OP No'su eksik {int(bozuk.sum())} "
                        f"satır atlandı.")
    ham, baslama, bitis = ham[~bozuk], baslama[~bozuk], bitis[~bozuk]

    def sayi(s):
        return pd.to_numeric(s.str.replace(",", "."), errors="coerce").fillna(0)

    df = pd.DataFrame({
        "is_emri": ham["İş Emri No"].str.strip(),
        "ariza_tipi": ham["Arıza Tipi"].str.strip(),
        "posta": ham["OP No"].map(op_kimligi_bakim),
        "ariza_tanimi": ham["Arıza Tanımı"].str.strip(),
        "ariza_nedeni": ham["Arıza Nedeni"].str.strip(),
        "yapilan_mudahale": ham["Yapılan Müdahale"].str.strip(),
        "baslama": baslama,
        "bitis": bitis,
        "mudahale_dk": sayi(ham["Toplam Müdahale Süresi"]).astype(float),
        "durus_dk": sayi(ham["Duruş Süresi"]).astype(float),
        "kisi_sayisi": sayi(ham["Kişi Sayısı"]).astype(int),
    }).reset_index(drop=True)
    return df, uyarilar


def _durus_dosyasi_mi(yol: Path) -> bool:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(yol, read_only=True)
        try:
            return DURUS_SAYFA in wb.sheetnames
        finally:
            wb.close()
    except Exception:
        return False


def _bakim_dosyasi_mi(yol: Path) -> bool:
    try:
        with open(yol, encoding="utf-8-sig") as f:
            return "İş Emri No" in f.readline()
    except Exception:
        return False


def dosya_bul(klasor: Path) -> tuple[Path, Path]:
    klasor = Path(klasor)
    def en_yeni(desen, kontrol):
        adaylar = [p for p in klasor.glob(desen) if p.is_file() and kontrol(p)]
        return max(adaylar, key=lambda p: p.stat().st_mtime) if adaylar else None
    durus = en_yeni("*.xlsx", _durus_dosyasi_mi)
    bakim = en_yeni("*.csv", _bakim_dosyasi_mi)
    if durus is None or bakim is None:
        eksik = [ad for ad, p in (("SMP99 duruş Excel'i", durus), ("bakım defteri CSV'si", bakim))
                 if p is None]
        raise VeriHatasi(f"{klasor} klasöründe bulunamadı: {', '.join(eksik)}.")
    return durus, bakim
