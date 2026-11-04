"""sonuc.json (+ aksiyonlar.json) içeriğinden tek dosyalık HTML rapor üretir."""
from __future__ import annotations

from html import escape

AKSIYON_ALANLARI = ("oncelik", "posta", "sorun", "kanit", "aksiyon_turu", "onerilen_aksiyon",
                    "beklenen_kazanc_motor_vardiya", "sorumlu_onerisi")
AKSIYON_TURLERI = ("hızlı düzeltme", "kalıcı çözüm", "koruyucu bakım", "otonom bakım",
                   "veri-sensör kontrolü")
SINIF_SIRASI = ["Kalıcı değil", "Kısmi", "Takipte", "Kalıcı", "Eşleşmedi", "Duruş verisi yok"]


def aksiyon_dogrula(aksiyonlar) -> list[str]:
    if not isinstance(aksiyonlar, list):
        return ["aksiyonlar.json bir liste ([...]) olmalı."]
    hatalar = []
    for i, a in enumerate(aksiyonlar, 1):
        if not isinstance(a, dict):
            hatalar.append(f"{i}. madde bir nesne ({{...}}) olmalı.")
            continue
        for alan in AKSIYON_ALANLARI:
            if alan not in a or a[alan] in (None, ""):
                hatalar.append(f"{i}. madde: '{alan}' alanı eksik.")
        if "aksiyon_turu" in a and a["aksiyon_turu"] not in AKSIYON_TURLERI:
            hatalar.append(f"{i}. madde: aksiyon_turu '{a['aksiyon_turu']}' geçersiz; izinli: "
                           + ", ".join(AKSIYON_TURLERI))
        for alan in ("oncelik", "beklenen_kazanc_motor_vardiya"):
            if alan in a and a[alan] not in (None, "") and not isinstance(a[alan], (int, float)):
                hatalar.append(f"{i}. madde: '{alan}' sayı olmalı.")
    return hatalar


# --- biçimlendirme -------------------------------------------------------------------------

def e(x) -> str:
    return escape("" if x is None else str(x), quote=True)


def sayi(x, ondalik: int = 0) -> str:
    if x is None:
        return "—"
    m = f"{x:,.{ondalik}f}"
    return m.replace(",", "\0").replace(".", ",").replace("\0", ".")


def yuzde(x, ondalik: int = 1, oran: bool = True) -> str:
    if x is None:
        return "—"
    return "%" + sayi(x * 100 if oran else x, ondalik)


def tablo(basliklar: list[str], satirlar: list[list[str]], sayisal: set[int] = frozenset(),
          bos: str = "Kayıt yok.") -> str:
    if not satirlar:
        return f'<p class="bos">{e(bos)}</p>'
    th = "".join(f'<th{" class=n" if i in sayisal else ""}>{e(b)}</th>'
                 for i, b in enumerate(basliklar))
    tr = "".join("<tr>" + "".join(f'<td{" class=n" if i in sayisal else ""}>{h}</td>'
                                  for i, h in enumerate(s)) + "</tr>" for s in satirlar)
    return f'<div class="tablo"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def rozet(metin: str, tur: str) -> str:
    return f'<span class="rozet {tur}">{e(metin)}</span>'


# --- grafikler (satır içi SVG) -------------------------------------------------------------

def _cubuk_grafik(etiketler: list[str], degerler: list[float], hedef: float | None,
                  renkler: list[str], alt: float = 0.85, ust: float = 1.02) -> str:
    G, Y, SOL, ALT = 720, 240, 40, 46
    n = max(len(degerler), 1)
    w = (G - SOL - 8) / n

    def y(v):
        v = min(max(v, alt), ust)
        return 8 + (ust - v) / (ust - alt) * (Y - 8 - ALT)

    parca = []
    for t in (alt, (alt + ust) / 2, ust):
        parca.append(f'<line x1="{SOL}" x2="{G}" y1="{y(t):.1f}" y2="{y(t):.1f}" class="izgara"/>'
                     f'<text x="{SOL - 4}" y="{y(t) + 4:.1f}" class="eksen" text-anchor="end">'
                     f'{e(yuzde(t, 0))}</text>')
    for i, (et, v, r) in enumerate(zip(etiketler, degerler, renkler)):
        x = SOL + i * w + w * 0.15
        parca.append(f'<rect x="{x:.1f}" y="{y(v):.1f}" width="{w * 0.7:.1f}" '
                     f'height="{Y - ALT - y(v):.1f}" class="{r}"><title>{e(et)}: '
                     f'{e(yuzde(v))}</title></rect>')
        if et.endswith("S") or i == 0:  # her günün ilk vardiyasında tarih etiketi
            parca.append(f'<text x="{x + w * 0.35:.1f}" y="{Y - ALT + 14}" class="eksen" '
                         f'text-anchor="end" transform="rotate(-45 {x + w * 0.35:.1f} '
                         f'{Y - ALT + 14})">{e(et[:5])}</text>')
    if hedef is not None:
        parca.append(f'<line x1="{SOL}" x2="{G}" y1="{y(hedef):.1f}" y2="{y(hedef):.1f}" '
                     f'class="hedef"/><text x="{G - 4}" y="{y(hedef) - 4:.1f}" class="eksen vurgu" '
                     f'text-anchor="end">hedef {e(yuzde(hedef, 0))}</text>')
    return (f'<svg viewBox="0 0 {G} {Y}" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="Vardiya Ro grafiği">{"".join(parca)}</svg>')


