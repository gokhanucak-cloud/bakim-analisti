"""Ro, ayıklama, MTTR/MTBF, Pareto ve bakım eşleşmesi hesapları."""
from __future__ import annotations

from typing import Literal

import pandas as pd

VARDIYA_SIRASI = {"Sabah": 0, "Aksam": 1}


def vardiya_ozeti(durus: pd.DataFrame, ayar: dict) -> pd.DataFrame:
    def baskin(s):
        s = s.dropna()
        return s.mode().iloc[0] if len(s) else pd.NA

    v = (durus.groupby(["tarih", "vardiya"])
         .agg(uretim=("sayac", "max"), ekip=("ekip", baskin))
         .reset_index())
    v["ekip"] = v["ekip"].astype("Int64")
    v["uretim"] = v["uretim"].astype(int)
    v["ro"] = v["uretim"] / ayar["vardiya_hedefi"]
    v["calisildi"] = v["uretim"] > 0
    v["_sira"] = v["vardiya"].map(VARDIYA_SIRASI).fillna(9)
    return v.sort_values(["tarih", "_sira"]).drop(columns="_sira").reset_index(drop=True)


def ayikla(durus: pd.DataFrame, vardiyalar: pd.DataFrame,
           ayar: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    calisilan = vardiyalar.loc[vardiyalar["calisildi"], ["tarih", "vardiya"]]
    df = durus.merge(calisilan, on=["tarih", "vardiya"], how="inner")
    anomali = df["sure_dk"] > ayar["anomali_esigi_dk"]
    temiz = df[~anomali].copy()
    temiz["tur"] = (temiz["sure_dk"] >= ayar["ariza_esigi_dk"]).map({True: "ariza", False: "mikro"})
    return temiz.reset_index(drop=True), df[anomali].reset_index(drop=True)


def kpi(temiz: pd.DataFrame, vardiya_sayisi: int, ayar: dict) -> dict:
    ariza = temiz[temiz["tur"] == "ariza"]["sure_dk"]
    mikro = temiz[temiz["tur"] == "mikro"]["sure_dk"]
    n, ariza_dk = int(len(ariza)), float(ariza.sum())
    toplam = float(temiz["sure_dk"].sum())
    return {
        "ariza_sayisi": n,
        "ariza_dk": ariza_dk,
        "mttr_dk": ariza_dk / n if n else None,
        "mtbf_dk": (vardiya_sayisi * ayar["net_sure_dk"] - ariza_dk) / n if n else None,
        "mikro_sayisi": int(len(mikro)),
        "mikro_dk": float(mikro.sum()),
        "toplam_kayip_dk": toplam,
        "kayip_motor": toplam / ayar["takt_dk"],
    }


def _python(deger):
    """numpy/pandas skalerlerini JSON'a yazılabilir Python değerine çevirir."""
    if deger is pd.NA or (isinstance(deger, float) and pd.isna(deger)):
        return None
    return deger.item() if hasattr(deger, "item") else deger


def kirilim(temiz: pd.DataFrame, vardiyalar: pd.DataFrame, ayar: dict,
            alan: Literal["posta", "vardiya", "ekip"]) -> list[dict]:
    calisilan = vardiyalar[vardiyalar["calisildi"]]
    sonuc = []
    for deger, grup in temiz.dropna(subset=[alan]).groupby(alan):
        if alan == "vardiya":
            n = int((calisilan["vardiya"] == deger).sum())
        else:  # posta ve ekip her çalışılan vardiyada bulunabilir
            n = int(len(calisilan))
        sonuc.append({alan: _python(deger), **kpi(grup, n, ayar)})
    return sorted(sonuc, key=lambda r: r["toplam_kayip_dk"], reverse=True)


def ro_ozeti(vardiyalar: pd.DataFrame, ayar: dict) -> dict:
    c = vardiyalar[vardiyalar["calisildi"]]
    return {
        "ortalama_ro": float(c["ro"].mean()) if len(c) else None,
        "hedefi_tutan_oran": float((c["ro"] >= ayar["ro_hedefi"]).mean()) if len(c) else None,
        "calisilan_vardiya": int(len(c)),
        "calisilmayan": [{"tarih": str(r.tarih), "vardiya": r.vardiya}
                         for r in vardiyalar[~vardiyalar["calisildi"]].itertuples()],
        "vardiya_ro": [{"tarih": str(r.tarih), "vardiya": r.vardiya, "ekip": _python(r.ekip),
                        "uretim": int(r.uretim), "ro": float(r.ro)} for r in c.itertuples()],
    }


def pareto(temiz: pd.DataFrame, anahtar: list[str], ayar: dict,
           ilk: int | None = None) -> list[dict]:
    toplam = float(temiz["sure_dk"].sum())
    g = temiz.assign(
        ariza_dk=temiz["sure_dk"].where(temiz["tur"] == "ariza", 0.0),
        mikro_dk=temiz["sure_dk"].where(temiz["tur"] == "mikro", 0.0),
    ).groupby(anahtar).agg(toplam_kayip_dk=("sure_dk", "sum"), adet=("sure_dk", "size"),
                           ariza_dk=("ariza_dk", "sum"), mikro_dk=("mikro_dk", "sum"))
    g = g.sort_values("toplam_kayip_dk", ascending=False).reset_index()
    sonuc, kumulatif = [], 0.0
    kesim = ayar["pareto_kesim"] * 100
    for r in g.to_dict("records"):
        yuzde = r["toplam_kayip_dk"] / toplam * 100 if toplam else 0.0
        onceki = kumulatif
        kumulatif += yuzde
        sonuc.append({
            **{k: _python(r[k]) for k in anahtar},
            "toplam_kayip_dk": float(r["toplam_kayip_dk"]), "adet": int(r["adet"]),
            "ariza_dk": float(r["ariza_dk"]), "mikro_dk": float(r["mikro_dk"]),
            "kayip_motor": float(r["toplam_kayip_dk"]) / ayar["takt_dk"],
            "yuzde": yuzde, "kumulatif_yuzde": kumulatif,
            "oncelik": bool(onceki < kesim - 1e-9),
            "baskin_tur": "ariza" if r["ariza_dk"] > r["mikro_dk"] else "mikro",
        })
    return sonuc[:ilk] if ilk else sonuc


def mikro_analiz(temiz: pd.DataFrame, calisilan_saat: float, ilk: int = 10) -> list[dict]:
    m = temiz[temiz["tur"] == "mikro"]
    g = (m.groupby(["posta", "neden"])["sure_dk"].agg(adet="size", mikro_dk="sum")
         .reset_index().sort_values(["mikro_dk", "adet"], ascending=False).head(ilk))
    return [{"posta": r.posta, "neden": r.neden, "adet": int(r.adet), "mikro_dk": float(r.mikro_dk),
             "saatte_adet": r.adet / calisilan_saat if calisilan_saat else None}
            for r in g.itertuples()]
