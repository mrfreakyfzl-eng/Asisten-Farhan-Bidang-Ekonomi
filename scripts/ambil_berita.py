#!/usr/bin/env python3
"""
Ambil berita ekonomi dari RSS media (CNBC Indonesia, CNN Indonesia, Antara, Detik, Tempo, dll.),
kelompokkan per tema, lalu simpan ke data/berita.json untuk dibaca dashboard.

Dijalankan otomatis tiap jam oleh .github/workflows/berita.yml. Hanya pustaka bawaan Python.
Menambah/mengganti sumber: ubah daftar FEEDS di bawah.
"""
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "berita.json"
UA = {"User-Agent": "Mozilla/5.0 (AsistenEkonomiHarian; +https://github.com)"}

# saring=True: feed umum, hanya artikel yang memuat kata kunci ekonomi yang diambil
FEEDS = [
    {"sumber": "CNBC Indonesia", "url": "https://www.cnbcindonesia.com/news/rss", "bahasa": "id", "saring": True},
    {"sumber": "CNBC Indonesia", "url": "https://www.cnbcindonesia.com/market/rss", "bahasa": "id", "tema": "pasar"},
    {"sumber": "CNBC Indonesia", "url": "https://www.cnbcindonesia.com/syariah/rss", "bahasa": "id", "tema": "syariah"},
    {"sumber": "CNN Indonesia", "url": "https://www.cnnindonesia.com/ekonomi/rss", "bahasa": "id"},
    {"sumber": "Antara", "url": "https://www.antaranews.com/rss/ekonomi.xml", "bahasa": "id"},
    {"sumber": "Detik Finance", "url": "https://finance.detik.com/rss", "bahasa": "id"},
    {"sumber": "Tempo Bisnis", "url": "https://rss.tempo.co/bisnis", "bahasa": "id"},
    {"sumber": "Republika Ekonomi", "url": "https://www.republika.co.id/rss/ekonomi", "bahasa": "id"},
    {"sumber": "Liputan6 Bisnis", "url": "https://feed.liputan6.com/rss/bisnis", "bahasa": "id"},
    # Agregator Google News: menjangkau Kontan, Bisnis.com, Kompas, Katadata, dll.
    {"sumber": "Google News", "url": "https://news.google.com/rss/search?q=ekonomi+indonesia+when:2d&hl=id&gl=ID&ceid=ID:id", "bahasa": "id"},
    {"sumber": "Google News", "url": "https://news.google.com/rss/search?q=bank+indonesia+OR+BPS+OR+APBN+when:2d&hl=id&gl=ID&ceid=ID:id", "bahasa": "id"},
    {"sumber": "Google News", "url": "https://news.google.com/rss/search?q=petani+OR+pangan+OR+perikanan+OR+kehutanan+when:3d&hl=id&gl=ID&ceid=ID:id", "bahasa": "id", "saring": True},
    # Ekonomi politik & kebijakan (berita politik hanya diambil bila menyangkut ekonomi/kebijakan)
    {"sumber": "Antara", "url": "https://www.antaranews.com/rss/politik.xml", "bahasa": "id", "tema": "politik", "kebijakan": True},
    {"sumber": "CNN Indonesia", "url": "https://www.cnnindonesia.com/nasional/rss", "bahasa": "id", "tema": "politik", "kebijakan": True},
    {"sumber": "Google News", "url": "https://news.google.com/rss/search?q=kebijakan+ekonomi+OR+regulasi+OR+DPR+anggaran+OR+peraturan+pemerintah+when:2d&hl=id&gl=ID&ceid=ID:id", "bahasa": "id", "tema": "politik", "kebijakan": True},
    # Internasional (bahasa Inggris, bisa diterjemahkan di dashboard)
    {"sumber": "CNBC International", "url": "https://www.cnbc.com/id/20910258/device/rss/rss.html", "bahasa": "en", "tema": "global"},
    {"sumber": "CNBC International", "url": "https://www.cnbc.com/id/10000664/device/rss/rss.html", "bahasa": "en", "tema": "global"},
]

TEMA = {
    "moneter":   ["bank indonesia", "bi rate", "bi-rate", "suku bunga", "rupiah", "kurs", "inflasi", "moneter", "likuiditas", "kredit", "perbankan", "ojk", "lps", "dolar", "cadangan devisa", "interest rate", "central bank", "the fed", "fed "],
    "fiskal":    ["apbn", "pajak", "kemenkeu", "menkeu", "defisit", "utang", "sbn", "obligasi negara", "subsidi", "bea cukai", "anggaran", "belanja negara", "fiscal", "tax", "budget"],
    "pasar":     ["ihsg", "saham", "bursa", "emiten", "investor", "reksa dana", "obligasi", "emas", "antam", "harga emas", "kripto", "bitcoin", "idx", "ipo", "dividen", "stock", "gold", "market"],
    "pertanian": ["petani", "pertanian", "pangan", "beras", "padi", "jagung", "pupuk", "bulog", "sawit", "cpo", "kopi", "kakao", "perikanan", "nelayan", "ikan", "kelautan", "hutan", "kehutanan", "peternak", "ntp", "hortikultura", "cabai", "gula", "bapanas", "kementan"],
    "energi":    ["minyak", "bbm", "batu bara", "batubara", "listrik", "pln", "pertamina", "nikel", "tambang", "energi", "gas", "hilirisasi", "smelter", "oil", "energy", "coal"],
    "syariah":   ["syariah", "halal", "zakat", "wakaf", "sukuk", "islamic", "bsi"],
    "makro":     ["pertumbuhan ekonomi", "pdb", "bps", "ekspor", "impor", "neraca perdagangan", "investasi", "daya beli", "konsumsi", "pengangguran", "kemiskinan", "umkm", "ekonomi", "industri", "manufaktur", "pmi", "gdp", "economy", "recession", "trade"],
    "politik":   ["dpr", "dpd", "mpr", "presiden", "wakil presiden", "kabinet", "istana", "kebijakan", "regulasi", "deregulasi", "peraturan pemerintah", "perpres", "inpres", "keppres", "undang-undang", "ruu", "omnibus", "pilkada", "pemilu", "partai", "koalisi", "oposisi", "danantara", "bumn", "kppu", "mahkamah konstitusi", "policy", "election", "parliament", "government"],
    "global":    ["global", "amerika", "china", "tiongkok", "tarif", "perang dagang", "imf", "bank dunia", "world bank", "tariff", "wall street", "europe"],
}
URUTAN_TEMA = ["moneter", "fiskal", "pasar", "pertanian", "energi", "syariah", "global", "politik", "makro"]
KATA_KEBIJAKAN = ["kebijakan", "regulasi", "deregulasi", "anggaran", "apbn", "perpres", "peraturan", "undang-undang", "ruu", "pajak", "subsidi", "investasi", "ekonomi", "bumn", "danantara", "tarif", "harga", "upah", "ump", "pangan", "energi", "fiskal", "moneter"]


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()


