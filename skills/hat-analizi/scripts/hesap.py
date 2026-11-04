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
