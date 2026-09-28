"""Arma el PDF del resumen: resumen.md -> resumen.html -> resumen.pdf.

- [srcnum:clave:valor] se muestra como el valor con coma decimal; [src:clave] como una referencia
  numerada al anexo de fuentes, que se arma con data/numbers.json (statement + reproduce).
- ![texto](ruta){w=NN} es una figura con NN % del ancho y el texto como epígrafe.
Antes, verificar las etiquetas: python3 scripts/check_provenance.py report/resumen/resumen.md
Correr desde la raíz del repo: python3 report/resumen/build.py
"""
import json
import os
import re
import subprocess

import markdown

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
REG = json.load(open(os.path.join(ROOT, "data", "numbers.json")))
md = open(os.path.join(HERE, "resumen.md")).read()

refs = []


def ref(key):
    if key not in refs:
        refs.append(key)
    return f'<sup class="ref"><a href="#f-{key}">{refs.index(key) + 1}</a></sup>'


md = re.sub(r"\[srcnum:([^:\]]+):([^\]]+)\]", lambda m: m.group(2).replace(".", ","), md)
md = re.sub(r"\[src:([^\]]+)\]", lambda m: "".join(ref(k.strip()) for k in m.group(1).split(",")), md)
md = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)\{w=(\d+)\}",
            lambda m: (f'<figure class="medio"><img src="{m.group(2)}" style="width:92%"><figcaption>{m.group(1)}</figcaption></figure>'
                       if int(m.group(3)) <= 50 and "img/fig_" in m.group(2) and "informe" not in m.group(2) else
                       f'<figure><img src="{m.group(2)}" style="width:{m.group(3)}%"><figcaption>{m.group(1)}</figcaption></figure>'), md)
# python-markdown needs a blank line before a list that follows a paragraph line
lines, prev = [], ""
for ln in md.split("\n"):
    if re.match(r"(- |\d+\. )", ln) and prev.strip() and not re.match(r"(- |\d+\. |\s)", prev):
        lines.append("")
    lines.append(ln); prev = ln
md = "\n".join(lines)
body = markdown.markdown(md, extensions=["tables"])

anexo = "".join(
    f'<li id="f-{k}"><b>{REG[k]["statement"]}</b><br><code>{REG[k]["reproduce"]}</code></li>' for k in refs)
css = """
@page { size: A4; margin: 14mm 16mm 13mm 16mm }
body { font-family: 'Source Serif 4', Georgia, serif; font-size: 10pt; line-height: 1.33; color: #1d2433 }
h1 { font-family: 'IBM Plex Sans', Arial, sans-serif; font-size: 17pt; line-height: 1.2; color: #14213D; margin: 0 0 4px }
h1 + p { color: #6A7382; margin-top: 0 }
h2 { font-family: 'IBM Plex Sans', Arial, sans-serif; font-size: 12.5pt; color: #14213D; margin: 14px 0 4px;
     border-bottom: 1px solid #DDDBD2; padding-bottom: 2px }
p, li { margin: 4px 0 }
table { border-collapse: collapse; width: 100%; font-size: 9pt; margin: 6px 0; font-family: 'IBM Plex Sans', Arial, sans-serif }
th, td { border-bottom: 1px solid #DDDBD2; padding: 3px 5px; text-align: left; vertical-align: top }
th { border-bottom: 1.5px solid #14213D }
figure { display: inline-block; vertical-align: top; width: 100%; margin: 5px 0; text-align: center; break-inside: avoid }
figure.medio { width: 49% }
figcaption { font-size: 8.8pt; color: #4a5568; margin-top: 2px; text-align: left; padding: 0 6% }
code { font-size: 8.6pt; background: #F1F0EA; padding: 0 2px }
sup.ref a { color: #D9692B; text-decoration: none; font-size: 7pt }
.anexo { break-before: page; font-size: 8.4pt; line-height: 1.3 }
.anexo li { margin: 3px 0 }
"""
html = (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Resumen del trabajo FPM</title>'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&'
        f'family=Source+Serif+4:ital,wght@0,400;0,600;1,400&display=swap"><style>{css}</style></head><body>{body}'
        f'<section class="anexo"><h2>Anexo: fuente de cada número</h2><p>Cada número del texto está en '
        '<code>data/numbers.json</code>, escrito por <code>scripts/compute_numbers.py</code>, y se verifica con '
        '<code>scripts/check_provenance.py report/resumen/resumen.md</code>.</p>'
        f'<ol>{anexo}</ol></section></body></html>')
out_html = os.path.join(HERE, "resumen.html")
open(out_html, "w").write(html)
subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={os.path.join(HERE, 'resumen.pdf')}", f"file://{out_html}"],
               check=True, stderr=subprocess.DEVNULL)
print("escrito", os.path.relpath(os.path.join(HERE, "resumen.pdf"), ROOT), "|", len(refs), "fuentes")
