"""PDF de la charla a partir de la versión ONLINE (la de referencia), con las figuras reales puestas.

1. Bajar las slides con la herramienta de Artifacts (read de project/deck.json y project/slides/*.html) a una carpeta.
2. python3 report/presentacion_agentes/pdf_desde_online.py <carpeta con project/>
   (inglés: python3 report/presentacion_agentes/pdf_desde_online.py report/presentacion_agentes/deck_english --en)
Cada recuadro de figura online es un <img alt="... (archivo NOMBRE.png)"> sin src: acá se reemplaza por la figura
de report/informe/img/NOMBRE.png. Escribe presentacion_agentes_ia.html, .pdf y notas_del_orador.txt.
Con --en (carpeta con las slides traducidas): figuras de report/informe/img_en/ y salida
presentacion_agentes_ia_english.html, .pdf y notas_del_orador_english.txt.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EN = "--en" in sys.argv[1:]
args = [a for a in sys.argv[1:] if a != "--en"]
SUF = "_english" if EN else ""
IMG = os.path.normpath(os.path.join(HERE, "..", "informe", "img_en" if EN else "img"))
src = os.path.join(args[0], "project")
deck = json.load(open(os.path.join(src, "deck.json")))
head = open(os.path.join(HERE, "head.html")).read()  # fuentes + CSS de impresión 1920x1080
if EN:
    head = head.replace('lang="es"', 'lang="en"').replace("Un mes con agentes de IA en microscopía", "A month with AI agents in microscopy")


def figura(m):
    tag = m.group(0)
    name = re.search(r"\(archivo ([^)]+)\)", tag).group(1)
    alt = re.sub(r"\s*\(archivo [^)]+\)", "", re.search(r'alt="([^"]*)"', tag).group(1))
    w = re.search(r"width:\s*(\d+)px", tag).group(1); h = re.search(r"height:\s*(\d+)px", tag).group(1)
    path = os.path.join(IMG, name)
    assert os.path.exists(path), path
    return f'<img src="file://{path}" alt="{alt}" style="width:{w}px; height:{h}px; object-fit:contain">'


body, notas = [], []
for n, sid in enumerate(deck["order"], 1):
    t = open(os.path.join(src, "slides", f"{sid}.html")).read()
    t = re.sub(r'<img alt="[^"]*\(archivo [^)]+\)"[^>]*>', figura, t)
    t = re.sub(r"<x-connector[^>]*></x-connector>", '<p style="font-size:44px; color:#6A7382">&#8594;</p>', t)
    t = t.replace("<section ", '<section class="slide" ', 1)
    body.append(t)
    a = re.search(r"<aside>(.*?)</aside>", t, re.S)
    notas.append(f"{n}. {sid}\n{a.group(1).strip() if a else ''}")
html = head + "<body>" + "".join(body) + "</body></html>"
out = os.path.join(HERE, f"presentacion_agentes_ia{SUF}.html")
open(out, "w").write(html)
open(os.path.join(HERE, f"notas_del_orador{SUF}.txt"), "w").write("\n\n".join(notas) + "\n")
subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={os.path.join(HERE, f'presentacion_agentes_ia{SUF}.pdf')}", f"file://{out}"],
               check=True, stderr=subprocess.DEVNULL)
print(len(deck["order"]), "slides ->", os.path.join(HERE, f"presentacion_agentes_ia{SUF}.pdf"))
