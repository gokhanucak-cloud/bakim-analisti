import json

import pytest

from rapor import AKSIYON_TURLERI, aksiyon_dogrula, rapor_olustur
from test_cli import calistir, girdiler  # noqa: F401  (fikstür)

GECERLI = {"oncelik": 1, "posta": "OP311", "sorun": "Yağ eşanjörü uyarısı",
           "kanit": "3.095 mikro duruş, 982 dk", "aksiyon_turu": "veri-sensör kontrolü",
           "onerilen_aksiyon": "Sensörü kontrol et", "beklenen_kazanc_motor_vardiya": 3.5,
           "sorumlu_onerisi": "elektrik"}


@pytest.fixture
def ornek_sonuc(girdiler):  # noqa: F811
    k, d, b = girdiler
    r = calistir("hesapla", "--durus", d, "--bakim", b, "--cikti", k / "o")
    assert r.returncode == 0, r.stderr
    return json.loads((k / "o" / "sonuc.json").read_text("utf-8"))


def test_bolumler(ornek_sonuc):
    h = rapor_olustur(ornek_sonuc, [GECERLI])
    for b in ["Özet", "Ro Trendi", "Darboğaz", "MTTR / MTBF", "Mikro Duruşlar",
              "Bakım Eşleşmesi", "Aksiyon Listesi", "Veri Anomalileri"]:
        assert f">{b}<" in h, b
    assert "Sensörü kontrol et" in h


def test_html_kacis(ornek_sonuc):
    h = rapor_olustur(ornek_sonuc, None)
    assert "<-1...5" not in h
    assert "&lt;-1...5 BAR&gt; &amp; &quot;test&quot;" in h


def test_aksiyon_kacis(ornek_sonuc):
    h = rapor_olustur(ornek_sonuc, [{**GECERLI, "sorun": "<script>x</script>"}])
    assert "<script>x" not in h


def test_dis_kaynak_yok(ornek_sonuc):
    h = rapor_olustur(ornek_sonuc, None)
    assert "http://" not in h.replace('xmlns="http://www.w3.org/2000/svg"', "")
    assert "https://" not in h and h.count("<svg") >= 2


def test_aksiyonsuz_rapor(ornek_sonuc):
    assert "Aksiyon listesi henüz hazırlanmadı" in rapor_olustur(ornek_sonuc, None)


def test_none_tire(ornek_sonuc):
    ornek_sonuc["kirilim_posta"][0]["mttr_dk"] = None
    assert "—" in rapor_olustur(ornek_sonuc, None)


def test_turkce_karakter_ve_lang(ornek_sonuc):
    h = rapor_olustur(ornek_sonuc, None)
    assert '<html lang="tr">' in h and 'charset="utf-8"' in h


def test_aksiyon_dogrula():
    assert aksiyon_dogrula([GECERLI]) == []
    assert any("aksiyon_turu" in m for m in aksiyon_dogrula([{**GECERLI, "aksiyon_turu": "dua"}]))
    assert any("posta" in m for m in aksiyon_dogrula(
        [{k: v for k, v in GECERLI.items() if k != "posta"}]))
    assert aksiyon_dogrula({"x": 1}) != []  # liste değil
    assert "kalıcı çözüm" in AKSIYON_TURLERI


def test_cli_rapor(girdiler, tmp_path):  # noqa: F811
    k, d, b = girdiler
    assert calistir("hesapla", "--durus", d, "--bakim", b, "--cikti", k / "o").returncode == 0
    a = tmp_path / "aksiyonlar.json"
    a.write_text(json.dumps([GECERLI], ensure_ascii=False), "utf-8")
    r = calistir("rapor", "--sonuc", k / "o" / "sonuc.json", "--aksiyonlar", a, "--cikti", k / "o")
    assert r.returncode == 0, r.stderr
    assert (k / "o" / "rapor.html").exists()


def test_cli_rapor_gecersiz_aksiyon(girdiler, tmp_path):  # noqa: F811
    k, d, b = girdiler
    calistir("hesapla", "--durus", d, "--bakim", b, "--cikti", k / "o")
    a = tmp_path / "aksiyonlar.json"
    a.write_text(json.dumps([{**GECERLI, "aksiyon_turu": "dua"}]), "utf-8")
    r = calistir("rapor", "--sonuc", k / "o" / "sonuc.json", "--aksiyonlar", a, "--cikti", k / "o")
    assert r.returncode == 2 and "aksiyon_turu" in r.stderr


def test_ekip_bolumu_yok(ornek_sonuc):
    assert "Ekip" not in rapor_olustur(ornek_sonuc, None)


def test_kapsam_disi_raporda_belirtilir(ornek_sonuc):
    assert "Kapsam dışı postalar: OP311, OP312" in rapor_olustur(ornek_sonuc, None)
