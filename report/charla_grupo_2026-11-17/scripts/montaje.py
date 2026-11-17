"""Diapositiva 4: "FPM: un LED en el montaje es un disco en Fourier".

Panel izquierdo: montaje en vista lateral (esquema, escala vertical comprimida).
Panel derecho: plano de Fourier A ESCALA (mosaico de la matriz 21x21).
Miniaturas: imagenes coherentes simuladas (pupila desplazada) para LED A y B.
"""
import os
import numpy as np
from idioma import EN, T, num, salida
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle, Ellipse, FancyArrowPatch
from matplotlib.path import Path

# ----------------------------------------------------------------- fisica
LAM = 0.63          # um
NA = 0.07
Z = 100.0           # mm
PASO = 6.0          # mm
N_LADO = 21
XA, XB = 6.0, 24.0  # mm, posicion de los LEDs A y B sobre el eje x

def sen(x, y=0.0, z=Z):
    """sin(theta) exacto por eje: x / sqrt(x^2 + y^2 + z^2)."""
    return x / np.sqrt(x * x + y * y + z * z)

R_PUP = NA / LAM
SA, SB = sen(XA), sen(XB)
FA, FB = SA / LAM, SB / LAM
idx = (np.arange(N_LADO) - N_LADO // 2) * PASO
GX, GY = np.meshgrid(idx, idx)
RR = np.sqrt(GX**2 + GY**2 + Z**2)
KX, KY = GX / RR / LAM, GY / RR / LAM
NA_IL_EJE = sen(idx.max())                       # LED extremo sobre un eje
NA_IL_DIAG = np.hypot(GX, GY).max() / RR.max()   # LED de la esquina
NA_SINT = NA_IL_EJE + NA
NA_SINT_DIAG = NA_IL_DIAG + NA

def c(v, n=3):
    return num(v, n).replace("-", "−")
SEN = T("sen", "sin")

# ----------------------------------------------------------------- simulacion
def simular():
    n, dx = 512, 0.5                      # px, um/px  (Nyquist 1 um^-1)
    rng = np.random.default_rng(7)
    x = (np.arange(n) - n / 2) * dx
    X, Y = np.meshgrid(x, x)
    fase = np.zeros((n, n)); amp = np.ones((n, n))
    puestos = []
    while len(puestos) < 9:
        r = rng.uniform(9, 24); cx, cy = rng.uniform(-128 + r + 8, 128 - r - 8, 2)
        if any(np.hypot(cx - a, cy - b) < r + q + 6 for a, b, q in puestos):
            continue
        puestos.append((cx, cy, r))
        rho = np.hypot(X - cx, Y - cy)
        dentro = np.clip((r - rho) / dx + 0.5, 0, 1)      # borde antialias
        if len(puestos) % 3 == 0:                          # disco plano
            fase += 0.9 * dentro
        else:                                              # esfera de fase
            fase += 1.6 * np.sqrt(np.clip(1 - (rho / r) ** 2, 0, 1))
        amp *= 1 - 0.18 * dentro                           # absorcion debil
    obj = amp * np.exp(1j * fase)
    O = np.fft.fft2(obj)
    f = np.fft.fftfreq(n, dx)
    FX, FY = np.meshgrid(f, f)
    def foto(fled):
        # el objetivo deja pasar el disco del espectro centrado en f_led
        P = (np.hypot(FX - fled, FY) <= R_PUP)
        return np.abs(np.fft.ifft2(O * P)) ** 2
    return foto(FA), foto(FB)

IA, IB = simular()

# ----------------------------------------------------------------- estilo
BG, T1, T2 = "#F6F4EE", "#1B2333", "#3E4756"
AZ, NJ, NJC = "#2F6690", "#A9471A", "#E8925E"
G1, G2 = "#C9CCD1", "#8A909B"
FS, FST = 22, 27        # pt a 100 dpi -> 30,6 px y 37,5 px
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": FS,
                     "text.color": T1, "axes.edgecolor": T2,
                     "axes.labelcolor": T1, "xtick.color": T2, "ytick.color": T2})

W, H = 2400, 1100
fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=BG)