def _pareto_grafik(satirlar: list[dict], kesim: float) -> str:
    G, Y, SOL, SAG, ALT = 720, 260, 48, 40, 60
    satirlar = satirlar[:15]
    n = max(len(satirlar), 1)
    w = (G - SOL - SAG) / n
    tepe = max((s["toplam_kayip_dk"] for s in satirlar), default=1) or 1

    def yk(v):
        return 8 + (1 - v / tepe) * (Y - 8 - ALT)

    def yy(p):
        return 8 + (1 - p / 100) * (Y - 8 - ALT)

    parca = [f'<line x1="{SOL}" x2="{G - SAG}" y1="{yy(kesim):.1f}" y2="{yy(kesim):.1f}" '
             f'class="hedef"/><text x="{G - SAG + 4}" y="{yy(kesim) + 4:.1f}" class="eksen vurgu">'
             f'%{kesim:.0f}</text>',
             f'<text x="{SOL - 4}" y="{yk(tepe) + 4:.1f}" class="eksen" text-anchor="end">'
             f'{e(sayi(tepe))}</text><text x="{SOL - 4}" y="{Y - ALT + 4}" class="eksen" '
             f'text-anchor="end">0</text>',
             f'<text x="{G - SAG + 4}" y="{yy(100) + 4:.1f}" class="eksen">%100</text>']
    noktalar = []
    for i, s in enumerate(satirlar):
        x = SOL + i * w + w * 0.15
        sinif = "cubuk1" if s["oncelik"] else "cubuk-soluk"
        parca.append(f'<rect x="{x:.1f}" y="{yk(s["toplam_kayip_dk"]):.1f}" width="{w * 0.7:.1f}" '
                     f'height="{Y - ALT - yk(s["toplam_kayip_dk"]):.1f}" class="{sinif}"><title>'
                     f'{e(s["posta"])}: {e(sayi(s["toplam_kayip_dk"]))} dk</title></rect>'
                     f'<text x="{x + w * 0.35:.1f}" y="{Y - ALT + 14}" class="eksen" '
                     f'text-anchor="end" transform="rotate(-45 {x + w * 0.35:.1f} {Y - ALT + 14})">'
                     f'{e(s["posta"])}</text>')
        noktalar.append(f'{x + w * 0.35:.1f},{yy(s["kumulatif_yuzde"]):.1f}')
    parca.append(f'<polyline points="{" ".join(noktalar)}" class="kumulatif"/>')
    parca += [f'<circle cx="{p.split(",")[0]}" cy="{p.split(",")[1]}" r="3" class="nokta"/>'
              for p in noktalar]
    return (f'<svg viewBox="0 0 {G} {Y}" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="Posta Pareto grafiği">{"".join(parca)}</svg>')


# --- bölümler ------------------------------------------------------------------------------

def _kutu(baslik: str, deger: str, alt: str = "", durum: str = "") -> str:
    return (f'<div class="kutu {durum}"><div class="kutu-b">{e(baslik)}</div>'
            f'<div class="kutu-d">{e(deger)}</div><div class="kutu-a">{e(alt)}</div></div>')