def bersih(t, maks=420):
    t = html.unescape(re.sub(r"<[^>]+>", " ", t or ""))
    t = re.sub(r"\s+", " ", t).strip()
    return (t[:maks].rsplit(" ", 1)[0] + "…") if len(t) > maks else t


def tanggal(s):
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
    except Exception:
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def gambar(item, desc_raw):
    for el in item.iter():
        tag = el.tag.split("}")[-1]
        if tag in ("content", "thumbnail") and el.get("url") and ("image" in (el.get("type") or "image") or el.get("medium") == "image"):
            return el.get("url")
        if tag == "enclosure" and el.get("url") and (el.get("type") or "").startswith("image"):
            return el.get("url")
    m = re.search(r'<img[^>]+src="([^"]+)"', desc_raw or "")
    return m.group(1) if m else None


def klasifikasi(teks, default=None):
    t = teks.lower()
    skor = {k: sum(1 for w in kw if re.search(r"(?<!\w)" + re.escape(w.strip()) + r"(?!\w)", t)) for k, kw in TEMA.items()}
    terbaik = max(URUTAN_TEMA, key=lambda k: (skor[k], -URUTAN_TEMA.index(k)))
    if skor[terbaik] == 0:
        return default, 0
    if default and skor.get(default, 0) >= skor[terbaik]:
        return default, skor[default]
    return terbaik, skor[terbaik]


def parse(feed):
    root = ET.fromstring(fetch(feed["url"]))
    items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    hasil = []
    for it in items:
        def txt(name):
            for el in it:
                if el.tag.split("}")[-1] == name:
                    return (el.text or "").strip() or el.get("href") or ""
            return ""
        judul = bersih(txt("title"), 300)
        link = txt("link")
        desc_raw = txt("description") or txt("summary") or txt("encoded")
        sumber = feed["sumber"]
        if feed["sumber"] == "Google News":
            src = next((el for el in it if el.tag.split("}")[-1] == "source"), None)
            if src is not None and src.text:
                sumber = src.text.strip()
                judul = re.sub(r"\s+-\s+" + re.escape(sumber) + r"\s*$", "", judul)
            desc = ""  # deskripsi Google News hanya berisi tautan
        else:
            desc = bersih(desc_raw)
        tema, skor = klasifikasi(judul + " " + desc, feed.get("tema"))
        if feed.get("saring") and skor == 0:
            continue
        if feed.get("kebijakan"):
            t = (judul + " " + desc).lower()
            if not any(re.search(r"(?<!\w)" + re.escape(k) + r"(?!\w)", t) for k in KATA_KEBIJAKAN):
                continue  # berita politik murni tanpa kaitan ekonomi/kebijakan dilewati
            tema = "politik"
        hasil.append({
            "judul": judul, "link": link, "ringkasan": desc, "gambar": gambar(it, desc_raw),
            "sumber": sumber, "tema": tema or "makro", "bahasa": feed["bahasa"],
            "waktu": (tanggal(txt("pubDate") or txt("published") or txt("updated")) or datetime.now(timezone.utc)).isoformat(),
        })
    return hasil


def main():
    semua, status = [], []
    for f in FEEDS:
        try:
            r = parse(f)
            semua += r
            status.append({"sumber": f["sumber"], "url": f["url"], "ok": True, "jumlah": len(r)})
        except Exception as e:
            status.append({"sumber": f["sumber"], "url": f["url"], "ok": False, "galat": str(e)[:120]})
            print("gagal:", f["url"], e, file=sys.stderr)
    batas = datetime.now(timezone.utc) - timedelta(days=4)
    unik, lihat = [], set()
    for b in sorted(semua, key=lambda x: x["waktu"], reverse=True):
        kunci = re.sub(r"\W+", "", b["judul"].lower())[:70]
        if not b["judul"] or kunci in lihat or datetime.fromisoformat(b["waktu"]) < batas:
            continue
        lihat.add(kunci)
        unik.append(b)
    data = {"diperbarui": datetime.now(timezone.utc).isoformat(), "sumber": status, "berita": unik[:400]}
    if not unik and OUT.exists():
        print("Tidak ada berita baru; file lama dipertahankan.")
        return
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(unik)} berita disimpan dari {sum(1 for s in status if s['ok'])}/{len(status)} sumber.")


if __name__ == "__main__":
    main()