# ================================================================= montaje
# Layout en pixeles: esquema (izq., toda la altura) | columna de fotos | Fourier
S_M = 14.6                           # px por unidad del esquema
CX_M, BY_M = 560, 84                 # px del eje optico y del borde inferior
YL = (-3, 59.5)
XL = (-CX_M / S_M + 0.3, (1190 - CX_M) / S_M)
axm = fig.add_axes([(CX_M + XL[0] * S_M) / W, BY_M / H, (XL[1] - XL[0]) * S_M / W, (YL[1] - YL[0]) * S_M / H])
axm.set_xlim(XL); axm.set_ylim(YL)
axm.set_aspect("equal"); axm.axis("off")
def titulo(x, y, fuerte, suave):
    t = fig.text(x, y, fuerte, fontsize=FST, weight="bold", va="baseline")
    fig.canvas.draw()
    x1 = t.get_window_extent().x1 / W
    fig.text(x1 + 0.008, y, suave, fontsize=FS, color=T2, va="baseline")
titulo(0.020, 0.945, T("El montaje", "The setup"), T("(esquema, no a escala)", "(sketch, not to scale)"))

YLED, YM, YOB, YOB2, YTL, YCAM = 4.0, 22.0, 34.0, 44.0, 49.0, 55.0
ZD = YM - YLED                       # 100 mm dibujados como ZD unidades
# compresion vertical uniforme: x en mm reales, z*ZD/100  ->  las relaciones
# "entra / no entra" se conservan exactamente.
half = (YOB - YM) * (np.tan(np.arcsin(NA)) * Z / ZD)       # semiapertura dibujada

axm.plot([0, 0], [1.5, 58.5], color=G2, lw=1.5, ls=(0, (8, 4, 2, 4)), zorder=1)
# placa de LEDs
HL = 0.7                             # semiancho dibujado de cada LED
axm.add_patch(Rectangle((-28.5, YLED - 1.9), 57, 1.5, fc=G1, ec=T2, lw=1.5, zorder=2))
for k in range(-4, 5):
    xk = k * PASO
    col = AZ if xk == XA else NJ if xk == XB else "#E3E1DA"
    axm.add_patch(Rectangle((xk - HL, YLED - 0.5), 2 * HL, 1.6, fc=col, ec=T2, lw=1.5, zorder=3))
for s in (-1, 1):
    axm.text(s * 32, YLED - 0.6, "···", ha="center", va="center", color=G2, fontsize=FS)
axm.text(2.5, -1.2, T("LEDs: 21×21, paso 6 mm", "LEDs: 21×21, 6 mm pitch"), ha="right", va="center", color=T2)
# cota z
axm.annotate("", (-27, YLED - 0.4), (-27, YM), arrowprops=dict(arrowstyle="<->", color=T2, lw=2))
axm.text(-28.2, (YLED + YM) / 2, "z ≈\n100 mm", ha="right", va="center", color=T2, linespacing=1.25)
# muestra
axm.add_patch(Rectangle((-15, YM - 0.6), 30, 1.2, fc="#DDE6EC", ec=T2, lw=1.5, zorder=4))
for xs in (-6, -2.5, 0, 3.5, 8):
    axm.add_patch(Circle((xs, YM), 0.42, fc=T2, ec="none", zorder=5))
axm.text(17, YM, T("muestra", "sample"), va="center", color=T1)
# cono de aceptacion
axm.add_patch(Polygon([(0, YM), (-half, YOB), (half, YOB)], fc=T2, alpha=0.16, ec="none", zorder=2))
# limite de NA a rayas (mismo estilo que el circulo del plano de Fourier): del punto
# iluminado a los bordes de la lente frontal, y prolongado hasta la matriz de LEDs.
# Misma pendiente arriba y abajo (half / (YOB - YM)): a z = 100 mm el cono abarca
# +-tan(asin(NA))*Z = +-7,0 mm -> A (6 mm) queda adentro y B (24 mm) afuera.
PEND = half / (YOB - YM)
YPL = YLED - 0.4                     # cara superior de la placa
for s in (-1, 1):
    axm.plot([s * PEND * (YM - YPL), 0, s * half], [YPL, YM, YOB], color="#1F4E79", lw=2.6,
             ls=(0, (5, 3)), zorder=2.5, solid_capstyle="butt")