def _ozet(s: dict) -> str:
    o, a = s["ozet"], s["ayarlar"]
    ro_ok = o["ortalama_ro"] is not None and o["ortalama_ro"] >= a["ro_hedefi"]
    kutular = "".join([
        _kutu("Ortalama Ro", yuzde(o["ortalama_ro"]), f"hedef {yuzde(a['ro_hedefi'], 0)}",
              "iyi" if ro_ok else "kotu"),
        _kutu("Hedefi tutan vardiya", yuzde(o["hedefi_tutan_oran"], 0),
              f"{o['calisilan_vardiya']} çalışılan vardiya"),
        _kutu("Motor açığı", sayi(o["gercek_kayip_motor"]),
              f"hedef {a['vardiya_hedefi']} × vardiya − üretim"),
        _kutu("Toplam duruş kaybı", f"{sayi(o['toplam_kayip_dk'])} dk",
              f"arıza {sayi(o['ariza_dk'])} · mikro {sayi(o['mikro_dk'])} dk"),
        _kutu("Hat MTTR", f"{sayi(o['mttr_dk'], 1)} dk", f"{o['ariza_sayisi']} arıza (≥ "
              f"{a['ariza_esigi_dk']} dk)"),
        _kutu("Hat MTBF", f"{sayi(o['mtbf_dk'], 0)} dk", f"net {a['net_sure_dk']} dk/vardiya"),
        _kutu("Mikro duruş", sayi(o["mikro_sayisi"]), f"< {a['ariza_esigi_dk']} dk"),
        _kutu("Ayıklanan anomali", sayi(o["anomali_sayisi"]),
              f"{len(s['calisilmayan_vardiyalar'])} çalışılmayan vardiya"),
    ])
    return f'<div class="kutular">{kutular}</div>'


def _ro_trendi(s: dict) -> str:
    v = s["vardiya_ro"]
    if not v:
        return '<p class="bos">Çalışılan vardiya yok.</p>'
    etiket = [f"{r['tarih'][5:]} {'S' if r['vardiya'] == 'Sabah' else 'A'}" for r in v]
    renk = ["sabah" if r["vardiya"] == "Sabah" else "aksam" for r in v]
    alt = min(0.85, min(r["ro"] for r in v) - 0.01)
    grafik = '<div class="grafik">' + _cubuk_grafik(etiket, [r["ro"] for r in v], s["ayarlar"]["ro_hedefi"], renk, alt=alt) + "</div>"
    lejant = ('<p class="lejant"><span class="kare sabah"></span>Sabah '
              '<span class="kare aksam"></span>Akşam</p>')
    alti = [r for r in v if r["ro"] < s["ayarlar"]["ro_hedefi"]]
    alti = sorted(alti, key=lambda r: r["ro"])[:8]
    t = tablo(["Tarih", "Vardiya", "Üretim", "Ro"],
              [[e(r["tarih"]), e(r["vardiya"]), sayi(r["uretim"]), yuzde(r["ro"])] for r in alti],
              {2, 3}, "Tüm vardiyalar hedefte.")
    return f'{grafik}{lejant}<h3>Hedefin en çok altında kalan vardiyalar</h3>{t}'


def _tur(t: str) -> str:
    return rozet("arıza ağırlıklı", "ariza") if t == "ariza" else rozet("mikro ağırlıklı", "mikro")


def _darbogaz(s: dict) -> str:
    kesim = s["ayarlar"]["pareto_kesim"] * 100
    p = s["pareto_posta"]
    oncelik = [r for r in p if r["oncelik"]]
    giris = (f'<p>Kaybın <b>%{kesim:.0f}</b>\'i {len(oncelik)} postada toplanıyor: '
             f'{", ".join(e(r["posta"]) for r in oncelik[:12])}'
             f'{" …" if len(oncelik) > 12 else ""}.</p>')
    t1 = tablo(["Posta", "Kayıp (dk)", "Pay", "Kümülatif", "Adet", "Tür", "Motor payı*"],
               [[f'<b>{e(r["posta"])}</b>' if r["oncelik"] else e(r["posta"]),
                 sayi(r["toplam_kayip_dk"]), yuzde(r["yuzde"], 1, False),
                 yuzde(r["kumulatif_yuzde"], 1, False), sayi(r["adet"]), _tur(r["baskin_tur"]),
                 sayi(r["kayip_motor"])] for r in p[:15]], {1, 2, 3, 4, 6})
    t2 = tablo(["Posta", "Duruş nedeni", "Kayıp (dk)", "Adet", "Tür"],
               [[e(r["posta"]), e(r["neden"]), sayi(r["toplam_kayip_dk"]), sayi(r["adet"]),
                 _tur(r["baskin_tur"])] for r in s["pareto_neden"]], {2, 3})
    not_ = ('<p class="not">* Motor payı: dönemdeki gerçek motor açığının, postanın duruş '
            'dakikası payı kadarı. Ara stoklar nedeniyle her posta duruşu hattı durdurmaz; '
            'bu bir dağıtım tahminidir.</p>')
    return (f'{giris}<div class="grafik">{_pareto_grafik(p, kesim)}</div><h3>Postalar (ilk 15)</h3>{t1}{not_}'
            f'<h3>İlk 10 posta – neden</h3>{t2}')


