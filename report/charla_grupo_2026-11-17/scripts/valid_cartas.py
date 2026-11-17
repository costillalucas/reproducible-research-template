"""Figuras 'valid_1.png' ... 'valid_4.png': las cuatro tarjetas de validacion.png, una por archivo,
para revelarlas de a una en la pregunta 3 (de la prueba más obvia a la menos obvia).

Reusa validacion.py (misma figura, mismas mini-imágenes simuladas): recorta cada tarjeta
(567 x 838 px) y le repinta el número, porque el orden de la charla no es el de validacion.png:
objeto conocido (1), predecir lo no visto (2), dos mitades (3), control nulo (4)."""
import io
import os
from PIL import Image, ImageDraw, ImageFont
from matplotlib import font_manager
import validacion as V
from idioma import salida

AQUI = os.path.dirname(os.path.abspath(__file__))
# número de cada tarjeta de validacion.png, de izquierda a derecha:
# objeto conocido 1 · dos mitades 3 · control nulo 4 · predecir lo no visto 2
NUMEROS = (1, 3, 4, 2)
Y0, ALTO = 31, 838                 # filas del recorte (la tarjeta va de la fila 30 a la 870)
DISCO = (24, 33, 92, 101)          # disco del número, en px del recorte (tapa el de validacion.png)
NEGRITA = ImageFont.truetype(
    font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans", weight="bold")), 44)

buf = io.BytesIO()
V.dibujar().savefig(buf, format="png", dpi=V.DPI, facecolor=V.BG)
buf.seek(0)
hoja = Image.open(buf).convert("RGB")
assert hoja.size == (V.W, V.H)
for n, x0 in zip(NUMEROS, V.X0):
    carta = hoja.crop((x0, Y0, x0 + V.CW, Y0 + ALTO))
    d = ImageDraw.Draw(carta)
    d.ellipse(DISCO, fill=V.ACC)
    d.text((59, 68), str(n), font=NEGRITA, fill=V.BG, anchor="mm")
    out = salida(f"valid_{n}.png", AQUI)
    carta.save(out)
    print(out)