axm.text(6.3, 31.4, T(f"cono de aceptación\n(NA {c(NA, 2)})", f"acceptance cone\n(NA {c(NA, 2)})"), va="center", color="#1F4E79", linespacing=1.25)
# objetivo
axm.add_patch(Polygon([(-half, YOB), (half, YOB), (6.8, YOB + 3.2), (6.8, YOB2), (-6.8, YOB2), (-6.8, YOB + 3.2)],
                      fc=G1, ec=T2, lw=2, zorder=6))
axm.text(9.5, 42.3, T("objetivo 2,5× / NA 0,07", "2.5× objective / NA 0.07"), va="center", weight="bold")
# (rotulo acepta ±4 quitado) axm.text(9.5, 38.0, "acepta ±4°\n(dibujado exagerado)", va="center", color=T2, linespacing=1.25)
# espacio infinito + lente de tubo + camara
axm.add_patch(Polygon([(-3.4, YOB2), (3.4, YOB2), (3.4, YTL), (0, YCAM), (-3.4, YTL)], fc=T2, alpha=0.13, ec="none", zorder=2))
axm.add_patch(Ellipse((0, YTL), 17, 2.3, fc="#DDE6EC", ec=T2, lw=2, zorder=6))
axm.text(11, YTL, T("lente de tubo", "tube lens"), va="center")
axm.add_patch(Rectangle((-7.5, YCAM), 15, 3.2, fc=T2, ec=T1, lw=1.5, zorder=6))
axm.text(9.5, YCAM + 1.6, T("cámara: una foto por LED", "camera: one photo per LED"), va="center", weight="bold")

# rayos directos
def punto(x0, y):                     # recta LED(x0) -> centro de la muestra
    return x0 * (1 - (y - YLED - 0.9) / (YM - YLED - 0.9))
y0 = YLED + 1.1
axm.annotate("", (punto(XA, YOB), YOB), (XA, y0), zorder=7,
             arrowprops=dict(arrowstyle="-|>,head_length=0.7,head_width=0.3", color=AZ, lw=4, shrinkA=0, shrinkB=0))
yfin = 42.5
axm.annotate("", (punto(XB, yfin), yfin), (XB, y0), zorder=7,
             arrowprops=dict(arrowstyle="-|>,head_length=0.7,head_width=0.3", color=NJ, lw=4, shrinkA=0, shrinkB=0))
# luz difractada de B
axm.annotate("", (2.2, YOB - 0.3), (0.3, YM + 0.9), zorder=8,
             arrowprops=dict(arrowstyle="-|>,head_length=0.6,head_width=0.25", color=NJC, lw=3, ls=(0, (3, 2)), shrinkA=0, shrinkB=0))
axm.text(7.5, 26.3, T("luz difractada", "diffracted light"), va="center", color=NJ)
# rotulos de LEDs y regimen
axm.text(XA + 3.0, 8.3, "A", color=AZ, weight="bold", ha="center", va="center", fontsize=FS + 2)
axm.text(XB + 3.2, 8.3, "B", color=NJ, weight="bold", ha="center", va="center", fontsize=FS + 2)
axm.text(-5.6, 12.5, T("campo claro", "bright field"), color=AZ, weight="bold", ha="right", va="center")
axm.text(11.0, 16.3, T("campo oscuro", "dark field"), color=NJ, weight="bold", ha="left", va="center")
axm.text(-36.3, 49.5, T("el haz directo de B\nno entra al objetivo", "the direct beam of B\nmisses the objective"), color=NJ, ha="left", va="center", linespacing=1.25)

