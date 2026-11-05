import pytest

from hesap import ayikla, kirilim, kpi, ro_ozeti, vardiya_ozeti
from veri import ayarlari_yukle
from yardimci import durus_df

AYAR = ayarlari_yukle()


def _temiz(satirlar):
    df = durus_df(satirlar)
    v = vardiya_ozeti(df, AYAR)
    temiz, anom = ayikla(df, v, AYAR)
    return df, v, temiz, anom


def test_vardiya_ozeti_ro():
    df = durus_df([("2026-10-05 08:00", 1, "OP1", "x", "Sabah", 1, 100),
                   ("2026-10-05 15:00", 1, "OP1", "x", "Sabah", 1, 514)])
    v = vardiya_ozeti(df, AYAR)
    assert len(v) == 1
    r = v.iloc[0]
    assert r.uretim == 514 and bool(r.calisildi) and "ekip" not in v.columns
    assert r.ro == pytest.approx(514 / 519)


def test_calisilmayan_vardiya_cikarilir():
    df, v, temiz, anom = _temiz([
        ("2026-10-17 07:35", 430, "OP1", "hava", "Sabah", 1, 0),
        ("2026-10-18 08:00", 1, "OP1", "x", "Sabah", 2, 500)])
    assert not bool(v.set_index("vardiya").loc["Sabah"].iloc[0].calisildi)
    assert (temiz.tarih.astype(str) == "2026-10-17").sum() == 0 and len(anom) == 0
    assert len(temiz) == 1


def test_anomali_ayrilir():
    df, v, temiz, anom = _temiz([
        ("2026-10-05 07:35", 430, "OP550", "kofre", "Sabah", 1, 520),
        ("2026-10-05 09:00", 3, "OP1", "x", "Sabah", 1, 520)])
    assert len(anom) == 1 and anom.iloc[0].posta == "OP550"
    assert temiz.sure_dk.max() < 348


def test_esik_5dk_ariza():
    _, _, temiz, _ = _temiz([("2026-10-05 08:00", 4.99, "OP1", "x", "Sabah", 1, 500),
                             ("2026-10-05 09:00", 5.0, "OP1", "x", "Sabah", 1, 500)])
    assert list(temiz.sort_values("baslangic").tur) == ["mikro", "ariza"]


def _iki_vardiya():
    return _temiz([
        ("2026-10-05 08:00", 10, "OP1", "a", "Sabah", 1, 510),
        ("2026-10-05 09:00", 1, "OP1", "m", "Sabah", 1, 510),
        ("2026-10-05 16:00", 20, "OP2", "b", "Aksam", 2, 515),
        ("2026-10-05 17:00", 2, "OP2", "m", "Aksam", 2, 515)])


def test_kpi_formulleri():
    _, _, temiz, _ = _iki_vardiya()
    k = kpi(temiz, 2, AYAR)
    assert k["ariza_sayisi"] == 2 and k["ariza_dk"] == 30
    assert k["mttr_dk"] == 15
    assert k["mtbf_dk"] == pytest.approx((2 * 435 - 30) / 2)
    assert k["mikro_sayisi"] == 2 and k["mikro_dk"] == 3
    assert k["toplam_kayip_dk"] == 33
    assert "kayip_motor" not in k  # motor kaybı gerçek açıktan dağıtılır (pareto)


def test_ariza_yoksa_none():
    _, _, temiz, _ = _temiz([("2026-10-05 08:00", 1, "OP1", "m", "Sabah", 1, 500)])
    k = kpi(temiz, 1, AYAR)
    assert k["mttr_dk"] is None and k["mtbf_dk"] is None and k["ariza_sayisi"] == 0


def test_kirilim_posta_siralama():
    _, v, temiz, _ = _iki_vardiya()
    p = kirilim(temiz, v, AYAR, "posta")
    assert [r["posta"] for r in p] == ["OP2", "OP1"]
    assert p[0]["mtbf_dk"] == pytest.approx((2 * 435 - 20) / 1)  # posta: tüm çalışılan vardiyalar


