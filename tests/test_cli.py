import json
import subprocess
import sys
from pathlib import Path

import pytest

from yardimci import bakim_csv_yaz, bakim_satir, durus_satir, durus_xlsx_yaz

ANALIZ = str(Path(__file__).resolve().parent.parent / "skills/hat-analizi/scripts/analiz.py")


@pytest.fixture
def girdiler(tmp_path):
    d = durus_xlsx_yaz(tmp_path / "d.xlsx", [
        durus_satir(saat="05.10.2026 08:00:00", sure=12, zon=" 6100 - OP170", neden="röle", sayac=300),
        durus_satir(saat="05.10.2026 09:00:00", sure=0.5, sayac=515),
        durus_satir(saat="05.10.2026 16:00:00", sure=6, posta="Aksam", ekip=2, sayac=505),
        durus_satir(saat="06.10.2026 07:35:00", sure=430, zon=" 6404 - OP550", neden="kofre", sayac=520),
        durus_satir(saat="06.10.2026 09:00:00", sure=1, sayac=520),
    ])
    b = bakim_csv_yaz(tmp_path / "b.csv", [
        bakim_satir(baslama="05.10.2026 09:00", bitis="05.10.2026 09:30",
                    tanim='BASINÇ <-1...5 BAR> & "test"'),
        bakim_satir(is_emri="2", tip="Koruyucu Bakım", op="MM11 311")])
    return tmp_path, d, b


def calistir(*args):
    return subprocess.run([sys.executable, ANALIZ, *map(str, args)], capture_output=True,
                          text=True, encoding="utf-8")


def test_cli_hesapla(girdiler):
    k, d, b = girdiler
    r = calistir("hesapla", "--durus", d, "--bakim", b, "--cikti", k / "o")
    assert r.returncode == 0, r.stderr
    s = json.loads((k / "o" / "sonuc.json").read_text("utf-8"))
    assert {"ozet", "vardiya_ro", "pareto_posta", "pareto_neden", "kirilim_posta",
            "kirilim_vardiya", "kirilim_ekip", "mikro", "bakim_eslesme", "kayitsiz_kronikler",
            "koruyucu_bakim", "anomaliler", "calisilmayan_vardiyalar", "uyarilar",
            "donem", "ayarlar"} <= s.keys()
    assert s["surum"] == 1 and s["ozet"]["ham_satir"] == 5
    assert s["ozet"]["calisilan_vardiya"] == 3 and s["anomaliler"][0]["posta"] == "OP550"
    assert s["bakim_eslesme"][0]["hedef_neden"] == "röle"
    assert s["ozet"]["gercek_kayip_motor"] == 4 + 14  # 519−515, 519−505; 520 hedef üstü
    assert s["pareto_posta"][0]["kayip_motor"] is not None
    assert s["koruyucu_bakim"] == {"adet": 1, "posta_sayisi": 1}
    assert "Ro" in r.stdout


def test_cli_klasorden_bulur(girdiler):
    k, d, b = girdiler
    r = calistir("hesapla", "--klasor", k, "--cikti", k / "o")
    assert r.returncode == 0, r.stderr


def test_cli_hata_kodu(girdiler):
    k, d, b = girdiler
    r = calistir("hesapla", "--durus", b, "--bakim", b, "--cikti", k / "o")
    assert r.returncode == 2 and "Smp99_Donnees" in r.stderr and "Traceback" not in r.stderr


def test_json_ad_icermez(girdiler):
    k, d, b = girdiler
    calistir("hesapla", "--durus", d, "--bakim", b, "--cikti", k / "o")
    assert "ÇEŞMECİ" not in (k / "o" / "sonuc.json").read_text("utf-8")


def test_cli_varsayilan_cikti_donem_ayi(girdiler, tmp_path, monkeypatch):
    k, d, b = girdiler
    r = subprocess.run([sys.executable, ANALIZ, "hesapla", "--durus", str(d), "--bakim", str(b)],
                       capture_output=True, text=True, encoding="utf-8", cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "bakim-analizleri" / "2026-10" / "sonuc.json").exists()


def test_cli_tek_dosya_verilirse_hata(girdiler):
    k, d, b = girdiler
    r = calistir("hesapla", "--durus", d, "--cikti", k / "o")
    assert r.returncode == 2 and "--bakim" in r.stderr


def test_cli_kullanilan_dosyalari_yazar(girdiler):
    k, d, b = girdiler
    r = calistir("hesapla", "--klasor", k, "--cikti", k / "o")
    assert d.name in r.stdout and b.name in r.stdout


def test_cli_bozuk_aksiyon_json(girdiler, tmp_path):
    k, d, b = girdiler
    calistir("hesapla", "--durus", d, "--bakim", b, "--cikti", k / "o")
    a = tmp_path / "aksiyonlar.json"
    a.write_text("[{bozuk", "utf-8")
    r = calistir("rapor", "--sonuc", k / "o" / "sonuc.json", "--aksiyonlar", a, "--cikti", k / "o")
    assert r.returncode == 2 and "aksiyonlar.json" in r.stderr and "Traceback" not in r.stderr


def test_cli_sonuc_yoksa(tmp_path):
    r = calistir("rapor", "--sonuc", tmp_path / "yok.json", "--cikti", tmp_path)
    assert r.returncode == 2 and "Traceback" not in r.stderr


def test_ro_vardiya_ve_gun(girdiler):
    k, d, b = girdiler
    calistir("hesapla", "--durus", d, "--bakim", b, "--cikti", k / "o")
    s = json.loads((k / "o" / "sonuc.json").read_text("utf-8"))
    v = {r["vardiya"]: r for r in s["kirilim_vardiya"]}
    assert v["Sabah"]["ortalama_ro"] == pytest.approx((515 + 520) / 2 / 519)
    assert v["Aksam"]["ortalama_ro"] == pytest.approx(505 / 519)
    assert s["gun_ro"] == [{"tarih": "2026-10-05", "uretim": 1020, "ro": pytest.approx(1020 / 1038)},
                           {"tarih": "2026-10-06", "uretim": 520, "ro": pytest.approx(520 / 519)}]
