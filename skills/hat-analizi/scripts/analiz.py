#!/usr/bin/env python3
"""Bakım Analisti hesap motoru.

  analiz.py hesapla [--durus X.xlsx] [--bakim Y.csv] [--klasor K] --cikti DIR
  analiz.py rapor --sonuc sonuc.json [--aksiyonlar aksiyonlar.json] --cikti DIR
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import hesap
    import veri
except ImportError as e:  # pandas / openpyxl eksik
    print(f"Gerekli Python paketi eksik ({e.name}). Kurmak için: "
          f"pip install -r requirements.txt  (ya da: pip install pandas openpyxl)", file=sys.stderr)
    sys.exit(2)


def _yuzde(x):
    return "—" if x is None else f"%{x * 100:.1f}"


def hesapla(args) -> int:
    if args.durus and args.bakim:
        durus_yolu, bakim_yolu = Path(args.durus), Path(args.bakim)
    else:
        durus_yolu, bakim_yolu = veri.dosya_bul(Path(args.klasor or "."))
    ayar = veri.ayarlari_yukle()
    durus, u1 = veri.durus_oku(durus_yolu)
    bakim, u2 = veri.bakim_oku(bakim_yolu)
    sonuc = hesap.analiz_et(durus, bakim, ayar, u1 + u2)
    sonuc["girdiler"] = {"durus": durus_yolu.name, "bakim": bakim_yolu.name}
    cikti = Path(args.cikti)
    cikti.mkdir(parents=True, exist_ok=True)
    (cikti / "sonuc.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=2), "utf-8")
    o = sonuc["ozet"]
    ilk = next((p["posta"] for p in sonuc["pareto_posta"]), "—")
    print(f"Dönem {sonuc['donem']['baslangic'][:10]} – {sonuc['donem']['bitis'][:10]} | "
          f"ortalama Ro {_yuzde(o['ortalama_ro'])} | hedefi tutan vardiya "
          f"{_yuzde(o['hedefi_tutan_oran'])} | en büyük kayıp: {ilk} | "
          f"sonuç: {cikti / 'sonuc.json'}")
    return 0


def rapor(args) -> int:
    import rapor as rapor_modulu
    sonuc = json.loads(Path(args.sonuc).read_text("utf-8"))
    aksiyonlar = None
    if args.aksiyonlar:
        aksiyonlar = json.loads(Path(args.aksiyonlar).read_text("utf-8"))
        hatalar = rapor_modulu.aksiyon_dogrula(aksiyonlar)
        if hatalar:
            print("Aksiyon listesi geçersiz:\n- " + "\n- ".join(hatalar), file=sys.stderr)
            return 2
    cikti = Path(args.cikti)
    cikti.mkdir(parents=True, exist_ok=True)
    (cikti / "rapor.html").write_text(rapor_modulu.rapor_olustur(sonuc, aksiyonlar), "utf-8")
    print(f"Rapor: {cikti / 'rapor.html'}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Motor montaj hattı duruş ve bakım analizi")
    alt = p.add_subparsers(dest="komut", required=True)
    h = alt.add_parser("hesapla", help="iki dosyadan sonuc.json üretir")
    h.add_argument("--durus")
    h.add_argument("--bakim")
    h.add_argument("--klasor", help="dosyalar verilmezse bu klasörde aranır")
    h.add_argument("--cikti", required=True)
    r = alt.add_parser("rapor", help="sonuc.json (+ aksiyonlar.json) ile rapor.html üretir")
    r.add_argument("--sonuc", required=True)
    r.add_argument("--aksiyonlar")
    r.add_argument("--cikti", required=True)
    args = p.parse_args(argv)
    try:
        return hesapla(args) if args.komut == "hesapla" else rapor(args)
    except veri.VeriHatasi as e:
        print(f"Hata: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
