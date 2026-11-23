#!/usr/bin/env python3
"""
Kirim ringkasan ekonomi harian ke WhatsApp.

Dijalankan otomatis oleh GitHub Actions setiap pagi (lihat .github/workflows/harian.yml),
atau manual:  python scripts/kirim_wa.py
Hanya memakai pustaka bawaan Python, tanpa instalasi tambahan.

Variabel lingkungan (diisi sebagai GitHub Secrets):
  WA_PHONE          nomor tujuan, format internasional, mis. 62895353066404
  CALLMEBOT_APIKEY  kunci gratis dari CallMeBot (pilihan 1, untuk kirim ke nomor sendiri)
  FONNTE_TOKEN      token Fonnte (pilihan 2, gateway WA Indonesia)
  DASHBOARD_URL     alamat dashboard, mis. https://namaanda.github.io/asisten-ekonomi/
Jika CALLMEBOT_APIKEY dan FONNTE_TOKEN kosong, pesan hanya dicetak (mode uji).
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

WIT = timezone(timedelta(hours=9))
NOW = datetime.now(WIT)
TODAY = NOW.date()
YEAR = TODAY.year
ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "AsistenEkonomiHarian/1.0 (+https://github.com)"}

HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
BULAN = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]
# Rotasi bidang: indeks = datetime.weekday() (Senin=0 ... Minggu=6)
BIDANG = [
    ("Ekonomi Murni", "macroeconomic"),
    ("Ekonomi Syariah", "islamic"),
    ("Ekonomi SDA & Lingkungan", "environmental"),
    ("Ekonomi Pertanian", "agricultural"),
    ("Ekonomi Kehutanan", "forest"),
    ("Ekonomi Kelautan & Perikanan", "fisheries"),
    ("Ekonomi Pembangunan", "poverty"),
]
# Catatan: tema "Ekonomi Politik & Kebijakan" tersedia di dashboard (menu Jurnal).


def get_json(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def nf(v, d=2):
    """Format angka gaya Indonesia: 18.245,50"""
    s = f"{v:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(a, b):
    return (a - b) / b * 100 if (a is not None and b) else None


def arah(p, kata_naik="naik", kata_turun="turun"):
    if p is None:
        return ""
    if abs(p) < 0.005:
        return "stabil"
    return f"{kata_naik if p > 0 else kata_turun} {nf(abs(p))}%"


# ---------------- data ----------------
def indikator():
    data = json.loads((ROOT / "data" / "indikator.json").read_text(encoding="utf-8"))
    return {i["id"]: i for g in data["kelompok"] for i in g["indikator"]}, data["diperbarui"]


def kurs():
    start = (TODAY - timedelta(days=10)).isoformat()
    d = get_json(f"https://api.frankfurter.dev/v1/{start}..?from=USD&to=IDR")
    days = sorted(d["rates"])
    return d["rates"][days[-1]]["IDR"], d["rates"][days[-2]]["IDR"], days[-1]


def emas():
    return get_json("https://api.gold-api.com/price/XAU")["price"]


def ihsg():
    """Yahoo Finance (tidak resmi). Bila gagal, bagian IHSG dilewati."""
    d = get_json("https://query1.finance.yahoo.com/v8/finance/chart/%5EJKSE?range=5d&interval=1d")
    closes = [c for c in d["chart"]["result"][0]["indicators"]["quote"][0]["close"] if c]
    return closes[-1], closes[-2]


def openalex(q=None, origin=None, year_from=None, year_to=None, frm=None, to=None, sort="cited_by_count:desc", per=25):
    f = ["primary_topic.field.id:20", "type:article", "has_abstract:true"]
    if q:
        f.append("title_and_abstract.search:" + urllib.parse.quote(q))
    if origin == "ID":
        f.append("authorships.countries:ID")
    elif origin == "INT":
        f.append("authorships.countries:!ID")
    if year_from:
        f.append(f"publication_year:{year_from}-{year_to}")
    if frm:
        f.append("from_publication_date:" + frm)
    if to:
        f.append("to_publication_date:" + to)
    sel = "id,doi,title,publication_year,publication_date,cited_by_count,counts_by_year,primary_location,abstract_inverted_index"
    url = f"https://api.openalex.org/works?filter={','.join(f)}&sort={sort}&per_page={per}&select={sel}"
    return get_json(url)["results"]


def abstrak(w, n=2, maks=380):
    inv = w.get("abstract_inverted_index") or {}
    pos = {}
    for word, ps in inv.items():
        for p in ps:
            pos[p] = word
    t = " ".join(pos[k] for k in sorted(pos))
    t = re.sub(r"^(abstract|abstrak)\s*[:.\-–]?\s*", "", t, flags=re.I).strip()
    kal = re.findall(r"[^.!?]+[.!?]+(?=\s|$)", t) or [t]
    out = " ".join(s.strip() for s in kal[:n])
    return (out[:maks].rsplit(" ", 1)[0] + "…") if len(out) > maks else out


def terjemah(t):
    """Terjemahkan ke Bahasa Indonesia (layanan Google Translate gratis, tidak resmi).
    Jika gagal, teks asli dipakai. Matikan dengan TERJEMAH=0."""
    if not t or os.environ.get("TERJEMAH", "1") == "0":
        return t
    try:
        url = ("https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=id&dt=t&q="
               + urllib.parse.quote(t))
        data = get_json(url, timeout=15)
        out = "".join(seg[0] for seg in data[0] if seg and seg[0])
        return out or t
    except Exception as e:
        print("terjemah gagal:", e, file=sys.stderr)
        return t


def judul(w):
    return re.sub(r"<[^>]+>", "", w.get("title") or "(tanpa judul)")


def sumber(w):
    loc = w.get("primary_location") or {}
    return (loc.get("source") or {}).get("display_name") or "—"


def link(w):
    return w.get("doi") or (w.get("primary_location") or {}).get("landing_page_url") or w["id"]


def sitasi_baru(w):
    return sum(c["cited_by_count"] for c in w.get("counts_by_year", []) if c["year"] >= YEAR - 1)


# ---------------- susun pesan ----------------
def susun():
    doy = TODAY.timetuple().tm_yday
    nama_bidang, q = BIDANG[TODAY.weekday()]
    L = [f"*RINGKASAN EKONOMI HARIAN*",
         f"{HARI[TODAY.weekday()]}, {TODAY.day} {BULAN[TODAY.month]} {YEAR}", ""]

    # Pasar
    L.append("*📈 Pasar & Investasi*")
    usd = None
    try:
        usd, prev, tgl = kurs()
        p = pct(usd, prev)
        L.append(f"• USD/IDR Rp{nf(usd, 0)} — Rupiah {arah(-p, 'menguat', 'melemah') if p is not None else ''} (kurs ref. {tgl})")
    except Exception as e:
        print("kurs gagal:", e, file=sys.stderr)
    try:
        g = emas()
        line = f"• Emas dunia US${nf(g)}/oz"
        if usd:
            line += f" ≈ Rp{nf(g * usd / 31.1034768, 0)}/gram (sebelum biaya cetak & pajak)"
        L.append(line)
    except Exception as e:
        print("emas gagal:", e, file=sys.stderr)
    try:
        c, pc = ihsg()
        L.append(f"• IHSG {nf(c)} ({arah(pct(c, pc))} pada penutupan terakhir)")
    except Exception as e:
        print("ihsg gagal:", e, file=sys.stderr)
    L.append("")

    # Indikator & analisis
    ind, diperbarui = indikator()
    v = lambda k: float(ind[k]["nilai"]) if k in ind else None
    L.append("*🇮🇩 Ekonomi Indonesia*")
    for k, label in [("pdb", "PDB"), ("inflasi", "Inflasi"), ("bi_rate", "BI-Rate"), ("cadev", "Cadev"),
                     ("neraca", "Neraca dagang"), ("defisit", "Defisit APBN"), ("ntp", "NTP")]:
        if k in ind:
            i = ind[k]
            L.append(f"• {label}: {nf(float(i['nilai']))} {i['satuan']} ({i['periode']})")
    L.append("")
    L.append("*🧭 Analisis singkat*")
    bi, inf, dfs, ntp = v("bi_rate"), v("inflasi"), v("defisit"), v("ntp")
    if bi is not None and inf is not None:
        real = bi - inf
        sas = "di atas" if inf > 3.5 else "di bawah" if inf < 1.5 else "dalam"
        L.append(f"• Inflasi {sas} sasaran BI 2,5±1%; suku bunga riil ≈ {nf(real)}% "
                 f"{'(cukup ketat, menopang Rupiah)' if real > 2 else '(masih positif)' if real > 0 else '(negatif)'}.")
    if dfs is not None:
        L.append(f"• Defisit APBN {nf(dfs)}% PDB, {'masih di bawah' if dfs < 3 else 'melewati'} batas 3% PDB.")
    if ntp is not None:
        L.append(f"• NTP {nf(ntp)} {'> 100: daya tukar petani surplus' if ntp > 100 else '< 100: daya tukar petani tertekan'}.")
    L.append(f"_Angka indikator per {diperbarui}_")
    L.append("")

    # Berita teratas (dari data/berita.json yang diperbarui tiap jam)
    try:
        bj = json.loads((ROOT / "data" / "berita.json").read_text(encoding="utf-8"))
        nama_tema = {"moneter": "Moneter", "fiskal": "Fiskal", "pasar": "Pasar", "pertanian": "Pertanian",
                     "energi": "Energi", "syariah": "Syariah", "global": "Global", "makro": "Makro",
                     "politik": "Kebijakan"}
        pilih, dipakai = [], set()
        for b in bj.get("berita", []):
            if b.get("bahasa") == "id" and b["tema"] not in dipakai:
                pilih.append(b); dipakai.add(b["tema"])
            if len(pilih) == 5:
                break
        if pilih:
            L.append("*📰 Berita Ekonomi Terkini*")
            for b in pilih:
                L.append(f"• [{nama_tema.get(b['tema'], 'Ekonomi')}] {b['judul']} — _{b['sumber']}_")
            L.append("")
    except Exception as e:
        print("berita gagal:", e, file=sys.stderr)

    # Headline riset
    try:
        res = openalex(frm=(TODAY - timedelta(days=365)).isoformat(), to=TODAY.isoformat(), per=10)
        h = next((w for w in res if (w.get("publication_year") or 0) >= YEAR - 1), res[0])
        L.append("*🔥 Headline Riset*")
        L.append(f"_{judul(h)}_ — {sumber(h)}, {h['cited_by_count']} sitasi sejak terbit {h.get('publication_date', '')}.")
        L.append(link(h))
        L.append("")
    except Exception as e:
        print("headline gagal:", e, file=sys.stderr)

    # Jurnal fondasi (rotasi harian, tanpa mengulang hari berikutnya)
    L.append(f"*📚 Jurnal Fondasi — {nama_bidang}*")
    for origin, label, geser in [("INT", "Internasional", 0), ("ID", "Nasional", 3)]:
        try:
            res = openalex(q=q, origin=origin, year_from=YEAR - 20, year_to=YEAR - 2)
            if not res:
                continue
            w = res[(doy + geser) % len(res)]
            L.append(f"{label}: _{judul(w)}_ ({sumber(w)}, {w['publication_year']}; {w['cited_by_count']} sitasi, "
                     f"{sitasi_baru(w)} dalam 2 tahun terakhir)")
            L.append(f"Ringkasan: {terjemah(abstrak(w))}")
            L.append(link(w))
            L.append("")
        except Exception as e:
            print("fondasi gagal:", e, file=sys.stderr)

    # Jurnal terbaru
    L.append(f"*🆕 Jurnal Terbaru — {nama_bidang}*")
    for origin, label, hari in [("INT", "Internasional", 30), ("ID", "Nasional", 60)]:
        try:
            res = openalex(q=q, origin=origin, frm=(TODAY - timedelta(days=hari)).isoformat(),
                           to=TODAY.isoformat(), sort="publication_date:desc", per=5)
            if not res:
                continue
            w = res[0]
            L.append(f"{label}: _{judul(w)}_ ({sumber(w)}, {w['publication_date']})")
            L.append(f"Ringkasan: {terjemah(abstrak(w))}")
            L.append(link(w))
            L.append("")
        except Exception as e:
            print("terbaru gagal:", e, file=sys.stderr)

    dash = os.environ.get("DASHBOARD_URL", "").strip()
    if dash:
        L.append(f"Baca lengkap di dashboard: {dash}")
    L.append("_Bukan rekomendasi investasi._")
    return "\n".join(L)


# ---------------- kirim ----------------
def kirim_callmebot(phone, apikey, text):
    # CallMeBot memakai GET; pesan panjang dipecah agar URL tidak terlalu panjang
    bagian, buf = [], ""
    for para in text.split("\n\n"):
        if len(buf) + len(para) > 1400:
            bagian.append(buf)
            buf = ""
        buf += (("\n\n" if buf else "") + para)
    if buf:
        bagian.append(buf)
    for b in bagian:
        url = ("https://api.callmebot.com/whatsapp.php?phone=+" + phone +
               "&text=" + urllib.parse.quote(b) + "&apikey=" + urllib.parse.quote(apikey))
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
            print("CallMeBot:", r.status)


def kirim_fonnte(phone, token, text):
    body = urllib.parse.urlencode({"target": phone, "message": text, "countryCode": "62"}).encode()
    req = urllib.request.Request("https://api.fonnte.com/send", data=body,
                                 headers={"Authorization": token, **UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        print("Fonnte:", r.status, r.read().decode()[:200])


def main():
    pesan = susun()
    print(pesan)
    print("\n---", len(pesan), "karakter ---")
    phone = re.sub(r"\D", "", os.environ.get("WA_PHONE", "62895353066404"))
    if os.environ.get("FONNTE_TOKEN"):
        kirim_fonnte(phone, os.environ["FONNTE_TOKEN"], pesan)
    elif os.environ.get("CALLMEBOT_APIKEY"):
        kirim_callmebot(phone, os.environ["CALLMEBOT_APIKEY"], pesan)
    else:
        print("Mode uji: CALLMEBOT_APIKEY / FONNTE_TOKEN belum diisi, pesan tidak dikirim.")


if __name__ == "__main__":
    main()
