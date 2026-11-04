"""Test verisi üreticileri: gerçek dosyalarla aynı başlıklara sahip küçük dosyalar yazar."""
import csv
from datetime import datetime, timedelta
from pathlib import Path

import openpyxl

DURUS_BASLIKLARI = [
    None, "E", "Saat", "Tip", "P", "D", "Süre", "Zon", "Modül", "Detaylı yer belirleme",
    "Durus nedeni", "OPE", "Yorum", "Ilk tip", "Son", "Posta", "Ekip", "Çesitlilik",
    "Çesitlilik mnemo", "Support", "Support 2", "Algilanan Modül", "Olay", "Tanimli Modül",
    "Detayli yer saptama kodu", "Neden", "Durus kodu", "Blok sayisi", "Durus aileleri",
    "Alt durus grubu", "Üretim Kayibi", "Robot tipi", "Müdahale seviyesi", "Diger",
    "NPT Baslangiç", "Robot hata No", "PJI", "İslem kodu", "Kapanistaki imalat sayisi", "N° OT",
]

BAKIM_BASLIKLARI = [
    "İş Emri No", "Arıza Tipi", "Arıza Kodu", "Sebep", "Ana Etken", "Makine Tesis No",
    "OP No", "Arıza Tanımı", "Arıza Nedeni", "Yapılan Müdahale", "Başlama Tarihi",
    "Toplam Müdahale Süresi", "Bitiş Tarihi", "Duruş Süresi", "Müdahale Eden",
    "Kişi Sayısı", "Kişi Bazlı Süre", "Sonuç",
]


def durus_satir(saat="05.10.2026 08:00:00", sure=1.0, zon=" 6611 - OP311_Z1", neden="NEDEN",
                posta="Sabah", ekip=1, sayac=100, modul="  3 - OPERATOR - Operator Yonetimi",
                son=None):
    bas = datetime.strptime(saat, "%d.%m.%Y %H:%M:%S")
    return {
        "E": "F", "Saat": saat, "Tip": "APP", "P": "Z", "D": "A", "Süre": sure, "Zon": zon,
        "Modül": modul, "Durus nedeni": neden, "Ilk tip": "APP",
        "Son": son if son is not None else bas + timedelta(minutes=sure),
        "Posta": posta, "Ekip": ekip, "Kapanistaki imalat sayisi": sayac,
    }


def durus_xlsx_yaz(yol: Path, satirlar, basliklar=None, sayfa="Smp99_Donnees") -> Path:
    basliklar = basliklar or DURUS_BASLIKLARI
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sayfa
    meta = ["Bursa_UM) - U (Isleme) - Durus gazetesi", "Alan : HB MOTOR", "Süre : M 2026 Ekim",
            "Posta : i", "Blok tipi : APP", "Durus blogu"]
    for m in meta:
        ws.append([None, m])
    ws.append(basliklar)
    for s in satirlar:
        ws.append([s.get(b) if b else None for b in basliklar])
    wb.save(yol)
    return yol


def bakim_satir(is_emri="1", tip="Elektronik", op="MM11 170", baslama="10.10.2026 09:00",
                bitis="10.10.2026 09:30", tanim="Arıza", neden="Neden", mudahale="Müdahale",
                eden="23672 Oktay ÇEŞMECİ", kisi="1"):
    return {
        "İş Emri No": is_emri, "Arıza Tipi": tip, "Arıza Kodu": "01", "Sebep": "C2",
        "Ana Etken": "", "Makine Tesis No": "6402 ME", "OP No": op, "Arıza Tanımı": tanim,
        "Arıza Nedeni": neden, "Yapılan Müdahale": mudahale, "Başlama Tarihi": baslama,
        "Toplam Müdahale Süresi": "30", "Bitiş Tarihi": bitis, "Duruş Süresi": "10",
        "Müdahale Eden": eden, "Kişi Sayısı": kisi, "Kişi Bazlı Süre": "30", "Sonuç": "tamamlandi",
    }


def bakim_csv_yaz(yol: Path, satirlar) -> Path:
    with open(yol, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL)
        w.writerow(BAKIM_BASLIKLARI)
        for s in satirlar:
            w.writerow([s.get(b, "") for b in BAKIM_BASLIKLARI])
    return yol


def durus_df(satirlar):
    """durus_oku çıktısıyla aynı sütunlara sahip DataFrame.

    Her satır: (zaman 'YYYY-MM-DD HH:MM', sure_dk, posta, neden, vardiya, ekip, sayac)
    """
    import pandas as pd
    kayitlar = []
    for zaman, sure, posta, neden, vardiya, ekip, sayac in satirlar:
        bas = pd.Timestamp(zaman)
        kayitlar.append({
            "baslangic": bas, "bitis": bas + pd.Timedelta(minutes=sure), "sure_dk": float(sure),
            "posta": posta, "zon": posta, "modul": "M", "neden": neden, "vardiya": vardiya,
            "ekip": ekip, "sayac": sayac, "tarih": bas.date(),
        })
    df = pd.DataFrame(kayitlar)
    df["ekip"] = df["ekip"].astype("Int64")
    return df
