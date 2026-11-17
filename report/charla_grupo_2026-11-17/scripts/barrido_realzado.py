"""Figura 'barrido_realzado.gif' (780 x 384, 49 cuadros): barrido de 49 LEDs.

Izquierda: la foto de cada LED. Las de campo claro van en escala común; las de campo oscuro,
con realce propio (cada una normalizada a su máximo), porque son mucho más tenues.
Derecha: el espectro del objeto (log, realzado con gamma), con la ventana activa en naranja y
la cobertura acumulada iluminada; lo que todavía no se cubrió queda atenuado.

Simulación: el mismo modelo y el mismo objeto «mixto» de report/fourier_interactivo_v2/generate.py
(grilla 128, pupila de radio 18, paso 10 entre LEDs, muestra delgada, sin ruido).
No tiene texto: la versión en inglés es la misma animación, escrita en ../figuras_en/."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from idioma import salida

AQUI = os.path.dirname(os.path.abspath(__file__))
N, R_PUPILA, PASO = 128, 18, 10
ESC = 3                            # cada píxel de la simulación = 3 x 3 px
SEP, BG, NJC, HALO = 12, "#F6F4EE", "#E8925E", "#999999"
# realce del espectro (en niveles de 8 bits): ganancia * ((nivel - piso) / 255) ** gamma;
# fuera de la cobertura se atenúa antes del gamma y el piso es más alto
GAMMA, GANANCIA = 0.358, 1.086
PISO_DENTRO, PISO_FUERA, ATENUA = 1.3, 6.5, 0.36
MS, MS_FINAL = 700, 2000           # duración de cada cuadro y del último

Y, X = np.mgrid[:N, :N]
U, V = X - N // 2, Y - N // 2
F = lambda a: np.fft.fftshift(np.fft.fft2(a, norm="ortho"))
INV = lambda a: np.fft.ifft2(np.fft.ifftshift(a), norm="ortho")
# del centro hacia afuera, como en la demo
LEDS = sorted([(x, y) for y in range(-3, 4) for x in range(-3, 4)],
              key=lambda p: (p[0] ** 2 + p[1] ** 2, np.arctan2(p[1], p[0])))
CENTROS = [(-x * PASO, -y * PASO) for x, y in LEDS]
MASKS = [((U - cx) ** 2 + (V - cy) ** 2 <= R_PUPILA ** 2) for cx, cy in CENTROS]


def fuente_bitmap():
    """La fuente bitmap chica de Pillow (la que usó la figura original), en cualquier versión."""
    f = getattr(ImageFont, "load_default_imagefont", None)
    if f:
        return f()
    core = ImageFont.core
    try:                           # Pillow >= 10.1 con FreeType devuelve una TrueType más grande
        ImageFont.core = None
        return ImageFont.load_default()
    finally:
        ImageFont.core = core


def objeto():
    """Objeto «mixto» de la demo v2: amplitud dibujada + fase suave."""
    im = Image.new("L", (N, N), 220)
    d = ImageDraw.Draw(im)
    d.text((48, 52), "FPM", fill=50, font=fuente_bitmap())
    for k in range(7):
        d.rectangle((20 + 4 * k, 22, 21 + 4 * k, 43), fill=65)
        d.rectangle((78, 75 + 4 * k, 106, 76 + 4 * k), fill=75)
    d.ellipse((20, 77, 49, 106), outline=70, width=2)
    amp = np.asarray(im) / 255
    fase = .85 * np.exp(-((U - 20) ** 2 + (V + 26) ** 2) / 220) + .6 * np.exp(-((U + 28) ** 2 + (V - 24) ** 2) / 140)
    fase += .25 * (1 + np.cos(2 * np.pi * 10 * X / N)) * np.exp(-(U ** 2 + V ** 2) / 700)
    return amp * np.exp(1j * fase)


def gris(t):
    """Matriz 0..1 -> imagen RGB ampliada sin interpolar."""
    im = Image.fromarray(np.uint8(np.clip(t, 0, 1) * 255)).convert("RGB")
    return im.resize((N * ESC, N * ESC), Image.NEAREST)


S = F(objeto())
fotos = [np.abs(INV(S * m)) ** 2 for m in MASKS]
pico = max(i.max() for i in fotos)
claro = [cx ** 2 + cy ** 2 <= R_PUPILA ** 2 for cx, cy in CENTROS]   # el orden cero entra
esp = np.log1p(np.abs(S))
esp8 = np.floor(255 * esp / esp.max())             # el espectro como imagen de 8 bits (como en la demo)
print(f"{len(LEDS)} LEDs, {sum(claro)} de campo claro; campo oscuro mas brillante: "
      f"{max(i.max() for i, c in zip(fotos, claro) if not c) / pico:.3f} del pico")

cuadros, cubierto = [], np.zeros((N, N), bool)
for (cx, cy), m, foto, bf in zip(CENTROS, MASKS, fotos, claro):
    cubierto |= m
    nivel = np.where(cubierto, esp8 - PISO_DENTRO, ATENUA * (esp8 - PISO_FUERA)).clip(0) / 255
    realzado = GANANCIA * nivel ** GAMMA
    c = Image.new("RGB", (2 * N * ESC + SEP, N * ESC), BG)
    c.paste(gris(foto / (pico if bf else foto.max())), (0, 0))
    x0 = N * ESC + SEP
    c.paste(gris(realzado), (x0, 0))
    d = ImageDraw.Draw(c)
    px, py = x0 + ESC * (N // 2 + cx) + 1, ESC * (N // 2 + cy) + 1      # centro de la ventana activa
    r = ESC * R_PUPILA
    d.ellipse((px - r - 1, py - r - 1, px + r + 1, py + r + 1), outline=HALO, width=6)
    d.ellipse((px - r, py - r, px + r, py + r), outline=NJC, width=4)
    cuadros.append(c.quantize(colors=256, dither=Image.Dither.NONE))

out = salida("barrido_realzado.gif", AQUI)
cuadros[0].save(out, save_all=True, append_images=cuadros[1:], loop=0,
                duration=[MS] * (len(cuadros) - 1) + [MS_FINAL], optimize=False, disposal=1)
print(out)
