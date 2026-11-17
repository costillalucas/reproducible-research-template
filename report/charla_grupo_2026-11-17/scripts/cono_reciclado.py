"""Figura 'cono_reciclado.png' (1800 x 960): ¿qué LEDs dan campo claro? Dos pasos.

Recicla puente.png (2400 x 1050, tres pasos): se queda con el paso 1 (geometría) y el paso 3
(regla sen θ contra NA), saca el paso 2 (Fourier, que va al anexo), renumera la regla como
paso 2 y dibuja una flecha nueva entre los dos. No vuelve a simular nada: recorta la imagen
que genera puente.py, así que el idioma lo hereda de ese archivo (si falta, corre puente.py)."""
import os
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont
from matplotlib import font_manager
from idioma import EN, salida

AQUI = os.path.dirname(os.path.abspath(__file__))
BG, NJ, NJC = "#F6F4EE", "#A9471A", "#E8925E"      # fondo, naranja oscuro y claro de puente.py
W, H = 1800, 960
Y0 = 30                            # se descartan 30 px de arriba y la frase final de abajo
X_REGLA, CORRE = 1430, 600         # el paso 3 empieza en x = 1430 y se corre 600 px a la izquierda


def puente():
    """puente.png del idioma en curso; si no está, lo genera con puente.py."""
    if EN:
        lugares = [os.path.join(AQUI, "..", "figuras_en", "puente.png")]
    else:
        lugares = [os.path.join(AQUI, "puente.png"), os.path.join(AQUI, "..", "figuras", "puente.png")]
    for p in lugares:
        if os.path.isfile(p):
            return p
    subprocess.run([sys.executable, os.path.join(AQUI, "puente.py")], check=True, cwd=AQUI)
    return lugares[0]


src = puente()
P = Image.open(src).convert("RGB")
assert P.size == (2400, 1050), P.size
out = Image.new("RGB", (W, H), BG)
out.paste(P.crop((0, Y0, 720, Y0 + H)), (0, 0))                                 # paso 1
out.paste(P.crop((X_REGLA, Y0, 2400, Y0 + H)), (X_REGLA - CORRE, 0))            # paso 3 -> paso 2

d = ImageDraw.Draw(out)
# flecha entre los dos pasos (antes se borran las dos de puente.png, que quedaron en los recortes)
d.rectangle((676, 440, 720, 510), fill=BG)
d.rectangle((826, 440, 862, 510), fill=BG)
d.rectangle((735, 452, 775, 488), fill=NJC)
d.polygon([(775, 432), (775, 508), (815, 470)], fill=NJC)
# el disco del número: "3" -> "2"
negrita = ImageFont.truetype(
    font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans", weight="bold")), 36)
d.ellipse((853, 20, 907, 74), fill=NJ)
d.text((880, 47), "2", font=negrita, fill="white", anchor="mm")

dst = salida("cono_reciclado.png", AQUI)
out.save(dst)
print(f"{src} -> {dst}")
