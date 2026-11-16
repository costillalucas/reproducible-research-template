"""Figuras a escala para la slide 'Proximo paso: alejar la matriz de LEDs a z ~ 143 mm'.
Genera siguiente.png (matriz vista desde arriba) y damero.png (espacio de Fourier).
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Wedge
from matplotlib.ticker import FuncFormatter, MultipleLocator

AQUI = os.path.dirname(os.path.abspath(__file__))

# ---------- parametros reales ----------
P = 6.0            # mm, paso de la matriz
N_LADO = 21        # grilla 21x21 centrada en el eje
NA = 0.070
NA_MIN, NA_MAX = 0.067, 0.074
LAM = 0.63         # um
ZS = (99.5, 143.0) # mm
R_MAX_CRUZ = 10 * P  # LED a 10 pasos en cruz

# ---------- estilo ----------
FONDO, TXT, TXT2 = "#F6F4EE", "#1B2333", "#3E4756"
ACENTO, AZUL, NARANJA_CL, GRIS = "#A9471A", "#2F6690", "#E8925E", "#B9B6AC"
DPI = 100
W_IN, H_IN = 24.0, 11.0          # -> 2400 x 1100 px


def px(n):
    """tamano de fuente en puntos para n pixeles reales"""
    return n * 72.0 / DPI


plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": TXT,
                     "axes.edgecolor": TXT2, "axes.labelcolor": TXT2,
                     "xtick.color": TXT2, "ytick.color": TXT2})


def coma(x, nd):
    return f"{x:.{nd}f}".replace(".", ",")


# ---------- fisica ----------
def r_borde(z, na):
    return z * np.tan(np.arcsin(na))


def sin_theta(r, z):
    return r / np.hypot(r, z)


def grilla():
    h = N_LADO // 2
    i = np.arange(-h, h + 1)
    return np.meshgrid(i, i)            # indices (col, fila) relativos al eje


def cuenta_bf(z, na):
    ix, iy = grilla()
    return int(np.sum(sin_theta(np.hypot(ix, iy) * P, z) < na))


def solapamiento(z, na):
    """fraccion del area de un disco de pupila compartida entre el LED central y el vecino a 6 mm"""
    d = sin_theta(P, z) / LAM
    u = d / (2 * na / LAM)
    return (2 / np.pi) * (np.arccos(u) - u * np.sqrt(1 - u * u))


def numeros():
    out = {}
    for z in ZS:
        out[z] = dict(
            rb=r_borde(z, NA), rb_min=r_borde(z, NA_MIN), rb_max=r_borde(z, NA_MAX),
            bf=cuenta_bf(z, NA), bf_min=cuenta_bf(z, NA_MIN), bf_max=cuenta_bf(z, NA_MAX),
            eta=solapamiento(z, NA), eta_min=solapamiento(z, NA_MIN), eta_max=solapamiento(z, NA_MAX),
            sin_cruz=sin_theta(P, z), sin_diag=sin_theta(P * np.sqrt(2), z), sin_2p=sin_theta(2 * P, z),
            na_il=sin_theta(R_MAX_CRUZ, z),
        )
        out[z]["na_sint"] = out[z]["na_il"] + NA
        out[z]["na_sint_min"] = out[z]["na_il"] + NA_MIN
        out[z]["na_sint_max"] = out[z]["na_il"] + NA_MAX
    return out


# ---------- figura 1 ----------
def fig_siguiente(nums):
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=DPI, facecolor=FONDO)
    alto = 0.585
    ancho = alto * H_IN / W_IN
    M = 4                                  # +-4 LEDs
    lim = M * P + 3.5
    for k, z in enumerate(ZS):
        n = nums[z]
        cx = 0.25 + 0.5 * k
        ax = fig.add_axes([cx - ancho / 2, 0.245, ancho, alto], facecolor=FONDO)
        ax.set_aspect("equal")
        ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
        # banda de incertidumbre NA 0,067-0,074
        ax.add_patch(Wedge((0, 0), n["rb_max"], 0, 360, width=n["rb_max"] - n["rb_min"],
                           facecolor=NARANJA_CL, alpha=0.45, edgecolor="none", zorder=1))
        ax.add_patch(Circle((0, 0), n["rb"], fill=False, edgecolor=ACENTO, lw=4, zorder=4))
        # LEDs
        nbf = 0
        for i in range(-M, M + 1):
            for j in range(-M, M + 1):
                x, y = i * P, j * P
                bf = sin_theta(np.hypot(x, y), z) < NA
                nbf += bf
                ax.add_patch(Circle((x, y), 1.25, facecolor=AZUL if bf else GRIS,
                                    edgecolor="none", zorder=3))
        assert nbf == n["bf"], "el recorte 9x9 debe contener todos los BF"
        ax.add_patch(Circle((0, 0), 1.25, fill=False, edgecolor=TXT, lw=3.5, zorder=5))
        ax.plot([0], [0], marker="+", color=FONDO, ms=16, mew=3, zorder=6)
        ax.xaxis.set_major_locator(MultipleLocator(12)); ax.yaxis.set_major_locator(MultipleLocator(12))
        ax.tick_params(labelsize=px(30), length=8, width=2)
        ax.set_xlabel("x sobre la matriz (mm)", fontsize=px(30), labelpad=6)
        if k == 0:
            ax.set_ylabel("y (mm)", fontsize=px(30), labelpad=2)
        for s in ax.spines.values():
            s.set_linewidth(1.8)
        # textos
        zt = coma(z, 1 if z < 100 else 0)
        fig.text(cx, 0.955, f"z = {zt} mm ({'actual' if k == 0 else 'propuesta'})  ·  borde de pupila a "
                 f"r = {coma(n['rb'], 2 if z < 100 else 1)} mm",
                 ha="center", va="center", fontsize=px(36), color=TXT2)
        fig.text(cx, 0.885, f"{n['bf']} LEDs de campo claro", ha="center", va="center",
                 fontsize=px(54), color=AZUL, fontweight="bold")
        fig.text(cx, 0.112, f"solapamiento entre vecinos ≈ {round(100 * n['eta']):d} %",
                 ha="center", va="center", fontsize=px(36), color=TXT)
        fig.text(cx, 0.064, f"NA de iluminación máxima (LED a 10 pasos en cruz) = {coma(n['na_il'], 2)}",
                 ha="center", va="center", fontsize=px(30), color=TXT2)
        fig.text(cx, 0.024, f"NA sintética = {coma(n['na_il'], 2)} + {coma(NA, 2)} ≈ {coma(n['na_sint'], 2)}",
                 ha="center", va="center", fontsize=px(30), color=TXT2)
    # leyenda central
    lax = fig.add_axes([0.435, 0.33, 0.13, 0.42], facecolor=FONDO)
    lax.set_xlim(0, 1); lax.set_ylim(0, 1); lax.axis("off")
    lax.plot([0.08], [0.90], "o", ms=26, color=AZUL); lax.text(0.2, 0.90, "campo claro", fontsize=px(30), va="center", color=TXT2)
    lax.plot([0.08], [0.72], "o", ms=26, color=GRIS); lax.text(0.2, 0.72, "campo oscuro", fontsize=px(30), va="center", color=TXT2)
    lax.plot([0.08], [0.54], "o", ms=26, mfc=AZUL, mec=TXT, mew=3.5); lax.text(0.2, 0.54, "LED central", fontsize=px(30), va="center", color=TXT2)
    lax.plot([0.0, 0.16], [0.36, 0.36], "-", lw=4, color=ACENTO); lax.text(0.2, 0.36, "NA 0,070", fontsize=px(30), va="center", color=TXT2)
    lax.add_patch(plt.Rectangle((0.0, 0.14), 0.16, 0.08, facecolor=NARANJA_CL, alpha=0.45, edgecolor="none"))
    lax.text(0.2, 0.18, "NA 0,067–\n0,074", fontsize=px(30), va="center", color=TXT2, linespacing=1.1)
    fig.savefig(os.path.join(AQUI, "siguiente.png"), dpi=DPI, facecolor=FONDO)
    plt.close(fig)


# ---------- figura 2 ----------
def fig_damero():
    z = ZS[0]
    R = NA / LAM
    M = 2                                   # vecindario 5x5
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=DPI, facecolor=FONDO)
    alto = 0.70
    ancho = alto * H_IN / W_IN
    lim = 0.36
    fmt = FuncFormatter(lambda v, _: coma(v, 1) if abs(v) > 1e-9 else "0")
    titulos = ("todos los LEDs", "una mitad (tablero)")
    for k in range(2):
        cx = 0.27 + 0.5 * k
        ax = fig.add_axes([cx - ancho / 2, 0.135, ancho, alto], facecolor=FONDO)
        ax.set_aspect("equal"); ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
        for i in range(-M, M + 1):
            for j in range(-M, M + 1):
                x, y = i * P, j * P
                d3 = np.sqrt(x * x + y * y + z * z)
                kx, ky = x / d3 / LAM, y / d3 / LAM
                usado = (k == 0) or ((i + j) % 2 == 0)
                if usado:
                    ax.add_patch(Circle((kx, ky), R, facecolor=AZUL, alpha=0.16, edgecolor="none", zorder=2))
                    ax.add_patch(Circle((kx, ky), R, fill=False, edgecolor=AZUL, lw=1.6, alpha=0.75, zorder=3))
                    ax.plot([kx], [ky], "o", ms=9, color=TXT, zorder=5)
                else:
                    ax.plot([kx], [ky], "o", ms=9, mfc=FONDO, mec=GRIS, mew=2.2, zorder=4)
        # disco del LED central resaltado
        ax.add_patch(Circle((0, 0), R, fill=False, edgecolor=ACENTO, lw=4, zorder=6))
        ax.xaxis.set_major_locator(MultipleLocator(0.1)); ax.yaxis.set_major_locator(MultipleLocator(0.1))
        ax.xaxis.set_major_formatter(fmt); ax.yaxis.set_major_formatter(fmt)
        ax.tick_params(labelsize=px(30), length=8, width=2)
        ax.set_xlabel(r"$k_x$ (µm$^{-1}$)", fontsize=px(32), labelpad=6)
        if k == 0:
            ax.set_ylabel(r"$k_y$ (µm$^{-1}$)", fontsize=px(32), labelpad=2)
        for s in ax.spines.values():
            s.set_linewidth(1.8)
        fig.text(cx, 0.915, titulos[k], ha="center", va="center", fontsize=px(46),
                 color=TXT, fontweight="bold")
    # columna central de leyenda
    lax = fig.add_axes([0.445, 0.25, 0.15, 0.50], facecolor=FONDO)
    lax.set_xlim(0, 1); lax.set_ylim(0, 1); lax.axis("off")
    lax.plot([0.07], [0.92], "o", ms=30, color=AZUL, alpha=0.3)
    lax.text(0.17, 0.92, "pupila de\ncada LED", fontsize=px(30), va="center", color=TXT2, linespacing=1.1)
    lax.plot([0.07], [0.68], "o", ms=30, mfc="none", mec=ACENTO, mew=4)
    lax.text(0.17, 0.68, "LED central\n(eje)", fontsize=px(30), va="center", color=TXT2, linespacing=1.1)
    lax.plot([0.07], [0.46], "o", ms=11, color=TXT)
    lax.text(0.17, 0.46, "k del LED", fontsize=px(30), va="center", color=TXT2)
    lax.plot([0.07], [0.30], "o", ms=11, mfc=FONDO, mec=GRIS, mew=2.2)
    lax.text(0.17, 0.30, "LED de la\notra mitad", fontsize=px(30), va="center", color=TXT2, linespacing=1.1)
    lax.text(0.0, 0.07, f"radio = NA/λ\n= {coma(R, 3)} µm⁻¹", fontsize=px(30), va="center", color=ACENTO, linespacing=1.15)
    fig.text(0.5, 0.027, f"espacio de Fourier a escala · z = {coma(z, 1)} mm · NA = {coma(NA, 3)} · "
             f"λ = {coma(LAM, 2)} µm · vecindario de 5×5 LEDs",
             ha="center", va="center", fontsize=px(30), color=TXT2)
    fig.savefig(os.path.join(AQUI, "damero.png"), dpi=DPI, facecolor=FONDO)
    plt.close(fig)
    return R


if __name__ == "__main__":
    nums = numeros()
    for z, n in nums.items():
        print(f"z = {z} mm")
        for kk, v in n.items():
            print(f"   {kk:12s} {v:.4f}" if isinstance(v, float) else f"   {kk:12s} {v}")
    fig_siguiente(nums)
    R = fig_damero()
    z = ZS[0]
    print("damero: R = NA/lam =", round(R, 4), "um^-1; dk vecino =", round(sin_theta(P, z) / LAM, 4),
          "; k LED a 12 mm =", round(sin_theta(2 * P, z) / LAM, 4))
