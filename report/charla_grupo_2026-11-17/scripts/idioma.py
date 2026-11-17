"""Selector de idioma para las figuras de la charla.

Uso:   FIG_LANG=en python script.py      (por defecto: es)

    from idioma import EN, T, num, salida
    T("Período", "Period")          # texto según idioma
    num(0.185, 3)                   # '0,185' (es) / '0.185' (en)
    fig.savefig(salida("q2.png", AQUI))

En español todo queda exactamente como antes (la salida va junto al script).
En inglés la salida va a ../figuras_en/ con el mismo nombre de archivo.
"""
import os

LANG = os.environ.get("FIG_LANG", "es").lower()
EN = LANG == "en"


def T(es, en):
    return en if EN else es


def num(x, n=3):
    """Número con n decimales: coma decimal en español, punto en inglés."""
    s = f"{x:.{n}f}"
    return s if EN else s.replace(".", ",")


def salida(nombre, aqui):
    """Ruta de salida: junto al script en es; ../figuras_en/ en en."""
    if not EN:
        return os.path.join(aqui, nombre)
    d = os.path.join(os.path.dirname(os.path.abspath(aqui)) if os.path.isfile(aqui) else aqui, "..", "figuras_en")
    d = os.path.normpath(d)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, nombre)
