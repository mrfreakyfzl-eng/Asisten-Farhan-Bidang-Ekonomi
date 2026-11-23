"""Rakit index.html dari src/ (template + CSS + JS) dan data/indikator.json."""
from pathlib import Path
root = Path(__file__).parent
src = root / "src"
html = (src / "index.template.html").read_text(encoding="utf-8")
css = (src / "style.css").read_text(encoding="utf-8")
js = (src / "app.js").read_text(encoding="utf-8")
data = (root / "data" / "indikator.json").read_text(encoding="utf-8").replace("</", "<\\/")
assert "</script" not in js.lower()
out = html.replace("/*STYLE_CSS*/", css).replace("/*INDIKATOR_JSON*/", data).replace("/*APP_JS*/", js)
(root / "index.html").write_text(out, encoding="utf-8")
print("index.html dibuat:", len(out), "byte")