# ================================================================= Fourier
LIM = 1.02
FX0, FY0, SF = 1570, 262, 700        # px: esquina inferior izquierda y lado
axf = fig.add_axes([FX0 / W, FY0 / H, SF / W, SF / H]); axf.set_xlim(-LIM, LIM); axf.set_ylim(-LIM, LIM)
axf.set_aspect("equal"); axf.set_facecolor("#FBFAF6")
titulo(FX0 / W, 0.945, T("El plano de Fourier", "The Fourier plane"), T("(a escala)", "(to scale)"))
fig.text(FX0 / W, 0.905, T("cada disco: radio NA/λ", "each disk: radius NA/λ") + f" = {c(R_PUP)} µm⁻¹", fontsize=FS, color=T2, va="center")
for kx, ky in zip(KX.ravel(), KY.ravel()):
    axf.add_patch(Circle((kx, ky), R_PUP, fc=G2, alpha=0.07, ec="none", zorder=1))
    axf.add_patch(Circle((kx, ky), R_PUP, fc="none", ec=G2, alpha=0.55, lw=0.9, zorder=2))
axf.add_patch(Circle((0, 0), NA_SINT / LAM, fc="none", ec=T1, lw=2.6, ls=(0, (2, 3)), zorder=4))
for f0, col in ((FA, AZ), (FB, NJ)):
    axf.add_patch(Circle((f0, 0), R_PUP, fc=col, alpha=0.38, ec="none", zorder=5))
    axf.add_patch(Circle((f0, 0), R_PUP, fc="none", ec=col, lw=3.5, zorder=6))
axf.add_patch(Circle((0, 0), R_PUP, fc="none", ec="#1F4E79", lw=3.0, ls=(0, (5, 3)), zorder=7))
caja = dict(boxstyle="round,pad=0.18", fc=BG, ec="none", alpha=0.90)
axf.annotate(T(f"límite NA {c(NA, 2)} (rayas):\nsi el centro del disco cae\nadentro → campo claro", f"NA {c(NA, 2)} limit (dashed):\nif the disk center falls\ninside → bright field"),
             (-R_PUP * 0.707, R_PUP * 0.707), (-0.42, 0.66), ha="center", va="center", zorder=9, bbox=caja,
             color="#1F4E79", fontsize=FS, linespacing=1.25,
             arrowprops=dict(arrowstyle="-", color="#1F4E79", lw=1.8, shrinkA=4, shrinkB=0))
axf.plot(0, 0, marker="+", ms=20, mew=3.2, color=T1, zorder=8)
axf.annotate(T("orden cero", "zero order"), (-0.035, 0.0), (-0.20, 0.0), ha="right", va="center", zorder=9, bbox=caja,
             arrowprops=dict(arrowstyle="-", color=T1, lw=1.8, shrinkA=2, shrinkB=0))
axf.text(FA + 0.12, -0.225, T("A: campo claro", "A: bright field"), color=AZ, weight="bold", ha="center", va="center", bbox=caja, zorder=9)
axf.text(FB + 0.04, 0.205, T("B: campo oscuro", "B: dark field"), color=NJ, weight="bold", ha="left", va="center", bbox=caja, zorder=9)
axf.text(0, -0.62, T("apertura sintética (punteado)", "synthetic aperture (dotted)") + "\n"
         f"NA ≈ {c(NA_IL_EJE, 2)} + {c(NA, 2)} = {c(NA_SINT, 2)}",
         ha="center", va="center", bbox=caja, zorder=9, linespacing=1.3)
tk = [-1, -0.5, 0, 0.5, 1]
axf.set_xticks(tk); axf.set_yticks(tk)
axf.set_xticklabels([c(t, 1) if t % 1 else c(t, 0) for t in tk])
axf.set_yticklabels([c(t, 1) if t % 1 else c(t, 0) for t in tk])
axf.yaxis.tick_right(); axf.yaxis.set_label_position("right")
axf.set_xlabel("$f_x$  (µm⁻¹)"); axf.set_ylabel("$f_y$  (µm⁻¹)")
axf.tick_params(length=6, width=1.5)

