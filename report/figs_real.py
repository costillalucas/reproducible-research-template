"""Figuras de datos reales (verde 2025-12-12) y de la validación sintética
con la geometría real. Roadmap secciones 6.9-6.10.

Fuentes (nada de esto está en el repo salvo results/, que no se trackea):
- results/synthetic_real_geometry/  (fork I: sintético con geometría real)
- results/residual_floor_2025-12-12/  (fork H: piso de residuo, ruido medido)
- results/geometry_search_2025-12-12/  (fork K: barrido de geometría + CV)
- results/led_geometry_2025-12-12/  (fork F: variantes congelada/descongelada)
- los paneles de imagen de fig08/fig09 salen de tres .npz chicos guardados al
  lado del script que los produjo (fig08_panels.npz, fig09_thawed_panels.npz,
  fig09_frozen_panel.npz): sólo las fases/amplitudes que se dibujan, en
  float32 y ya recortadas, con un .json de procedencia al lado de cada uno.
  Si falta alguno, `_need` dice el comando exacto que lo regenera.
- una captura LR cruda bajo ~/Documents/AleYLu (no está en el repo).
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image

import figstyle as fs

RESULTS = fs.REPO / "results"
SYNTH = RESULTS / "synthetic_real_geometry"
FLOOR = RESULTS / "residual_floor_2025-12-12"
GEOM = RESULTS / "geometry_search_2025-12-12"

# Paneles de imagen ya extraídos (ver el .json de procedencia de cada uno).
FIG08_PANELS = SYNTH / "fig08_panels.npz"
FIG09_THAWED = FLOOR / "fig09_thawed_panels.npz"
FIG09_FROZEN = RESULTS / "led_geometry_2025-12-12" / "fig09_frozen_panel.npz"

REGEN_FIG08 = ("OBJ=lenamap python3 results/synthetic_real_geometry/run.py && "
               "OBJ=scatter python3 results/synthetic_real_geometry/run.py "
               "(ver results/synthetic_real_geometry/fig08_panels.json)")
REGEN_THAWED = ("python3 results/residual_floor_2025-12-12/run.py step0.3 0.3 10 10 "
                "(ver results/residual_floor_2025-12-12/fig09_thawed_panels.json)")
REGEN_FROZEN = ("cd results/led_geometry_2025-12-12 && python3 run_variant.py "
                "ctl_norm_scaled_20 2.0 0.10 76 17.45 14.65 1 20 scaled "
                "(ver results/led_geometry_2025-12-12/fig09_frozen_panel.json)")

LR_DIR = (Path.home() / "Documents" / "AleYLu" / "imagenes_tomadas"
          / "2025-12-12" / "organizado" / "green" / "9x9_recortada_400")

ROWS = range(13, 22)            # filas de LED de la captura 9x9
COLS = range(11, 20)
LR_PX_UM = 1.6                  # 2x sobre píxel de cámara 3.2 µm
FACTOR = 5                      # upsampling -> píxel HR 0.32 µm
SEQ = LinearSegmentedColormap.from_list("seq_blue", fs.SEQ_BLUE)


def _need(path: Path, how: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(
            f"falta {path.relative_to(fs.REPO) if fs.REPO in path.parents else path}"
            f"; regenerar desde la raíz del repo con:  {how}")
    return path


def _bare(ax) -> None:
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)


def _scalebar(ax, n_px: int, px_um: float, um: float = 20.0) -> None:
    """Barra de escala abajo a la derecha, en tinta sobre fondo claro."""
    length = um / px_um
    x1 = n_px * 0.95
    x0, y = x1 - length, n_px * 0.93
    ax.plot([x0, x1], [y, y], color="white", lw=5, solid_capstyle="butt")
    ax.plot([x0, x1], [y, y], color=fs.INK, lw=2.5, solid_capstyle="butt")
    ax.text((x0 + x1) / 2, y - n_px * 0.025, f"{um:.0f} µm", ha="center",
            va="bottom", color=fs.INK, fontsize=9,
            bbox=dict(fc="white", ec="none", pad=0.8, alpha=0.75))


def _phase_colorbar(fig, mappable, cax, label="fase (rad)"):
    cb = fig.colorbar(mappable, cax=cax,
                      ticks=[-np.pi, -np.pi / 2, 0, np.pi / 2, np.pi])
    cb.ax.set_yticklabels(["−π", "−π/2", "0", "π/2", "π"])
    cb.set_label(label, color=fs.INK_2)
    cb.outline.set_visible(False)
    return cb


def _panel_note(ax, text: str) -> None:
    """Cifras del panel, en tinta, debajo de la imagen (sin tapar nada)."""
    ax.text(0.5, -0.02, text, transform=ax.transAxes, ha="center", va="top",
            color=fs.INK, fontsize=10)


def _sign(v: float, nd: int = 2) -> str:
    return f"{v:+.{nd}f}".replace("-", "−")


# --------------------------------------------------------------------------
# fig08: sintético con la geometría real (fork I)
# --------------------------------------------------------------------------

def _synth_runs(variant: str) -> dict:
    runs = json.loads((SYNTH / f"summary_{variant}.json").read_text())["runs"]
    return {r["label"]: r for r in runs}


def fig08_sintetico_geometria_real() -> Path:
    """Verdad vs ePIE 0.3 vs centro supuesto errado medio LED, dos objetos.

    Cada fila tiene su propia escala de fase (la comparación que importa es
    dentro de la fila): lena/mapa a ±3σ de su fase verdadera (~±0.55 rad),
    objeto disperso a ±π. El panel de centro nominal de lena/mapa satura con
    esa escala y lleva el rótulo que lo dice.
    """
    cols = [
        ("truth", "Fase verdadera del objeto", None),
        ("correct",
         "Reconstruida con el centro correcto\n(paso ePIE 0.3, ruido tipo captura)",
         "offset_noise_g1/assume_correct/epie0.3/it100"),
        ("nominal",
         "Reconstruida con el centro nominal\n(error de ~½ LED, los mismos datos)",
         "offset_noise_g1/assume_nominal/epie0.3/it100"),
    ]
    variants = [("lenamap", "Objeto lena / mapa"),
                ("scatter", "Objeto disperso\n(DF/BF 0.050, como el real)")]

    fig = plt.figure(figsize=(13.4, 9.4))
    gs = fig.add_gridspec(2, 4, width_ratios=[1, 1, 1, 0.045],
                          wspace=0.08, hspace=0.32)
    panels = np.load(_need(FIG08_PANELS, REGEN_FIG08))
    vlim_row = []
    for i, (variant, row_label) in enumerate(variants):
        runs = _synth_runs(variant)
        truth = panels[f"{variant}__truth"]
        # Escala de la fila: ±3σ de la fase verdadera, acotada a ±π (y si
        # queda cerca de ±π, se usa ±π para poder rotular en múltiplos de π).
        vlim = min(3.0 * float(truth.std()), np.pi)
        if vlim > 0.9 * np.pi:
            vlim = np.pi
        vlim_row.append(vlim)
        im = None
        for j, (key, title, run_key) in enumerate(cols):
            ax = fig.add_subplot(gs[i, j])
            ph = panels[f"{variant}__{key}"]
            im = ax.imshow(ph, cmap=fs.PHASE_CMAP, vmin=-vlim, vmax=vlim)
            _bare(ax)
            if run_key is None:
                note = f"std {ph.std():.2f} rad"
            else:
                r = runs[run_key]
                note = (f"corr. fase {_sign(r['phase_correlation'])} · "
                        f"residuo {r['residual_final']['all']:.3f} · "
                        f"std {r['phase_std_recon_rad']:.2f} rad")
            if np.percentile(np.abs(ph), 98) > 1.5 * vlim:
                note += "\nescala saturada: la excursión real llega a ±π"
            _panel_note(ax, note)
            if i == 0:
                ax.set_title(title, fontsize=11, color=fs.INK)
            if j == 0:
                ax.text(-0.04, 0.5, row_label, transform=ax.transAxes,
                        rotation=90, ha="right", va="center", color=fs.INK,
                        fontsize=11, fontweight="bold")

        cax = fig.add_subplot(gs[i, 3])
        if abs(vlim - np.pi) < 1e-6:
            _phase_colorbar(fig, im, cax)
        else:
            cb = fig.colorbar(im, cax=cax,
                              ticks=[-vlim, -vlim / 2, 0, vlim / 2, vlim])
            cb.ax.set_yticklabels([f"{t:+.2f}".replace("-", "−")
                                   for t in (-vlim, -vlim / 2)] +
                                  ["0"] + [f"+{t:.2f}" for t in (vlim / 2, vlim)])
            cb.set_label("fase (rad)", color=fs.INK_2)
            cb.outline.set_visible(False)

    fig.suptitle("Con la geometría real el solver corregido recupera la fase, "
                 "y medio LED de error la destruye", x=0.015, y=0.98, ha="left",
                 fontsize=14, fontweight="bold", color=fs.INK)
    fig.subplots_adjust(top=0.87, bottom=0.05, left=0.05, right=0.93)
    fs.caption(fig, "Sintético con la geometría de la captura real (2x/NA 0.10, "
                    "z=76 mm, 9x9, verde, crop 128, factor 5, píxel HR 0.32 µm) y ruido "
                    "tipo captura (g=1); 100 iteraciones, campo de 205 µm de lado. Los datos "
                    "se generan con el centro (17.45, 14.65) y se reconstruyen con ese centro "
                    "o con el nominal (17, 15). Cada fila tiene su propia escala de fase, "
                    f"ajustada a ±3σ de su fase verdadera (arriba ±{vlim_row[0]:.2f} rad, "
                    f"abajo ±π): lo que se compara es cada fila consigo misma. Con la escala "
                    "de arriba sólo satura el panel de centro nominal, cuya excursión real "
                    "llega a ±π, y por eso lleva ese rótulo. En el objeto disperso la "
                    "correlación de fase "
                    "satura en ~0.69 por el envolvimiento; la cifra limpia es la de lena/mapa "
                    "(roadmap 6.10.1).")
    return fs.save(fig, "fig08_sintetico_geometria_real")


# --------------------------------------------------------------------------
# fig09: datos reales, congelada vs descongelada
# --------------------------------------------------------------------------

def fig09_reales_congelada_descongelada() -> Path:
    """Captura LR, reconstrucción congelada y descongelada (amplitud y fase)."""
    lr = np.asarray(Image.open(_need(LR_DIR / "fila17_col15.tiff",
                                     "la captura cruda del laboratorio")), float)
    frozen = np.load(_need(FIG09_FROZEN, REGEN_FROZEN))
    thawed = np.load(_need(FIG09_THAWED, REGEN_THAWED))

    n_lr = 128                                  # mismo campo en los 4 paneles
    y0 = (lr.shape[0] - n_lr) // 2              # 204.8 µm de lado
    lr_c = lr[y0:y0 + n_lr, y0:y0 + n_lr]       # los .npz ya vienen recortados

    floor = json.loads((FLOOR / "SUMMARY.json").read_text())
    base = floor["base_100it"]
    frozen_std = json.loads((RESULTS / "led_geometry_2025-12-12"
                             / "variants_summary.json").read_text())
    frozen_std = next(v["phase_std_rad"] for v in frozen_std["variants"]
                      if v["variant"] == "ctl_norm_scaled_20")
    thawed_std = floor["runs_iteration_meanres_phasestd_rms"]["step0.3"][-1][2]

    panels = [
        (np.sqrt(np.clip(lr_c, 0, None)), LR_PX_UM, fs.AMP_CMAP,
         "Captura LR, LED central",
         "amplitud medida: la muestra se distingue"),
        (frozen["amplitude"], LR_PX_UM / FACTOR, fs.AMP_CMAP,
         "Congelada: paso por defecto",
         f"≈ la estimación inicial · fase std {frozen_std:.2f} rad"),
        (thawed["amplitude"], LR_PX_UM / FACTOR, fs.AMP_CMAP,
         "Descongelada: amplitud",
         f"moteado de ~2 µm, sin elefante · residuo {base['mean']:.3f}"),
        (thawed["phase"], LR_PX_UM / FACTOR, fs.PHASE_CMAP,
         "Descongelada: fase",
         f"tipo ruido, std {thawed_std:.2f} rad (uniforme: 1.81)"),
    ]

    fig = plt.figure(figsize=(15.2, 4.8))
    gs = fig.add_gridspec(1, 5, width_ratios=[1, 1, 1, 1, 0.035], wspace=0.07)
    cax = fig.add_subplot(gs[0, 4])
    phase_im = None
    for k, (img, px, cmap, title, note) in enumerate(panels):
        ax = fig.add_subplot(gs[0, k])
        if cmap is fs.PHASE_CMAP:
            phase_im = ax.imshow(img, cmap=cmap, vmin=-np.pi, vmax=np.pi)
        else:
            lo, hi = np.percentile(img, [1, 99])
            ax.imshow(img, cmap=cmap, vmin=lo, vmax=hi)
        _bare(ax)
        _scalebar(ax, img.shape[0], px)
        ax.set_title(title, fontsize=11, color=fs.INK)
        _panel_note(ax, note)

    _phase_colorbar(fig, phase_im, cax)
    fig.suptitle("En los datos reales descongelar el solver no revela la "
                 "muestra: moteado y fase tipo ruido", x=0.015, y=0.99,
                 ha="left", fontsize=14, fontweight="bold", color=fs.INK)
    fig.subplots_adjust(top=0.79, bottom=0.08, left=0.02, right=0.95)
    fs.caption(fig, "Verde 2025-12-12, crop 400, 2x/NA 0.10, z=76 mm, centro "
                    "(17.45, 14.65), exposición normalizada. Mismo recorte espacial "
                    "(204.8 µm de lado) en los cuatro paneles: 128 px LR de 1.6 µm y "
                    "640 px HR de 0.32 µm. Congelada = 20 it con el paso por defecto; "
                    "descongelada = 100 it con paso 0.3·lr_n_px. Amplitud en gris "
                    "(estirada 1–99%), fase en mapa cíclico (roadmap 6.9–6.10).")
    return fs.save(fig, "fig09_reales_congelada_descongelada")


# --------------------------------------------------------------------------
# fig10: residuo por LED, medido vs predicho por ruido
# --------------------------------------------------------------------------

def _per_led_tables() -> tuple[dict, dict]:
    meas = json.loads((FLOOR / "step0.3" / "summary.json").read_text())["per_led_final"]
    noise = json.loads((FLOOR / "noise_prediction.json").read_text())["per_led"]
    noise = {k: v["noise_rel_resid_with_fpn"] for k, v in noise.items()}
    return meas, {k: v for k, v in noise.items() if k in meas}


def _led_map(table: dict) -> np.ndarray:
    m = np.full((9, 9), np.nan)
    for i, r in enumerate(ROWS):
        for j, c in enumerate(COLS):
            v = table.get(f"{r},{c}")
            if v is not None:
                m[i, j] = v
    return m


def fig10_residuo_por_led() -> Path:
    """Residuo por LED medido contra el que predice el ruido medido."""
    meas, noise = _per_led_tables()
    vmax = max(meas.values())
    maps = [(_led_map(meas), "Medido (100 it, paso ePIE 0.3)"),
            (_led_map(noise), "Predicho por el ruido medido")]

    fig = plt.figure(figsize=(15.0, 5.2))
    gs = fig.add_gridspec(1, 4, width_ratios=[1, 1, 0.04, 1.5], wspace=0.55)
    axes = [fig.add_subplot(gs[0, i]) for i in range(2)]
    im = None
    for ax, (m, title) in zip(axes, maps):
        im = ax.imshow(m, cmap=SEQ, vmin=0, vmax=vmax,
                       extent=(10.5, 19.5, 21.5, 12.5))
        ax.set_xticks(list(COLS))
        ax.set_yticks(list(ROWS))
        ax.tick_params(labelsize=8)
        ax.grid(False)
        ax.set_title(f"{title}\nmediana {np.nanmedian(m):.3f}", fontsize=11)
        ax.set_xlabel("columna de LED")
        if ax is axes[0]:
            ax.set_ylabel("fila de LED")
    cb = fig.colorbar(im, cax=fig.add_subplot(gs[0, 2]))
    cb.ax.yaxis.set_ticks_position("left")
    cb.ax.yaxis.set_label_position("left")
    cb.set_label("residuo relativo por LED", color=fs.INK_2)
    cb.outline.set_visible(False)

    ax = fig.add_subplot(gs[0, 3])
    order = sorted(meas, key=lambda k: meas[k])
    x = np.arange(len(order))
    ym = [meas[k] for k in order]
    yn = [noise[k] for k in order]
    ax.plot(x, ym, ls="none", marker="o", markersize=5, color=fs.C_OK,
            label="medido")
    ax.plot(x, yn, ls="none", marker="o", markersize=5, color=fs.C_BAD,
            label="predicho por el ruido medido")
    fs.direct_label(ax, x[-1], ym[-1], f"{ym[-1]:.2f}", dx=8, dy=-2)
    fs.direct_label(ax, x[-1], yn[-1], f"{yn[-1]:.3f}", dx=8, dy=-2)
    xm = len(x) * 0.45
    ax.annotate("", xy=(xm, np.median(ym)), xytext=(xm, np.median(yn)),
                arrowprops=dict(arrowstyle="<->", color=fs.INK_2, lw=1.4))
    ax.text(xm + 2, (np.median(ym) + np.median(yn)) / 2,
            f"×{base_ratio():.0f} en la mediana", color=fs.INK, fontsize=11,
            ha="left", va="center")
    ax.set_ylim(0, vmax * 1.10)
    ax.set_xlim(-3, len(x) + 11)
    ax.set_xlabel("LEDs ordenados por residuo medido (80 de 81)")
    ax.set_ylabel("residuo relativo por LED")
    ax.set_title("Ningún LED se acerca al piso de ruido", fontsize=12)
    ax.legend(loc="center left", bbox_to_anchor=(0.02, 0.42))

    fig.suptitle("El residuo real está ~10 veces por encima del ruido en todos "
                 "los LEDs", x=0.015, y=0.99, ha="left", fontsize=14,
                 fontweight="bold", color=fs.INK)
    fig.subplots_adjust(top=0.78, bottom=0.13, left=0.05, right=0.98)
    fs.caption(fig, "Verde 2025-12-12, crop 400, 2x/NA 0.10, z=76 mm, centro "
                    "(17.45, 14.65). Predicción de ruido medida sobre pares frame_1/frame_2 "
                    "(ganancia 0.30 ADU/e⁻, varianza de lectura 7.2 ADU²) más patrón fijo; "
                    "sin patrón fijo baja a 0.020. Los dos mapas comparten la escala de "
                    "color; la celda en blanco es el LED (13, 17), descartado por el "
                    "laboratorio (roadmap 6.10.2).")
    return fs.save(fig, "fig10_residuo_por_led")


def base_ratio() -> float:
    return json.loads((FLOOR / "SUMMARY.json").read_text())["base_100it"]["resid_over_noise_median"]


# --------------------------------------------------------------------------
# fig11: paisaje de geometría (fork K)
# --------------------------------------------------------------------------

def fig11_paisaje_geometria() -> Path:
    """Residuo vs offset de centro, rotación y z, contra el control aleatorio."""
    off = json.loads((GEOM / "offset_grid.json").read_text())["rows"]
    rotz = json.loads((GEOM / "rot_z_grid.json").read_text())["rows"]
    ctrl = json.loads((GEOM / "controls.json").read_text())
    scr = [c["res_all"] for c in ctrl["scrambled"]]

    drs = sorted({r["dr"] for r in off})
    dcs = sorted({r["dc"] for r in off})
    m = np.full((len(drs), len(dcs)), np.nan)
    for r in off:
        m[drs.index(r["dr"]), dcs.index(r["dc"])] = r["res_all"]
    vmin, vmax = 0.24, max(scr) + 0.01

    fig = plt.figure(figsize=(14.8, 5.2))
    gs = fig.add_gridspec(1, 4, width_ratios=[1.1, 0.04, 1, 1], wspace=0.46)

    ax = fig.add_subplot(gs[0, 0])
    step = drs[1] - drs[0]
    im = ax.imshow(m, cmap=SEQ, vmin=vmin, vmax=vmax, origin="lower",
                   extent=(dcs[0] - step / 2, dcs[-1] + step / 2,
                           drs[0] - step / 2, drs[-1] + step / 2))
    ax.grid(False)
    ax.plot(-0.35, 0.45, marker="*", markersize=16, color=fs.SURFACE,
            markeredgecolor=fs.INK, markeredgewidth=1.2, ls="none")
    ax.annotate("centro estimado\npor radiancia", (-0.35, 0.45),
                xytext=(8, 8), textcoords="offset points", color=fs.INK,
                fontsize=9)
    ax.set_xlabel("offset de columna (pasos de LED)")
    ax.set_ylabel("offset de fila (pasos de LED)")
    ax.set_title(f"Offset del centro: plano\n{m.min():.3f}–{m.max():.3f} "
                 f"en 169 puntos", fontsize=12)
    cb = fig.colorbar(im, cax=fig.add_subplot(gs[0, 1]))
    cb.ax.yaxis.set_ticks_position("left")
    cb.ax.yaxis.set_label_position("left")
    cb.set_label("residuo medio por LED", color=fs.INK_2)
    cb.outline.set_visible(False)
    for v in scr:
        cb.ax.axhline(v, color=fs.STATUS["critical"], lw=2)

    ax2 = fig.add_subplot(gs[0, 2])
    zs = sorted({r["z_mm"] for r in rotz})
    thetas = sorted({r["theta_deg"] for r in rotz})
    lut = {(r["theta_deg"], r["z_mm"]): r["res_all"] for r in rotz}
    for i, z in enumerate(zs):
        ax2.plot(thetas, [lut[(t, z)] for t in thetas], marker="o",
                 markersize=6, color=fs.SEQ_BLUE[i + 2], label=f"z = {z:.0f} mm")
    ax2.set_xticks(thetas)
    ax2.set_xlabel("rotación de la matriz de LEDs (grados)")
    ax2.set_ylabel("residuo medio por LED")
    ax2.set_title("Rotación: plano a cualquier z", fontsize=12)
    ax2.legend(loc="upper left", ncol=2, fontsize=9,
               bbox_to_anchor=(0.0, 0.72))

    ax3 = fig.add_subplot(gs[0, 3])
    lut_z = {r["z_mm"]: r["res_all"] for r in rotz if r["theta_deg"] == 0}
    lut_z.update({r["z_mm"]: r["res_all"] for r in ctrl["z_extended"]})
    z_all = sorted(lut_z)
    ax3.plot(z_all, [lut_z[z] for z in z_all], marker="o", markersize=6,
             color=fs.C_OK)
    ax3.axvline(76, color=fs.NOISE_REF, lw=1.2, ls="--")
    ax3.text(78, vmin + 0.005, "z medido\n76 mm", ha="left", va="bottom",
             color=fs.INK_2, fontsize=9)
    ax3.set_xlabel("distancia LED–muestra z (mm)")
    ax3.set_ylabel("residuo medio por LED")
    ax3.set_title("z: pendiente suave, sin mínimo", fontsize=12)

    for a in (ax2, ax3):
        a.axhspan(min(scr), max(scr), color=fs.STATUS["critical"], alpha=0.18,
                  lw=0)
        a.text(0.98, np.mean(scr), "control: LEDs asignados al azar",
               transform=a.get_yaxis_transform(), ha="right", va="center",
               color=fs.INK, fontsize=9)
        a.set_ylim(vmin, vmax)

    fig.suptitle("Los datos reales no distinguen la geometría: sólo el control "
                 "aleatorio se separa", x=0.015, y=0.99, ha="left", fontsize=14,
                 fontweight="bold", color=fs.INK)
    fig.subplots_adjust(top=0.76, bottom=0.14, left=0.05, right=0.99)
    fs.caption(fig, "Verde 2025-12-12, crop central 96, 2x/NA 0.10, factor 5, "
                    "paso ePIE 0.3, 35 iteraciones por punto; offsets relativos al centro "
                    "nominal (17, 15). Los tres paneles comparten la escala de residuo "
                    "0.24–0.42, y las líneas rojas de la barra de color marcan el control "
                    "aleatorio. En sintético (fig08) medio LED de error lleva el residuo de "
                    "0.035 a 0.22; acá ±1.5 LED lo cambian 0.006. La pendiente en z no es un "
                    "mínimo: la validación cruzada se mueve al revés (fig12, roadmap 6.10.3).")
    return fs.save(fig, "fig11_paisaje_geometria")


# --------------------------------------------------------------------------
# fig12: sobreajuste (LEDs usados vs excluidos)
# --------------------------------------------------------------------------

def fig12_sobreajuste_leds_excluidos() -> Path:
    """Residuo de entrenamiento vs LEDs excluidos, por familia de geometría."""
    rows = json.loads((GEOM / "heldout_cv.json").read_text())["rows"]
    by_tag = {}
    for r in rows:
        by_tag.setdefault(r["tag"], []).append(r)
    nominal = [r for r in by_tag["off"] if r["dr"] == 0 and r["dc"] == 0]

    groups = [
        ("Centro nominal (17, 15)", nominal),
        ("Centro estimado por radiancia", by_tag["F_center"]),
        ("Offsets de centro ±1 LED\n(25 puntos)", by_tag["off"]),
        ("Rotación ±5°\n(4 puntos)", by_tag["rot"]),
        ("z de 40 a 120 mm\n(7 puntos)", by_tag["z"]),
        ("Control: LEDs asignados\nal azar (3 semillas)",
         by_tag["scr0"] + by_tag["scr1"] + by_tag["scr2"]),
    ]
    y = np.arange(len(groups))[::-1]

    fig, ax = plt.subplots(figsize=(11.5, 5.6))
    for yi, (_, rs) in zip(y, groups):
        tr = [r["train_res"] for r in rs]
        ho = [r["heldout_res"] for r in rs]
        ax.plot([np.mean(tr), np.mean(ho)], [yi, yi], color=fs.GRID, lw=2,
                zorder=1)
        for vals, color, label in ((tr, fs.C_OK, "LEDs usados (entrenamiento)"),
                                   (ho, fs.C_BAD, "LEDs excluidos (20 de 81)")):
            if len(vals) > 1:
                ax.plot([min(vals), max(vals)], [yi, yi], color=color, lw=6,
                        alpha=0.35, solid_capstyle="butt", zorder=2)
            ax.plot(np.mean(vals), yi, marker="o", markersize=9, color=color,
                    ls="none", zorder=3,
                    label=label if yi == y[0] else None)
        ax.text(np.mean(tr), yi + 0.28, f"{np.mean(tr):.2f}", ha="center",
                va="bottom", color=fs.INK, fontsize=10)
        ax.text(np.mean(ho), yi + 0.28, f"{np.mean(ho):.2f}", ha="center",
                va="bottom", color=fs.INK, fontsize=10)

    ax.set_yticks(y, [g for g, _ in groups])
    ax.set_ylim(-0.6, len(groups) - 0.25)
    ax.set_xlim(0.18, 1.08)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("residuo relativo medio por LED")
    ax.set_title("La reconstrucción no generaliza: 0.29 en los LEDs usados, "
                 "0.50 en los excluidos")
    ax.legend(loc="upper right", bbox_to_anchor=(1.0, 0.98))
    fs.caption(fig, "Validación cruzada dejando 20 de los 81 LEDs afuera: se "
                    "reconstruye sin ellos y se mide el residuo sobre esos 20 (verde "
                    "2025-12-12, crop 96, "
                    "2x/NA 0.10, paso ePIE 0.3, 35 iteraciones). Punto = media del grupo; "
                    "barra = rango. Ninguna geometría razonable baja el residuo de los LEDs "
                    "excluidos (roadmap 6.10.3).")
    return fs.save(fig, "fig12_sobreajuste_leds_excluidos")


FIGURES = {
    "fig08_sintetico_geometria_real": fig08_sintetico_geometria_real,
    "fig09_reales_congelada_descongelada": fig09_reales_congelada_descongelada,
    "fig10_residuo_por_led": fig10_residuo_por_led,
    "fig11_paisaje_geometria": fig11_paisaje_geometria,
    "fig12_sobreajuste_leds_excluidos": fig12_sobreajuste_leds_excluidos,
}
