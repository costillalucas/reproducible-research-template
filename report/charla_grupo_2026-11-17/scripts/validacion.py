"""Figura 'validacion.png': cuatro pruebas de que el detalle reconstruido es real.
Mini-imagenes simuladas con numpy (imagen coherente con pupila circular)."""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle, FancyArrowPatch
from idioma import T, salida

BG, CARD, TXT, SEC, ACC, BLUE = "#16202E", "#22303F", "#F3EFE6", "#B8C2CF", "#E8925E", "#6FA8D6"
OFF = "#44546A"
W, H, DPI = 2400, 900, 100
PT = 72 / DPI                      # px -> pt
F_TIT, F_LIN, F_LAB = 38 * PT, 29 * PT, 28 * PT
plt.rcParams["font.family"] = "DejaVu Sans"
rng = np.random.default_rng(7)
N = 160
FC_FOTO, FC_REC = 1 / 14, 1 / 5    # cortes coherentes (ciclos/px)

fy, fx = np.meshgrid(np.fft.fftfreq(N), np.fft.fftfreq(N), indexing="ij")


def pupila(fc, kx=0.0, ky=0.0):
    return ((fx - kx) ** 2 + (fy - ky) ** 2 <= fc ** 2).astype(float)


def imagen(campo, fc, kx=0.0, ky=0.0):
    """Intensidad de la imagen coherente con iluminacion inclinada (kx, ky)."""
    return np.abs(np.fft.ifft2(np.fft.fft2(campo) * pupila(fc, kx, ky))) ** 2


def ruido_suave(fc, seed):
    r = np.random.default_rng(seed).standard_normal((N, N))
    r = np.real(np.fft.ifft2(np.fft.fft2(r) * pupila(fc)))
    return r / r.std()


def usaf():
    o = np.full((N, N), 0.12)
    def elem(x, y, w):
        for i in range(3):
            o[y:y + 5 * w, x + 2 * i * w:x + (2 * i + 1) * w] = 1        # barras verticales
            o[y + 2 * i * w:y + (2 * i + 1) * w, x + 6 * w:x + 11 * w] = 1  # horizontales
    elem(10, 10, 10); elem(10, 75, 6); elem(92, 80, 4); elem(10, 126, 3); elem(62, 129, 2)
    elem(100, 124, 3)
    o[18:40, 128:150] = 1
    return o


def muestra():
    """'Celulas': discos con textura fina adentro."""
    yy, xx = np.mgrid[:N, :N]
    blobs = np.zeros((N, N))
    for cx, cy, r in [(45, 48, 30), (112, 40, 22), (118, 108, 30), (48, 118, 24), (82, 80, 12)]:
        blobs = np.maximum(blobs, np.clip((r - np.hypot(xx - cx, yy - cy)) / 2.0, 0, 1))
    t = np.random.default_rng(3).standard_normal((N, N))
    t = np.real(np.fft.ifft2(np.fft.fft2(t) * (pupila(1 / 5.5) - pupila(1 / 9))))
    tex = (t > 0.15 * t.std()).astype(float)
    return 0.12 + 0.88 * blobs * (0.35 + 0.65 * tex)


U, M = usaf(), muestra()
u_foto, u_rec = imagen(U, FC_FOTO), imagen(U, FC_REC)
m_rec = imagen(M, FC_REC)
rec_a = m_rec + 0.035 * ruido_suave(FC_REC, 11)
rec_b = m_rec + 0.035 * ruido_suave(FC_REC, 12)
rec_nulo = imagen(M, FC_FOTO) + 0.04 * ruido_suave(1 / 8, 13)
k = 1.55 * FC_FOTO                 # LED de campo oscuro
df = [imagen(M, FC_FOTO, k * np.cos(a), k * np.sin(a)) for a in (0.3, 1.9, 3.5, 5.0)]
pred = imagen(M, FC_FOTO, k * np.cos(0.9), k * np.sin(0.9))
med = pred + 0.10 * pred.max() * np.sqrt(pred / pred.max() + 0.02) * rng.standard_normal((N, N))

fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=BG)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_facecolor(BG); ax.axis("off")


def img(a, x, y, s, vmax=None, borde=SEC):
    ax.imshow(a, cmap="gray", extent=(x, x + s, y, y + s), vmin=0,
              vmax=vmax if vmax else np.percentile(a, 99.7), interpolation="bilinear", zorder=3)
    ax.add_patch(Rectangle((x, y), s, s, fill=False, ec=borde, lw=2, zorder=4))


def etiqueta(x, y, s, color=SEC, **kw):
    ax.text(x, y, s, color=color, fontsize=F_LAB, ha="center", va="top", zorder=5, **kw)


def flecha(p0, p1, color=SEC, lw=4, estilo="-|>", rad=0.0):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle=estilo, mutation_scale=28, lw=lw, color=color,
                                 connectionstyle=f"arc3,rad={rad}", zorder=6, shrinkA=0, shrinkB=0))


def leds(x, y, s, color_de, n=7):
    ax.add_patch(FancyBboxPatch((x, y), s, s, boxstyle="round,pad=0,rounding_size=10",
                                fc=BG, ec=OFF, lw=2, zorder=3))
    p = s / n
    for i in range(n):
        for j in range(n):
            ax.add_patch(Circle((x + (i + .5) * p, y + (j + .5) * p), 0.33 * p,
                                color=color_de(i, j), zorder=4))


CW, GAP, MX = 567, 24, 30
titulos = [T("Objeto conocido", "Known object"), T("Dos mitades\nindependientes", "Two independent\nhalves"),
           T("Control nulo", "Null control"), T("Predecir\nlo no visto", "Predict\nthe unseen")]