def _kpi_satir(ad: str, r: dict) -> list[str]:
    return [ad, sayi(r["ariza_sayisi"]), sayi(r["mttr_dk"], 1), sayi(r["mtbf_dk"]),
            sayi(r["mikro_sayisi"]), sayi(r["toplam_kayip_dk"])]


def _mttr_mtbf(s: dict) -> str:
    bas = ["", "Arıza", "MTTR (dk)", "MTBF (dk)", "Mikro duruş", "Toplam kayıp (dk)"]
    n = {1, 2, 3, 4, 5}
    t1 = tablo(["Posta"] + bas[1:], [_kpi_satir(f"<b>{e(r['posta'])}</b>", r)
                                     for r in s["kirilim_posta"]], n)
    t2 = tablo(["Vardiya"] + bas[1:], [_kpi_satir(e(r["vardiya"]), r)
                                       for r in s["kirilim_vardiya"]], n)
    t3 = tablo(["Ekip"] + bas[1:], [_kpi_satir(e(r["ekip"]), r)
                                    for r in sorted(s["kirilim_ekip"], key=lambda r: r["ekip"])], n)
    not_ = ('<p class="not">Ekip, duruş kaydındaki ekip numarasıdır. Aynı vardiyada birden fazla '
            'ekip numarası görülebildiği için ekip MTBF\'si tüm çalışılan vardiyalar üzerinden '
            'hesaplanır.</p>')
    return (f'<h3>Posta bazında (kayba göre ilk 15)</h3>{t1}<h3>Vardiya bazında</h3>{t2}'
            f'<h3>Ekip bazında</h3>{t3}{not_}')


def _mikro(s: dict) -> str:
    return tablo(["Posta", "Duruş nedeni", "Adet", "Kayıp (dk)", "Saatte"],
                 [[e(r["posta"]), e(r["neden"]), sayi(r["adet"]), sayi(r["mikro_dk"]),
                   sayi(r["saatte_adet"], 1)] for r in s["mikro"]], {2, 3, 4})


def _bakim(s: dict) -> str:
    es = s["bakim_eslesme"]
    sayim = {k: sum(1 for r in es if r["sinif"] == k) for k in SINIF_SIRASI}
    renk = {"Kalıcı değil": "kotu", "Kısmi": "uyari", "Kalıcı": "iyi", "Takipte": "notr",
            "Eşleşmedi": "notr", "Duruş verisi yok": "notr"}
    ozet = " ".join(f'{rozet(f"{k}: {v}", renk[k])}' for k, v in sayim.items() if v)
    kb = s["koruyucu_bakim"]
    giris = (f'<p>{len(es)} arıza iş emri değerlendirildi. {ozet}</p><p class="not">'
             f'Koruyucu bakım: {kb["adet"]} iş emri, {kb["posta_sayisi"]} posta (eşleştirmeye '
             f'girmez). Kalıcılık: iş emrinden önceki ve sonraki '
             f'{s["ayarlar"]["kalicilik_gun"]} gündeki tekrar sayısı.</p>')
    sirali = sorted([r for r in es if r["sinif"] in ("Kalıcı değil", "Kısmi", "Takipte", "Kalıcı")],
                    key=lambda r: (SINIF_SIRASI.index(r["sinif"]), r["baslama"]))
    t1 = tablo(["Sınıf", "İş emri", "Posta", "Tarih", "Arıza tanımı", "Yapılan müdahale",
                "Hedef duruş nedeni", "Önce", "Sonra"],
               [[rozet(r["sinif"], renk[r["sinif"]]), e(r["is_emri"]), e(r["posta"]),
                 e(r["baslama"][:16].replace("T", " ")), e(r["ariza_tanimi"]),
                 e(r["yapilan_mudahale"]), e(r["hedef_neden"]), sayi(r["once"]),
                 sayi(r["sonra"])] for r in sirali], {7, 8}, "Eşleşen iş emri yok.")
    t2 = tablo(["Posta", "Duruş nedeni", "Kayıp (dk)", "Adet"],
               [[e(r["posta"]), e(r["neden"]), sayi(r["toplam_kayip_dk"]), sayi(r["adet"])]
                for r in s["kayitsiz_kronikler"]], {2, 3},
               "İlk 10 kronik duruşun hepsi için bakım kaydı var.")
    return (f'{giris}<h3>Duruşla eşleşen iş emirleri</h3>{t1}'
            f'<h3>Bakıma kayıt açılmamış kronik duruşlar</h3>'
            f'<p class="not">İlk 10 posta–neden çiftinden, dönemde aynı postada hiç arıza iş '
            f'emri açılmamış olanlar.</p>{t2}')