def test_kirilim_vardiya():
    _, v, temiz, _ = _iki_vardiya()
    s = {r["vardiya"]: r for r in kirilim(temiz, v, AYAR, "vardiya")}
    assert s["Sabah"]["mttr_dk"] == 10 and s["Aksam"]["mttr_dk"] == 20


def test_ro_ozeti_hedef_orani():
    df = durus_df([("2026-10-05 08:00", 1, "OP1", "x", "Sabah", 1, 517),   # 0.996
                   ("2026-10-05 16:00", 1, "OP1", "x", "Aksam", 2, 509),   # 0.981
                   ("2026-10-17 08:00", 430, "OP1", "x", "Sabah", 3, 0)])  # çalışılmadı
    r = ro_ozeti(vardiya_ozeti(df, AYAR), AYAR)
    assert r["hedefi_tutan_oran"] == 0.5 and r["calisilan_vardiya"] == 2
    assert r["ortalama_ro"] == pytest.approx((517 + 509) / 2 / 519)
    assert r["calisilmayan"] == [{"tarih": "2026-10-17", "vardiya": "Sabah"}]
    assert r["vardiya_ro"][0] == {"tarih": "2026-10-05", "vardiya": "Sabah",
                                  "uretim": 517, "ro": pytest.approx(517 / 519)}


# --- Görev 3: Pareto ve mikro duruşlar ---
from hesap import mikro_analiz, pareto  # noqa: E402


def _kayiplar(dagilim):
    """{posta: [süreler]} → temiz DataFrame."""
    satirlar = []
    for posta, sureler in dagilim.items():
        for i, s in enumerate(sureler):
            satirlar.append((f"2026-10-05 08:{i:02d}", s, posta, f"n-{posta}", "Sabah", 1, 500))
    return _temiz(satirlar)[2]


def test_pareto_kesim():
    p = pareto(_kayiplar({"A": [50], "B": [30], "C": [15], "D": [5]}), ["posta"], AYAR,
               toplam_kayip_motor=100)
    assert [r["posta"] for r in p] == ["A", "B", "C", "D"]
    assert [r["posta"] for r in p if r["oncelik"]] == ["A", "B"]
    assert p[1]["kumulatif_yuzde"] == pytest.approx(80.0)
    assert p[0]["yuzde"] == pytest.approx(50.0)
    assert p[0]["kayip_motor"] == pytest.approx(50.0)  # açığın %50 payı


def test_pareto_ilk_eleman_her_zaman_oncelik():
    p = pareto(_kayiplar({"A": [90], "B": [10]}), ["posta"], AYAR)
    assert p[0]["oncelik"] is True and p[1]["oncelik"] is False


def test_baskin_tur():
    p = pareto(_kayiplar({"A": [6] + [2] * 10}), ["posta"], AYAR)
    assert p[0]["baskin_tur"] == "mikro" and p[0]["adet"] == 11
    assert p[0]["ariza_dk"] == 6 and p[0]["mikro_dk"] == 20


def test_pareto_neden_ilk():
    p = pareto(_kayiplar({f"P{i}": [i + 1] for i in range(15)}), ["posta", "neden"], AYAR, ilk=10)
    assert len(p) == 10 and p[0]["posta"] == "P14" and p[0]["neden"] == "n-P14"


def test_mikro_saatte_adet():
    temiz = _kayiplar({"A": [0.1] * 29, "B": [6]})
    m = mikro_analiz(temiz, 14.5)
    assert len(m) == 1 and m[0]["posta"] == "A" and m[0]["adet"] == 29
    assert m[0]["saatte_adet"] == pytest.approx(2.0)


def test_pareto_motor_verilmezse_none():
    p = pareto(_kayiplar({"A": [5]}), ["posta"], AYAR)
    assert p[0]["kayip_motor"] is None


def test_ro_ozeti_gercek_acik():
    df = durus_df([("2026-10-05 08:00", 1, "OP1", "x", "Sabah", 1, 500),   # 19 eksik
                   ("2026-10-05 16:00", 1, "OP1", "x", "Aksam", 2, 525)])  # hedef üstü: 0
    assert ro_ozeti(vardiya_ozeti(df, AYAR), AYAR)["gercek_kayip_motor"] == 19