# ================================================================= columna central de fotos
# B arriba y A abajo: asi cada flecha (LED -> foto -> disco) llega sin cruzar a la otra.
PX0, PT = 1230, 260                  # px: borde izquierdo y lado de las fotos
YB_B, YB_A = 728, 236                # px: borde inferior de cada foto
vA = 1.7 * np.median(IA); vB = np.percentile(IB, 99.7)
for yb, im, vm, col, lineas in (
        (YB_B, IB, vB, NJ, [(T("foto del LED B", "photo of LED B"), 1), (T("campo oscuro", "dark field"), 1), (f"{SEN} θ = {c(SB)} > NA", 0),
                            (T(f"(brillo ×{round(vA / vB, -1):.0f})", f"(brightness ×{round(vA / vB, -1):.0f})"), 0)]),
        (YB_A, IA, vA, AZ, [(T("foto del LED A", "photo of LED A"), 1), (T("campo claro", "bright field"), 1), (f"{SEN} θ = {c(SA)} < NA", 0)])):
    a = fig.add_axes([PX0 / W, yb / H, PT / W, PT / H]); a.imshow(im, cmap="gray", vmin=0, vmax=vm)
    a.set_xticks([]); a.set_yticks([])
    for s in a.spines.values():
        s.set_edgecolor(col); s.set_linewidth(5)
    for i, (t, fuerte) in enumerate(lineas):
        fig.text((PX0 + PT / 2) / W, (yb - 33 - i * 42) / H, t, ha="center", va="center",
                 color=col if fuerte else T2, weight="bold" if fuerte else "normal")

# ================================================================= mensaje
fig.text(0.5, 0.040, T("cada foto mide un disco del espectro; los discos vecinos se solapan y el algoritmo los cose", "each photo measures one disk of the spectrum; neighboring disks overlap and the algorithm stitches them"),
         ha="center", va="center", fontsize=FST, color=T1, weight="bold")

# ================================================================= flechas LED -> foto -> disco
fig.canvas.draw()
ov = fig.add_axes([0, 0, 1, 1]); ov.set_xlim(0, W); ov.set_ylim(0, H); ov.axis("off"); ov.patch.set_alpha(0)
pm = axm.transData.transform; pf = axf.transData.transform
def flecha(p0, c1, c2, p1, col):
    """Bezier cubica en px: sale de p0 hacia c1 y llega a p1 desde c2."""
    cam = Path([p0, c1, c2, p1], [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4])
    ov.add_patch(FancyArrowPatch(path=cam, color=col, lw=2.6,
                                 arrowstyle="-|>,head_length=12,head_width=5.5", zorder=20))
def borde_disco(f0, grados, extra=0.0):
    a = np.deg2rad(grados)
    return np.array(pf((f0 + (R_PUP + extra) * np.cos(a), (R_PUP + extra) * np.sin(a))))
G = 7                                # px de aire entre la punta y el borde de la foto
# --- B: LED -> foto (arriba) -> disco
b0 = np.array(pm((XB + HL, YLED + 0.9)))
flecha(b0 + (3, 0), b0 + (190, 12), (PX0 - 110, YB_B + 120), (PX0 - G, YB_B + 120), NJ)
b1 = borde_disco(FB, 112)
flecha((PX0 + PT + G, YB_B + 22), (PX0 + PT + 150, YB_B + 22), borde_disco(FB, 112, 0.42), b1, NJ)
# --- A: LED -> foto (abajo) -> disco
a0 = np.array(pm((XA, YLED - 2.1)))
flecha(a0, a0 + (110, -100), (PX0 - 140, YB_A - 120), (PX0 - G, YB_A + 70), AZ)
a1 = borde_disco(FA, 205)
flecha((PX0 + PT + G, YB_A + 205), (PX0 + PT + 140, YB_A + 205), borde_disco(FA, 205, 0.40), a1, AZ)

out = salida("montaje.png", os.path.dirname(os.path.abspath(__file__)))
fig.savefig(out, dpi=100, facecolor=BG)
print(f"sen A = {SA:.4f}  fA = {FA:.4f} um^-1 | sen B = {SB:.4f}  fB = {FB:.4f} um^-1")
print(f"radio pupila = {R_PUP:.4f} um^-1 | A contiene origen: {FA < R_PUP} | B: {FB < R_PUP}")
print(f"NA_ilum max: eje {NA_IL_EJE:.4f}, diagonal {NA_IL_DIAG:.4f}")
print(f"NA sintetica: eje {NA_SINT:.4f}, diagonal {NA_SINT_DIAG:.4f}")
print(f"brillo DF/BF: vmax A {vA:.3g}, vmax B {vB:.3g}, factor {vA / vB:.1f}")