def _aksiyonlar(aksiyonlar: list[dict] | None) -> str:
    if not aksiyonlar:
        return ('<p class="bos">Aksiyon listesi henüz hazırlanmadı. Bakım Analisti ajanına '
                '<code>/hat-analizi</code> ile hazırlatabilirsiniz.</p>')
    satir = [[sayi(a["oncelik"]), f'<b>{e(a["posta"])}</b>', e(a["sorun"]), e(a["kanit"]),
              rozet(a["aksiyon_turu"], "notr"), e(a["onerilen_aksiyon"]),
              sayi(a["beklenen_kazanc_motor_vardiya"], 1), e(a["sorumlu_onerisi"])]
             for a in sorted(aksiyonlar, key=lambda a: a["oncelik"])]
    return tablo(["#", "Posta", "Sorun", "Kanıt", "Tür", "Önerilen aksiyon",
                  "Kazanç (motor/vardiya)", "Sorumlu"], satir, {0, 6})


def _anomaliler(s: dict) -> str:
    t1 = tablo(["Tarih", "Vardiya"], [[e(r["tarih"]), e(r["vardiya"])]
                                      for r in s["calisilmayan_vardiyalar"]],
               bos="Çalışılmayan vardiya yok.")
    t2 = tablo(["Tarih", "Vardiya", "Posta", "Duruş nedeni", "Süre (dk)"],
               [[e(r["tarih"]), e(r["vardiya"]), e(r["posta"]), e(r["neden"]),
                 sayi(r["sure_dk"])] for r in s["anomaliler"]], {4}, "Anomali yok.")
    uy = ("".join(f"<li>{e(u)}</li>" for u in s["uyarilar"])) or "<li>Uyarı yok.</li>"
    esik = s["ayarlar"]["anomali_esigi_dk"]
    return (f'<h3>Çalışılmayan vardiyalar (üretim 0, analiz dışı)</h3>{t1}'
            f'<h3>Sıkışmış alarm / bypass şüphesi (üretim varken &gt; {sayi(esik)} dk)</h3>'
            f'<p class="not">Bu kayıtlar MTTR/MTBF ve Pareto\'ya alınmadı. Sensör veya alarm '
            f'mantığı kontrol edilmeli.</p>{t2}<h3>Veri uyarıları</h3><ul>{uy}</ul>')


