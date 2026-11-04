import pandas as pd
import pytest

from hesap import ayikla, bakim_eslestir, kayitsiz_kronikler, koruyucu_bakim_ozeti, vardiya_ozeti
from veri import ayarlari_yukle
from yardimci import durus_df

AYAR = ayarlari_yukle()
DONEM = (pd.Timestamp("2026-10-01 07:30"), pd.Timestamp("2026-10-20 23:30"))


def bakim_df(kayitlar):
    """kayitlar: (is_emri, tip, posta, baslama, bitis)"""
    return pd.DataFrame([{
        "is_emri": ie, "ariza_tipi": tip, "posta": posta, "ariza_tanimi": "tanım",
        "ariza_nedeni": "neden", "yapilan_mudahale": "müdahale",
        "baslama": pd.Timestamp(bas), "bitis": pd.Timestamp(bit),
        "mudahale_dk": 30.0, "durus_dk": 10.0, "kisi_sayisi": 1} for ie, tip, posta, bas, bit in kayitlar])


def temiz_df(satirlar):
    df = durus_df([(z, s, p, n, "Sabah", 1, 500) for z, s, p, n in satirlar])
    return ayikla(df, vardiya_ozeti(df, AYAR), AYAR)[0]


IE = [("1", "Elektronik", "OP170", "2026-10-10 09:00", "2026-10-10 09:30")]


def _role(once_gunler, sonra_gunler, pencere=True):
    satirlar = [(f"2026-10-{g:02d} 10:00", 6, "OP170", "röle") for g in once_gunler]
    satirlar += [(f"2026-10-{g:02d} 10:00", 6, "OP170", "röle") for g in sonra_gunler]
    if pencere:
        satirlar += [("2026-10-10 08:00", 12, "OP170", "röle"),
                     ("2026-10-10 08:30", 3, "OP170", "sensör")]
    return temiz_df(satirlar)


def test_hedef_neden_en_cok_kayip():
    e, _ = bakim_eslestir(bakim_df(IE), _role([], []), AYAR, DONEM)
    assert e[0]["hedef_neden"] == "röle" and e[0]["posta"] == "OP170"


def test_kalici():
    e, _ = bakim_eslestir(bakim_df(IE), _role([3, 5, 7, 9], []), AYAR, DONEM)
    assert (e[0]["once"], e[0]["sonra"], e[0]["sinif"]) == (5, 0, "Kalıcı")  # pencere içindeki 08:00 duruşu da önceye girer


def test_kismi():
    e, _ = bakim_eslestir(bakim_df(IE), _role([3, 5, 7, 9], [12, 14]), AYAR, DONEM)
    assert (e[0]["once"], e[0]["sonra"], e[0]["sinif"]) == (5, 2, "Kısmi")


def test_kalici_degil():
    e, _ = bakim_eslestir(bakim_df(IE), _role([3, 5, 7, 9], [12, 14, 16]), AYAR, DONEM)
    assert e[0]["sinif"] == "Kalıcı değil"


def test_once_sifir_sonra_var_kalici_degil():
    e, _ = bakim_eslestir(bakim_df(IE), _role([], [12]), AYAR, DONEM)
    assert (e[0]["once"], e[0]["sonra"], e[0]["sinif"]) == (1, 1, "Kalıcı değil")


def test_sonra_penceresi_7_gun():
    e, _ = bakim_eslestir(bakim_df(IE), _role([3], [18]), AYAR, DONEM)  # 18 > 10+7
    assert e[0]["sonra"] == 0


def test_eslesmedi():
    e, _ = bakim_eslestir(bakim_df(IE), _role([3], [], pencere=False), AYAR, DONEM)
    assert e[0]["sinif"] == "Eşleşmedi" and e[0]["hedef_neden"] is None


def test_takipte():
    ie = [("2", "Mekanik", "OP170", "2026-10-15 09:00", "2026-10-15 09:30")]
    temiz = temiz_df([("2026-10-15 08:30", 8, "OP170", "röle")])
    e, _ = bakim_eslestir(bakim_df(ie), temiz, AYAR, DONEM)
    assert e[0]["sinif"] == "Takipte" and e[0]["sonra"] is None


def test_koruyucu_bakim_haric():
    ie = IE + [("3", "Koruyucu Bakım", "OP170", "2026-10-10 09:00", "2026-10-10 09:10")]
    e, _ = bakim_eslestir(bakim_df(ie), _role([], []), AYAR, DONEM)
    assert [r["is_emri"] for r in e] == ["1"]


def test_donem_disi_is_emri():
    ie = [("4", "Elektrik", "OP170", "2026-09-20 09:00", "2026-09-20 09:30")]
    e, uy = bakim_eslestir(bakim_df(ie), _role([], []), AYAR, DONEM)
    assert e == [] and any("dönem" in u for u in uy)


def test_cikti_json_uyumlu():
    import json
    e, _ = bakim_eslestir(bakim_df(IE), _role([3], []), AYAR, DONEM)
    json.dumps(e)
    assert e[0]["baslama"] == "2026-10-10T09:00:00"


def test_kayitsiz_kronik():
    p = [{"posta": "OP311", "neden": "YAG ESANJORU NOK"}, {"posta": "OP170", "neden": "röle"}]
    bakim = bakim_df(IE + [("5", "Koruyucu Bakım", "OP311", "2026-10-10 09:00", "2026-10-10 09:10")])
    k = kayitsiz_kronikler(p, bakim, DONEM)
    assert [x["posta"] for x in k] == ["OP311"]


def test_koruyucu_bakim_ozeti():
    bakim = bakim_df(IE + [("5", "Koruyucu Bakım", "OP311", "2026-10-10 09:00", "2026-10-10 09:10"),
                           ("6", "Koruyucu Bakım", "OP311", "2026-10-11 09:00", "2026-10-11 09:10")])
    assert koruyucu_bakim_ozeti(bakim) == {"adet": 2, "posta_sayisi": 1}


def test_duruş_verisi_yok():
    ie = [("7", "AGV", "MM11 AGV", "2026-10-10 09:00", "2026-10-10 09:30")]
    e, _ = bakim_eslestir(bakim_df(ie), _role([3], []), AYAR, DONEM)
    assert e[0]["sinif"] == "Duruş verisi yok"


def test_kayitsiz_kronik_donem_disi_is_emri_sayilmaz():
    p = [{"posta": "OP311", "neden": "YAG ESANJORU NOK"}]
    bakim = bakim_df([("8", "Mekanik", "OP311", "2026-09-28 09:00", "2026-09-28 09:30")])
    assert [x["posta"] for x in kayitsiz_kronikler(p, bakim, DONEM)] == ["OP311"]
