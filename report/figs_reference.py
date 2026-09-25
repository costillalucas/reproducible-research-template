"""Figures about the elefante reference and the effective magnification.

fig06 and fig07 read the lab's images under ~/Documents/AleYLu (not in the
repo); fig07's second panel and fig13 read results/ (not tracked).
See roadmap sections 6.7-6.9.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy.signal import fftconvolve

import figstyle as fs

ALEYLU = Path.home() / "Documents" / "AleYLu"
LR_CAPTURE = ALEYLU / "img_ref_recortada_1120.tif"          # on-axis green LED
REFERENCE = ALEYLU / "img_mov_alineada_recortada_1120.tif"  # reference used
ZEISS_TILE = ALEYLU / "elefante" / "2025-12-02" / "3x3" / "3x3_S0000(TR1)_C00_M0000_ORG.tif"
RESULTS = fs.REPO / "results"

ZEISS_UM_PER_PX = 2.344     # Zeiss metadata, 2.5x/0.075, 1.0x tube lens
CAMERA_PX_UM = 3.2          # FPM camera pixel


def _load(path: Path) -> np.ndarray:
    a = np.asarray(Image.open(path), dtype=float)
    return a.mean(axis=2) if a.ndim == 3 else a


def _radial_power_db(a: np.ndarray, n_bins: int = 20):
    """Hann-windowed radial power spectrum; x = fraction of Nyquist,
    y = dB relative to the 0.05-0.10 band (same recipe as roadmap 6.8)."""
    s = min(a.shape)
    a = a[:s, :s] - a[:s, :s].mean()
    a = a * np.outer(np.hanning(s), np.hanning(s))
    p = np.abs(np.fft.fftshift(np.fft.fft2(a))) ** 2
    y, x = np.indices(p.shape)
    r = np.hypot((y - s // 2) / (s / 2), (x - s // 2) / (s / 2))
    edges = np.linspace(0, 1, n_bins + 1)
    power = np.array([p[(r >= edges[i]) & (r < edges[i + 1])].mean()
                      for i in range(n_bins)])
    centers = 0.5 * (edges[:-1] + edges[1:])
    return centers, 10 * np.log10(power / power[1])


def fig06_espectro_referencia() -> Path:
    """Radial spectra: one LR capture vs the reference vs the raw Zeiss tile."""
    series = [
        ("Captura FPM (LED central, 1 imagen LR)", _load(LR_CAPTURE), fs.SERIES[0]),
        ("Referencia usada (Zeiss registrado a la grilla FPM)", _load(REFERENCE), fs.SERIES[1]),
        ("Tile Zeiss crudo (2.5x/0.075)", _load(ZEISS_TILE), fs.SERIES[2]),
    ]
    fig = plt.figure(figsize=(12, 5.6))
    gs = fig.add_gridspec(3, 2, width_ratios=[2.4, 1], hspace=0.35, wspace=0.12)
    ax = fig.add_subplot(gs[:, 0])
    for label, img, color in series:
        x, db = _radial_power_db(img)
        ax.plot(x, db, color=color, marker="o", markersize=5, label=label)
        fs.direct_label(ax, x[-1], db[-1], f"{db[-1]:.0f} dB")
    ax.axvspan(0.7, 1.0, color=fs.GRID, alpha=0.5, lw=0)
    ax.text(0.85, 12, "la referencia ya\nes piso de ruido", ha="center",
            va="top", color=fs.INK_2, fontsize=10)
    ax.set_xlim(0, 1.08)
    ax.set_xlabel("frecuencia espacial (fracción del Nyquist de la grilla LR)")
    ax.set_ylabel("potencia (dB, relativa a la banda 0.05–0.10)")
    ax.set_title("La referencia tiene menos detalle fino que una sola captura LR")
    ax.legend(loc="lower left")

    for i, (label, img, _) in enumerate(series):
        axi = fig.add_subplot(gs[i, 1])
        s = min(img.shape)
        c = img[s // 2 - 100:s // 2 + 100, s // 2 - 100:s // 2 + 100]
        lo, hi = np.percentile(c, [1, 99])
        axi.imshow(c, cmap=fs.AMP_CMAP, vmin=lo, vmax=hi)
        axi.set_xticks([]); axi.set_yticks([]); axi.grid(False)
        axi.set_title(label.split(" (")[0], fontsize=10, fontweight="normal")
    fs.caption(fig, "Por eso la correlación contra esta referencia no puede "
                    "validar superresolución (roadmap 6.8). Recortes centrales de 200x200 px.")
    return fs.save(fig, "fig06_espectro_referencia")


def _ncc_vs_scale(scales, rot_deg: float = 2.0, crop: int = 800):
    tile = _load(ZEISS_TILE)
    ref = _load(REFERENCE)[:, ::-1]  # registration flipped columns
    ref = np.asarray(Image.fromarray(ref.astype(np.float32)).rotate(rot_deg, Image.BICUBIC), float)
    h = (ref.shape[0] - crop) // 2
    ref = ref[h:h + crop, h:h + crop]  # centre only: avoids rotated borders
    out = []
    for s in scales:
        n = int(round(crop * s))
        q = np.asarray(Image.fromarray(ref.astype(np.float32)).resize((n, n), Image.LANCZOS), float)
        q = (q - q.mean()) / q.std() / q.size
        ones = np.ones_like(q)
        num = fftconvolve(tile, q[::-1, ::-1], "valid")
        mu = fftconvolve(tile, ones, "valid") / q.size
        var = fftconvolve(tile ** 2, ones, "valid") / q.size - mu ** 2
        out.append(float((num / np.sqrt(np.maximum(var, 1e-9))).max()))
    return np.array(out)


def fig07_aumento_efectivo() -> Path:
    """Where the reference sits inside the Zeiss tile -> FPM pixel size."""
    scales = np.round(np.arange(0.52, 0.8001, 0.01), 3)
    ncc = _ncc_vs_scale(scales)
    best = scales[int(np.argmax(ncc))]
    px_um = best * ZEISS_UM_PER_PX

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13, 5.2),
                                  gridspec_kw={"width_ratios": [1.5, 1], "wspace": 0.3})
    ax.plot(scales, ncc, color=fs.SERIES[0], marker="o", markersize=5)
    for s, lab in [(1.28 / ZEISS_UM_PER_PX, "esperado 2.5x\n(1.28 µm/px)"),
                   (1.60 / ZEISS_UM_PER_PX, "esperado 2x\n(1.60 µm/px)")]:
        ax.axvline(s, color=fs.NOISE_REF, lw=1.2, ls="--")
        ax.text(s, 0.99, lab, transform=ax.get_xaxis_transform(), ha="center",
                va="top", color=fs.INK_2, fontsize=9,
                bbox=dict(fc=fs.SURFACE, ec="none", pad=1))
    ax.annotate(f"pico NCC {ncc.max():.2f}\nescala {best:.3f} → {px_um:.2f} µm/px\n"
                f"aumento efectivo ≈ {CAMERA_PX_UM / px_um:.2f}x",
                (best, ncc.max()), xytext=(-150, -80), textcoords="offset points",
                color=fs.INK, fontsize=10,
                arrowprops=dict(arrowstyle="-", color=fs.INK_2, lw=1))
    ax.set_ylim(ncc.min() - 0.05, 1.0)
    ax.set_xlabel("escala referencia → tile Zeiss (µm/px FPM ÷ 2.344 µm/px Zeiss)")
    ax.set_ylabel("correlación cruzada normalizada (NCC)")
    ax.set_title(f"La referencia calza en el Zeiss a ~{px_um:.2f} µm/px: ni 2.5x ni 2x")

    # Panel 2: NA x pixel from the red intensity-spectrum cutoff (fork A).
    summ = json.loads((RESULTS / "mag_check_2025-12-12" / "summary.json").read_text())
    red = summ["method_1_intensity_spectrum_cutoff"]["red_630nm"]
    meas, unc = red["NA_times_px_sample_um"], red["unc_um"]
    hyp = summ["hypotheses_vs_NA_times_px"]
    rows = [("2.5x / NA 0.07\n(config vieja)", hyp["config current 2.5x/0.07 (px 1.28)"]["predicted"]),
            ("2x / NA 0.10\n(nominal)", hyp["nominal 2x/0.10 (px 1.60)"]["predicted"]),
            ("1.75 µm/px (Zeiss)\n+ NA 0.10", hyp["Zeiss-registration px 1.746 + NA 0.10"]["predicted"])]
    y = np.arange(len(rows))[::-1]
    ax2.barh(y, [v for _, v in rows], height=0.5, color=fs.SERIES[0])
    ax2.axvspan(meas - unc, meas + unc, color=fs.SERIES[1], alpha=0.35, lw=0)
    ax2.axvline(meas, color=fs.SERIES[1], lw=2)
    ax2.text(meas, len(rows) - 0.35, f" medido {meas:.3f} ± {unc:.3f} µm", color=fs.INK,
             fontsize=10, ha="right", va="bottom")
    for yi, (_, v) in zip(y, rows):
        ax2.text(v, yi, f" {v:.3f}", va="center", color=fs.INK, fontsize=10)
    ax2.set_yticks(y, [r for r, _ in rows])
    ax2.set_xlim(0, 0.24)
    ax2.set_ylim(-0.6, len(rows) - 0.1)
    ax2.grid(axis="y", visible=False)
    ax2.set_xlabel("NA × píxel en muestra (µm)")
    ax2.set_title("Corte espectral (rojo): mejor ajuste\n~1.83x con NA ~0.11", fontsize=12)
    fs.caption(fig, "Izq.: búsqueda de la referencia (columnas invertidas, rotada 2°) dentro del "
                    "tile Zeiss 3x3. Der.: NA·px medido del corte del espectro de intensidad vs. "
                    "predicciones de cada hipótesis (roadmap 6.8).")
    return fs.save(fig, "fig07_aumento_efectivo")


def fig13_correlacion_vs_iteraciones() -> Path:
    """Historical: reference correlation vs WF iterations, old vs fixed objective."""
    old = json.loads((RESULTS / "sweep_finegrained_green.json").read_text())["rows"]
    new = json.loads((RESULTS / "sweep_green_future" / "sweep_green_future.json").read_text())["rows"]
    extras = json.loads((RESULTS / "sweep_green_future" / "extras_lrgrid_phase_spectrum.json").read_text())
    old_pts = {r["iterations"]: r["reference_correlation"] for r in old}
    new_pts = {r["iterations"]: r["reference_correlation"] for r in new}
    for e in extras:  # iteration 0 and 200 points from fork B's extras
        (new_pts if e["objective"] == "future" else old_pts).setdefault(
            e["iterations"], e["ref_corr_hr_grid"])

    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    for pts, color, lab in [(old_pts, fs.C_BAD, "objetivo viejo 2.5x/0.07"),
                            (new_pts, fs.C_OK, "objetivo corregido 2x/0.10")]:
        it = sorted(pts)
        x = [max(i, 0.5) for i in it]  # iteration 0 drawn at 0.5 on the log axis
        ax.plot(x, [pts[i] for i in it], color=color, marker="o", markersize=6, label=lab)
        fs.direct_label(ax, x[-1], pts[it[-1]], f"{pts[it[-1]]:.3f}")
    ax.set_xscale("log")
    ax.set_xticks([0.5, 1, 10, 100, 200], ["0", "1", "10", "100", "200"])
    ax.set_xlim(0.4, 400)
    ax.set_xlabel("iteraciones de WF")
    ax.set_ylabel("correlación con la referencia (grilla HR)")
    ax.set_title("Contexto histórico: la correlación nunca superó a la imagen inicial")
    ax.legend(loc="lower left")
    ax.text(0.03, 0.62, "Solver congelado (paso ≈ 1/8000 del ePIE)\n"
                        "y referencia sin alta resolución:\n"
                        "no mide calidad de reconstrucción",
            transform=ax.transAxes, ha="left", va="top", color=fs.INK,
            fontsize=10, bbox=dict(fc=fs.GRID, ec="none", pad=6))
    fs.caption(fig, "Figura histórica (roadmap 6.7, corregida en 6.8–6.9). "
                    "Verde, crop 400, captura 2025-12-12.")
    return fs.save(fig, "fig13_correlacion_vs_iteraciones")


FIGURES = {
    "fig06_espectro_referencia": fig06_espectro_referencia,
    "fig07_aumento_efectivo": fig07_aumento_efectivo,
    "fig13_correlacion_vs_iteraciones": fig13_correlacion_vs_iteraciones,
}