CSS = """
:root{--bg:#f6f7f9;--yuzey:#fff;--metin:#1b1f24;--soluk:#5b6470;--cizgi:#dde1e6;
--vurgu:#c2410c;--sabah:#2563eb;--aksam:#7c3aed;--iyi:#15803d;--kotu:#b91c1c;--uyari:#b45309;
--notr:#475569;--cubuk:#2563eb;--cubuk-soluk:#a9b8d6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#111418;--yuzey:#1a1f25;
--metin:#e6e9ed;--soluk:#9aa4b0;--cizgi:#2c333b;--vurgu:#fb923c;--sabah:#60a5fa;--aksam:#a78bfa;
--iyi:#4ade80;--kotu:#f87171;--uyari:#fbbf24;--notr:#94a3b8;--cubuk:#60a5fa;--cubuk-soluk:#3b4a63}}
:root[data-theme="dark"]{--bg:#111418;--yuzey:#1a1f25;--metin:#e6e9ed;--soluk:#9aa4b0;
--cizgi:#2c333b;--vurgu:#fb923c;--sabah:#60a5fa;--aksam:#a78bfa;--iyi:#4ade80;--kotu:#f87171;
--uyari:#fbbf24;--notr:#94a3b8;--cubuk:#60a5fa;--cubuk-soluk:#3b4a63}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--metin);
font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 64px}
header h1{margin:0 0 4px;font-size:1.6rem}header p{margin:0;color:var(--soluk)}
section{background:var(--yuzey);border:1px solid var(--cizgi);border-radius:10px;padding:18px;
margin-top:18px}h2{margin:0 0 12px;font-size:1.2rem}h3{margin:18px 0 8px;font-size:1rem}
.kutular{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.kutu{border:1px solid var(--cizgi);border-radius:8px;padding:10px 12px}
.kutu-b{color:var(--soluk);font-size:.8rem}.kutu-d{font-size:1.5rem;font-weight:650}
.kutu-a{color:var(--soluk);font-size:.75rem}.kutu.iyi .kutu-d{color:var(--iyi)}
.kutu.kotu .kutu-d{color:var(--kotu)}
.tablo{overflow-x:auto;max-width:100%}table{border-collapse:collapse;width:100%;font-size:.85rem}
th,td{padding:6px 8px;border-bottom:1px solid var(--cizgi);text-align:left;vertical-align:top}
th{color:var(--soluk);font-weight:600;white-space:nowrap}td.n,th.n{text-align:right;
font-variant-numeric:tabular-nums;white-space:nowrap}
.rozet{display:inline-block;padding:1px 8px;border-radius:999px;font-size:.75rem;
border:1px solid currentColor;white-space:nowrap;margin:1px 0}
.rozet.iyi{color:var(--iyi)}.rozet.kotu{color:var(--kotu)}.rozet.uyari{color:var(--uyari)}
.rozet.notr{color:var(--notr)}.rozet.ariza{color:var(--kotu)}.rozet.mikro{color:var(--uyari)}
.not{color:var(--soluk);font-size:.8rem}.bos{color:var(--soluk);font-style:italic}
.grafik{overflow-x:auto}.grafik svg{min-width:600px}svg{width:100%;height:auto;display:block}svg .izgara{stroke:var(--cizgi)}
svg .eksen{fill:var(--soluk);font-size:10px}svg .vurgu{fill:var(--vurgu)}
svg .hedef{stroke:var(--vurgu);stroke-dasharray:4 3;stroke-width:1.5}
svg .sabah{fill:var(--sabah)}svg .aksam{fill:var(--aksam)}svg .cubuk1{fill:var(--cubuk)}
svg .cubuk-soluk{fill:var(--cubuk-soluk)}svg .kumulatif{fill:none;stroke:var(--vurgu);
stroke-width:2}svg .nokta{fill:var(--vurgu)}
.lejant{font-size:.8rem;color:var(--soluk)}.kare{display:inline-block;width:10px;height:10px;
border-radius:2px;margin:0 4px 0 10px;vertical-align:-1px}.kare.sabah{background:var(--sabah)}
.kare.aksam{background:var(--aksam)}
@media print{body{background:#fff;color:#000}section{break-inside:avoid;border-color:#ccc}}
"""


def rapor_olustur(sonuc: dict, aksiyonlar: list[dict] | None) -> str:
    d = sonuc["donem"]
    bolumler = [("Özet", _ozet(sonuc)), ("Ro Trendi", _ro_trendi(sonuc)),
                ("Darboğaz", _darbogaz(sonuc)), ("MTTR / MTBF", _mttr_mtbf(sonuc)),
                ("Mikro Duruşlar", _mikro(sonuc)), ("Bakım Eşleşmesi", _bakim(sonuc)),
                ("Aksiyon Listesi", _aksiyonlar(aksiyonlar)),
                ("Veri Anomalileri", _anomaliler(sonuc))]
    govde = "".join(f"<section><h2>{e(b)}</h2>{h}</section>" for b, h in bolumler)
    girdi = sonuc.get("girdiler", {})
    kaynak = " · ".join(e(v) for v in girdi.values())
    return (f'<!doctype html><html lang="tr"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Hat Bakım Analizi</title><style>{CSS}</style></head><body><main>'
            f'<header><h1>Hat Bakım Analizi</h1><p>Dönem {e(d["baslangic"][:10])} – '
            f'{e(d["bitis"][:10])}{" · " + kaynak if kaynak else ""}</p></header>'
            f'{govde}</main></body></html>')
