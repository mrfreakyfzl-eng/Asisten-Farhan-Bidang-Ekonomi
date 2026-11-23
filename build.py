"""Gabungkan data/indikator.json ke dalam index.html (data cadangan saat dibuka tanpa server)."""
from pathlib import Path
root = Path(__file__).parent
tpl = (root / "src" / "index.template.html").read_text(encoding="utf-8")
data = (root / "data" / "indikator.json").read_text(encoding="utf-8").replace("</", "<\\/")
(root / "index.html").write_text(tpl.replace("/*INDIKATOR_JSON*/", data), encoding="utf-8")
print("index.html dibuat")
