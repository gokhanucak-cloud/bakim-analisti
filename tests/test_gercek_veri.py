"""Gerçek Ekim 2026 dosyalarıyla duman testi. BAKIM_DURUS ve BAKIM_DEFTER verilmezse atlanır."""
import json
import os

import pytest

from test_cli import calistir

DURUS, DEFTER = os.environ.get("BAKIM_DURUS"), os.environ.get("BAKIM_DEFTER")
pytestmark = pytest.mark.skipif(not (DURUS and DEFTER), reason="gerçek veri yolu verilmedi")


@pytest.fixture(scope="module")
def sonuc(tmp_path_factory):
    o = tmp_path_factory.mktemp("gercek")
    r = calistir("hesapla", "--durus", DURUS, "--bakim", DEFTER, "--cikti", o)
    assert r.returncode == 0, r.stderr
    return json.loads((o / "sonuc.json").read_text("utf-8"))


def test_satir_sayisi(sonuc):
    assert sonuc["ozet"]["ham_satir"] == 14296


def test_calisilmayan_vardiyalar(sonuc):
    assert {(c["tarih"], c["vardiya"]) for c in sonuc["calisilmayan_vardiyalar"]} == {
        ("2026-10-17", "Sabah"), ("2026-10-17", "Aksam"), ("2026-10-27", "Aksam"),
        ("2026-10-28", "Aksam"), ("2026-10-29", "Aksam")}


def test_5_ekim_sabah(sonuc):
    r = next(v for v in sonuc["vardiya_ro"] if (v["tarih"], v["vardiya"]) == ("2026-10-05", "Sabah"))
    assert r["uretim"] == 521


def test_op311_en_sik(sonuc):
    en = max(sonuc["kirilim_posta"], key=lambda r: r["ariza_sayisi"] + r["mikro_sayisi"])
    assert en["posta"] == "OP311"


def test_anomaliler(sonuc):
    assert all(a["sure_dk"] > 348 for a in sonuc["anomaliler"])
    assert any(a["posta"] == "OP550" for a in sonuc["anomaliler"])
