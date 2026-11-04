import os
import time

import pytest

from veri import (VeriHatasi, ayarlari_yukle, bakim_oku, dosya_bul, durus_oku,
                  op_kimligi_bakim, op_kimligi_zon)
from yardimci import (DURUS_BASLIKLARI, bakim_csv_yaz, bakim_satir, durus_satir,
                      durus_xlsx_yaz)


@pytest.mark.parametrize("zon,beklenen", [
    (" 6611 - OP311_Z1", "OP311"), ("6209 - OP425_Zone3_1", "OP425"),
    ("6404 - OP550", "OP550"), (" 6411 - Konv_Z1", "Konv_Z1")])
def test_op_kimligi_zon(zon, beklenen):
    assert op_kimligi_zon(zon) == beklenen


@pytest.mark.parametrize("op,beklenen", [
    ("MM11 170", "OP170"), ("MM11 AGV", "MM11 AGV"), ("MM11 BAP 1230", "MM11 BAP 1230")])
def test_op_kimligi_bakim(op, beklenen):
    assert op_kimligi_bakim(op) == beklenen


def test_ayarlar_hesaplanan_degerler():
    a = ayarlari_yukle()
    assert a["net_sure_dk"] == 435 and a["anomali_esigi_dk"] == 348
    assert a["takt_dk"] == pytest.approx(435 / 519)


def test_durus_oku_alanlar(tmp_path):
    yol = durus_xlsx_yaz(tmp_path / "d.xlsx", [
        durus_satir(saat="05.10.2026 08:00:00", sure=0.067),
        durus_satir(saat="05.10.2026 16:00:00", sure=2.0, posta="Aksam", ekip=2,
                    zon=" 6411 - Konv_Z1"),
        {"Süre": 99.0},  # Posta'sı boş özet satırı
    ])
    df, uyarilar = durus_oku(yol)
    assert len(df) == 2
    r = df.iloc[0]
    assert r.posta == "OP311" and r.vardiya == "Sabah" and r.ekip == 1
    assert r.sure_dk == pytest.approx(0.067) and r.sayac == 100
    assert str(r.tarih) == "2026-10-05"
    assert df.iloc[1].posta == "Konv_Z1"
    assert uyarilar == []


def test_durus_birim_uyarisi(tmp_path):
    from datetime import datetime, timedelta
    satirlar = []
    for i in range(5):  # Süre 100 kat büyük yazılmış (1/100 dk gibi)
        s = durus_satir(saat=f"05.10.2026 08:0{i}:00", sure=50.0)
        s["Son"] = datetime(2026, 10, 5, 8, i) + timedelta(minutes=0.5)
        satirlar.append(s)
    _, uyarilar = durus_oku(durus_xlsx_yaz(tmp_path / "d.xlsx", satirlar))
    assert any("birim" in u for u in uyarilar)


def test_durus_bozuk_tarih_atlanir(tmp_path):
    s = durus_satir()
    s["Saat"] = "bozuk"
    df, uyarilar = durus_oku(durus_xlsx_yaz(tmp_path / "d.xlsx", [durus_satir(), s]))
    assert len(df) == 1 and any("atlandı" in u for u in uyarilar)


def test_bakim_oku_ad_tasimaz(tmp_path):
    df, _ = bakim_oku(bakim_csv_yaz(tmp_path / "b.csv", [bakim_satir()]))
    assert "Müdahale Eden" not in df.columns
    assert not df.astype(str).apply(lambda c: c.str.contains("ÇEŞMECİ")).any().any()
    r = df.iloc[0]
    assert r.posta == "OP170" and r.kisi_sayisi == 1 and r.mudahale_dk == 30
    assert str(r.baslama) == "2026-10-10 09:00:00"


def test_bakim_bozuk_satir(tmp_path):
    yol = bakim_csv_yaz(tmp_path / "b.csv", [bakim_satir(), bakim_satir(is_emri="2", baslama="")])
    df, uyarilar = bakim_oku(yol)
    assert len(df) == 1 and any("atlandı" in u for u in uyarilar)


def test_yanlis_dosya_turu(tmp_path):
    yol = bakim_csv_yaz(tmp_path / "b.csv", [bakim_satir()])
    with pytest.raises(VeriHatasi, match="Smp99_Donnees"):
        durus_oku(yol)


def test_bakim_yanlis_dosya(tmp_path):
    yol = durus_xlsx_yaz(tmp_path / "d.xlsx", [durus_satir()])
    with pytest.raises(VeriHatasi, match="İş Emri No"):
        bakim_oku(yol)


def test_eksik_sutun(tmp_path):
    basliklar = [b for b in DURUS_BASLIKLARI if b != "Zon"]
    yol = durus_xlsx_yaz(tmp_path / "d.xlsx", [durus_satir()], basliklar=basliklar)
    with pytest.raises(VeriHatasi, match="Zon"):
        durus_oku(yol)


def test_dosya_bul(tmp_path):
    eski = durus_xlsx_yaz(tmp_path / "eski.xlsx", [durus_satir()])
    os.utime(eski, (time.time() - 100, time.time() - 100))
    d = durus_xlsx_yaz(tmp_path / "a1b2-SMP.xlsx", [durus_satir()])
    b = bakim_csv_yaz(tmp_path / "c3d4-defter.csv", [bakim_satir()])
    (tmp_path / "ilgisiz.csv").write_text("a;b\n1;2\n", encoding="utf-8")
    assert dosya_bul(tmp_path) == (d, b)


def test_dosya_bul_bulamazsa(tmp_path):
    with pytest.raises(VeriHatasi):
        dosya_bul(tmp_path)