lineas = [T("¿se separan barras de\ntamaño conocido?", "are bars of known\nsize resolved?"),
          T("¿coinciden más allá de lo que\nve el objetivo? (FRC)", "do they agree beyond what\nthe objective sees? (FRC)"),
          T("si destruyo el campo oscuro,\nel detalle tiene que\ndesaparecer", "if I destroy the dark field,\nthe detail has to\ndisappear"),
          T("¿predice fotos que no usó?", "does it predict photos it\ndid not use?")]
X0 = [MX + i * (CW + GAP) for i in range(4)]
for i, x0 in enumerate(X0):
    ax.add_patch(FancyBboxPatch((x0, 30), CW, 840, boxstyle="round,pad=0,rounding_size=28",
                                fc=CARD, ec="none", zorder=1))
    ax.add_patch(Circle((x0 + 58, 800), 33, color=ACC, zorder=3))
    ax.text(x0 + 58, 798, str(i + 1), color=BG, fontsize=F_TIT, fontweight="bold",
            ha="center", va="center", zorder=4)
    ax.text(x0 + 108, 800, titulos[i], color=TXT, fontsize=F_TIT, fontweight="bold",
            ha="left", va="center", linespacing=1.1, zorder=4)
    ax.text(x0 + 28, 218, lineas[i], color=TXT, fontsize=F_LIN, ha="left", va="top",
            linespacing=1.3, zorder=4)

# 1 - objeto conocido
x0 = X0[0]; s = 250
vm = np.percentile(u_rec, 99.5)
img(u_foto, x0 + 22, 410, s, vm); img(u_rec, x0 + 295, 410, s, vm, borde=ACC)
flecha((x0 + 275, 535), (x0 + 293, 535), lw=3)
etiqueta(x0 + 22 + s / 2, 395, T("foto", "photo")); etiqueta(x0 + 295 + s / 2, 395, T("reconstrucción", "reconstruction"), ACC)

# 2 - dos mitades
x0 = X0[1]; s = 195
leds(x0 + 22, 385, 215, lambda i, j: ACC if (i + j) % 2 == 0 else BLUE)
vm = np.percentile(m_rec, 99.7)
img(rec_a, x0 + 305, 525, s, vm, borde=ACC); img(rec_b, x0 + 305, 262, s, vm, borde=BLUE)
flecha((x0 + 243, 530), (x0 + 298, 610), ACC, rad=-0.2)
flecha((x0 + 243, 455), (x0 + 298, 370), BLUE, rad=0.2)
ax.text(x0 + 305 + s / 2, 490, "≈", color=TXT, fontsize=50 * PT, fontweight="bold", ha="center", va="center")
ax.text(x0 + 530, 622, "A", color=ACC, fontsize=F_TIT, fontweight="bold", ha="center", va="center")
ax.text(x0 + 530, 360, "B", color=BLUE, fontsize=F_TIT, fontweight="bold", ha="center", va="center")
etiqueta(x0 + 22 + 107, 372, T("LEDs en\ndos grupos", "LEDs in\ntwo groups"), linespacing=1.15)

# 3 - control nulo
x0 = X0[2]; t = 105; g = 12
vmd = np.percentile(np.array(df), 99.8)
pos = [(x0 + 22, 420 + t + g), (x0 + 22 + t + g, 420 + t + g), (x0 + 22, 420), (x0 + 22 + t + g, 420)]
for d, (px, py) in zip(df, pos):
    img(d, px, py, t, vmd, borde=OFF)
c = [(p[0] + t / 2, p[1] + t / 2) for p in pos]
flecha(c[0], c[3], ACC, lw=6, estilo="<|-|>", rad=0.25)
flecha(c[1], c[2], ACC, lw=6, estilo="<|-|>", rad=0.25)
flecha((x0 + 256, 531), (x0 + 296, 531))
img(rec_nulo, x0 + 305, 410, 240, vm)
etiqueta(x0 + 22 + t + g / 2, 395, T("campo oscuro\nmezclado", "dark field\nshuffled"), linespacing=1.15)
etiqueta(x0 + 305 + 120, 395, T("sin detalle", "no detail"))

# 4 - predecir lo no visto
x0 = X0[3]; s = 190
res = {(1, 5), (4, 6), (5, 2), (2, 1), (6, 4), (0, 3), (3, 3)}
leds(x0 + 40, 560, 170, lambda i, j: ACC if (i, j) in res else BLUE)
for yy_, col, lab in [(680, BLUE, T("usados", "used")), (610, ACC, T("reservados", "held out"))]:
    ax.add_patch(Circle((x0 + 262, yy_), 13, color=col, zorder=4))
    ax.text(x0 + 290, yy_, lab, color=col, fontsize=F_LAB, ha="left", va="center")
vmp = np.percentile(pred, 99.8)
img(pred, x0 + 60, 345, s, vmp, borde=BLUE); img(med, x0 + 317, 345, s, vmp, borde=ACC)
ax.text(x0 + 283.5, 440, "vs", color=SEC, fontsize=F_LAB, ha="center", va="center")
etiqueta(x0 + 60 + s / 2, 332, T("foto predicha", "predicted photo"), BLUE); etiqueta(x0 + 317 + s / 2, 332, T("foto medida", "measured photo"), ACC)

ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("auto")
fig.savefig(salida("validacion.png", os.path.dirname(os.path.abspath(__file__))),
            dpi=DPI, facecolor=BG)
