"""Figures about the synthetic experiments (milestones 16-21 and roadmap 6.9).

All sources are tracked JSON under data/, except fig05, which reads
results/led_geometry_2025-12-12/synthetic_step_size_control.json (results/ is
NOT tracked; that figure needs the local directory).

Caveat applied throughout: WF's effective step is `step_max=20 / lr_n_px`, i.e.
20/crop**2 of the classic ePIE unit step (roadmap 6.9). At crop 32 that is
~0.02 -> the WF column of the crop-32 sweeps (milestones 16-19) is a frozen
solver and is either excluded or drawn in muted ink with an explicit note; it
is never compared against GD as if it were "algorithm vs algorithm" (audit A2).
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

import figstyle as fs

DATA = fs.REPO / "data"
RESULTS = fs.REPO / "results"
PI = np.pi

# Local style additions (not in figstyle, kept here on purpose):
FROZEN = fs.INK_MUTED          # series that do not measure the algorithm
BAND = fs.GRID                 # "here the reading is not valid" bands


def _load(name: str, base: Path = DATA) -> list[dict]:
    return json.loads((base / f"{name}.json").read_text())


def _ms(rows: list[dict], field: str) -> tuple[float, float]:
    """mean, population sd over seeds."""
    v = [r[field] for r in rows]
    return float(np.mean(v)), float(np.std(v))


def _group(rows: list[dict], key) -> dict:
    out: dict = {}
    for r in rows:
        out.setdefault(key(r), []).append(r)
    return out


def _curve(groups: dict, keys, field):
    m = np.array([_ms(groups[k], field)[0] for k in keys])
    s = np.array([_ms(groups[k], field)[1] for k in keys])
    return m, s


def _zero_line(ax):
    ax.axhline(0, color=fs.INK_MUTED, lw=1.0, zorder=0)


# ---------------------------------------------------------------- fig01

def fig01_contraste_amplitud() -> Path:
    """Phase correlation vs amplitude contrast + the pure-phase init diagnosis.

    data/amplitude_contrast_sweep.json (milestone 19, 20 jobs, GD-amplitude and
    WF, lena_map, green, phase 0.3pi, crop 32, 2 seeds) and
    data/init_diagnosis_pure_phase.json (milestone 21, 32 jobs, 4 seeds).
    """
    rows = _load("amplitude_contrast_sweep")
    g = _group(rows, lambda r: (round(100 * (1 - r["min_amp"])), r["peak"]))
    contrasts = [0, 2, 5, 10, 20]
    x = np.arange(len(contrasts))

    fig = plt.figure(figsize=(13.2, 5.2))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.45, 1], wspace=0.28)
    ax = fig.add_subplot(gs[0, 0])

    m, s = _curve(g, [(c, 1000.0) for c in contrasts], "gd_phase")
    ax.errorbar(x, m, yerr=s, color=fs.C_OK, marker="o", capsize=3,
                elinewidth=1.2, label="GD-amplitud, pico 1000")
    fs.direct_label(ax, x[-1], m[-1], "GD, pico 1000", dx=-6, dy=14, ha="right")

    m, s = _curve(g, [(c, 100.0) for c in contrasts], "gd_phase")
    ax.errorbar(x, m, yerr=s, color=fs.C_BAD, marker="o", capsize=3,
                elinewidth=1.2, label="GD-amplitud, pico 100")
    fs.direct_label(ax, x[0], m[0], "GD, pico 100", dx=8, dy=14, ha="left")

    m_wf, _ = _curve(g, [(c, 1000.0) for c in contrasts], "wf_phase")
    ax.plot(x, m_wf, color=FROZEN, marker="s", ls="--",
            label="WF, pico 1000 (congelado)")
    fs.direct_label(ax, x[-1], m_wf[-1], "WF (congelado)", dx=-6, dy=14, ha="right")

    _zero_line(ax)
    ax.annotate("fase pura (0 %): GD colapsa\npor debajo de cero",
                (0, g[(0, 1000.0)][0]["gd_phase"]), xytext=(20, -38),
                textcoords="offset points", color=fs.INK, fontsize=10,
                arrowprops=dict(arrowstyle="-", color=fs.INK_2, lw=1))
    ax.set_xticks(x, [f"{c} %" for c in contrasts])
    ax.set_xlim(-0.35, len(contrasts) - 0.55)
    ax.set_ylim(-0.48, 0.92)
    ax.set_xlabel("contraste de amplitud del objeto, 1 − mín|o| (%)")
    ax.set_ylabel("correlación de fase con la verdad")
    ax.set_title("Con 5–10 % de contraste de amplitud la fase se recupera;\n"
                 "con fase pura el solver colapsa")
    ax.legend(loc="lower right")

    # Panel 2: initialisation diagnosis at exactly 0 % contrast.
    ini = _load("init_diagnosis_pure_phase")
    gi = _group(ini, lambda r: (r["init"], r["peak"]))
    labels = [("default", "arranque por defecto\n(imagen del LED central)"),
              ("oracle_amp_zero_phase", "oráculo de amplitud\n(|o| = 1, fase 0)"),
              ("random_phase", "fase aleatoria\n(σ = 0.3 rad)"),
              ("oracle_full", "oráculo completo\n(el objeto verdadero)")]
    ax2 = fig.add_subplot(gs[0, 1])
    y = np.arange(len(labels))[::-1]
    for off, peak, color, lab in [(+0.19, 1000.0, fs.C_OK, "pico 1000 fotones"),
                                  (-0.19, 100.0, fs.C_BAD, "pico 100 fotones")]:
        m = [_ms(gi[(k, peak)], "phase_corr")[0] for k, _ in labels]
        s = [_ms(gi[(k, peak)], "phase_corr")[1] for k, _ in labels]
        ax2.barh(y + off, m, height=0.34, color=color, label=lab,
                 xerr=s, error_kw=dict(ecolor=fs.INK_2, elinewidth=1.2, capsize=3))
        for yi, v, e in zip(y + off, m, s):
            d = e + 0.05
            ax2.text(v + (d if v >= 0 else -d), yi, f"{v:+.2f}",
                     va="center", ha="left" if v >= 0 else "right",
                     color=fs.INK, fontsize=9)
    ax2.axvline(0, color=fs.INK_MUTED, lw=1.0)
    ax2.set_yticks(y, [t for _, t in labels], fontsize=9)
    ax2.set_xlim(-0.85, 1.45)
    ax2.set_ylim(-0.6, len(labels) - 0.25)
    ax2.grid(axis="y", visible=False)
    ax2.set_xlabel("correlación de fase (contraste 0 %, 4 semillas)")
    ax2.set_title("Arrancar en la verdad sí converge:\nel problema es la cuenca, no el óptimo",
                  fontsize=12)
    ax2.legend(loc="upper right", bbox_to_anchor=(1.0, 0.62))

    fs.caption(fig, "Izq.: barrido de contraste (hito 19; lena_map, verde, fase 0.3π, "
                    "recorte 32 px, 9×9 LEDs, 2 semillas; barras = desvío entre semillas). "
                    "La serie WF se dibuja en gris porque a recorte 32 su paso efectivo es "
                    "~0.02 del paso ePIE (roadmap 6.9): mide el solver congelado, no el "
                    "algoritmo. Der.: hito 21, mismo caso de fase pura, variando solo la "
                    "inicialización de GD-amplitud (4 semillas).")
    return fs.save(fig, "fig01_contraste_amplitud")


# ---------------------------------------------------------------- fig02

def fig02_cadena_acoplada() -> Path:
    """Coupled vs naive thickness recovery (WF), with and without the mask.

    data/coupled_opl_ceiling_sweep_masked.json (milestone 20, 48 jobs, crop 16,
    9x9, peak 1000, 4 seeds). Only the WF rows are read as a result; the GD rows
    appear in the second panel as a diagnosis of its wrap numbers, never as a
    quality comparison against WF.
    """
    rows = _load("coupled_opl_ceiling_sweep_masked")
    wf = _group([r for r in rows if r["solver"] == "wirtinger"], lambda r: r["t_scale"])
    gd = _group([r for r in rows if r["solver"] == "gd-amplitude"], lambda r: r["t_scale"])
    scales = sorted(wf)
    blue = [wf[s][0]["max_phase_blue_pi"] for s in scales]
    xt = [f"{s}\n{b:.2f}π" for s, b in zip(scales, blue)]
    x = np.arange(len(scales))

    fig = plt.figure(figsize=(13.6, 5.4))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.55, 1], wspace=0.3)
    ax = fig.add_subplot(gs[0, 0])
    ax.axvspan(2.5, len(scales) - 0.5, color=BAND, alpha=0.6, lw=0, zorder=0)
    ax.text(4.0, 0.88, "acá enmascarar descarta el 67–93 %\n"
                       "de la imagen: el desenvolvimiento\nhace falta de verdad",
            ha="center", va="top", color=fs.INK_2, fontsize=9)

    for field, color, label, lab_short, dy in [
            ("corr_coupled_masked", fs.C_OK, "acoplada + máscara de píxeles con k espurio",
             "acoplada + máscara", 24),
            ("corr_naive", fs.C_THIRD, "ingenua (cada canal por separado)", "ingenua", -15),
            ("corr_coupled", fs.C_BAD, "acoplada (cadena 2b.i+2b.ii tal cual)", "acoplada", 13)]:
        m, s = _curve(wf, scales, field)
        ax.errorbar(x, m, yerr=s, color=color, marker="o", capsize=3,
                    elinewidth=1.2, label=label)
        fs.direct_label(ax, x[0], m[0], lab_short, dx=8, dy=dy)
    _zero_line(ax)
    ax.set_xticks(x, xt)
    ax.set_xlim(-0.35, len(scales) - 0.35)
    ax.set_ylim(-1.2, 1.15)
    ax.set_xlabel("escala del espesor  (arriba) y fase máxima del canal azul (abajo)")
    ax.set_ylabel("correlación con el espesor verdadero")
    ax.set_title("Filtrar los píxeles con envolvimiento espurio vuelve útil la\n"
                 "cadena acoplada (WF): 0.93 contra 0.66 de la ingenua")
    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 0.02))

    ax2 = fig.add_subplot(gs[0, 1])
    for grp, color, label in [(wf, fs.C_OK, "WF (Wirtinger flow)"),
                              (gd, fs.SERIES[6], "GD-amplitud")]:
        m, _ = _curve(grp, scales, "frac_masked_out")
        ax2.plot(x, 100 * m, color=color, marker="o", label=label)
        fs.direct_label(ax2, x[0], 100 * m[0], label.split(" (")[0],
                        dx=6, dy=10 if grp is wf else -14)
    ax2.set_xticks(x, [str(s) for s in scales])
    ax2.set_ylim(-4, 108)
    ax2.set_xlabel("escala del espesor")
    ax2.set_ylabel("píxeles con k ≠ 0, enmascarados (%)")
    ax2.set_title("En GD casi toda la imagen recibe\nun k espurio", fontsize=12)
    ax2.legend(loc="lower right")

    fs.caption(fig, "Hito 20: crop 16, 9×9 LEDs, pico 1000, 4 semillas (barras = desvío). "
                    "La máscara descarta los píxeles con número de envolvimiento k ≠ 0. "
                    "El refinamiento TV no interviene (da resultados idénticos bit a bit). "
                    "GD-amplitud aparece solo en el panel derecho, como diagnóstico de su "
                    "ruido de fase: su calidad no es comparable con la de WF acá (objeto y "
                    "recorte elegidos por el test de WF, y WF sin afinar, auditoría A2).")
    return fs.save(fig, "fig02_cadena_acoplada")


# ---------------------------------------------------------------- fig03

def fig03_error_posicion_leds() -> Path:
    """LED position error vs recovered phase: nominal grid, rigid calibration, oracle.

    data/plan_p1_led_position_error.json (P1, 22 jobs), plan_p3_* (10 jobs) and
    plan_p1_p3_extra_seeds.json (10 jobs, seeds 2-3 for the 5 ambiguous cells);
    milestone 16. The WF column is excluded: at crop 32 its step is ~0.02 of the
    ePIE unit step (roadmap 6.9) and it sits at 0.02-0.05 everywhere.
    """
    p1 = _load("plan_p1_led_position_error")
    p3 = _load("plan_p3_led_position_error")
    extra = _load("plan_p1_p3_extra_seeds")
    p1 += [r for r in extra if r["exp"] == "P1"]
    p3 += [r for r in extra if r["exp"] == "P3"]

    g1 = _group(p1, lambda r: r["err"])
    order = ["none", "jitter0.05", "pitch+1%", "jitter0.2", "rot1deg", "z+2mm",
             "offset0.5", "rot3deg", "combined", "z+7mm", "offset2"]
    names = {"none": "ninguno", "jitter0.05": "jitter 0.05 mm", "pitch+1%": "pitch +1 %",
             "jitter0.2": "jitter 0.2 mm", "rot1deg": "rotación 1°", "z+2mm": "z +2 mm",
             "offset0.5": "offset 0.5 mm", "rot3deg": "rotación 3°",
             "combined": "combinado", "z+7mm": "z +7 mm", "offset2": "offset 2 mm"}
    kerr = [_ms(g1[k], "k_err_bins")[0] for k in order]
    x = np.arange(len(order))

    fig = plt.figure(figsize=(13.8, 5.8))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.75, 1], wspace=0.22,
                          bottom=0.17, top=0.9)
    ax = fig.add_subplot(gs[0, 0])
    lines = [("gd_true_phase", fs.C_THIRD, "posiciones verdaderas (oráculo)", "oráculo", 13),
             ("gd_rigid_phase", fs.C_OK, "grilla nominal + calibración rígida", "rígido", -21),
             ("gd_nominal_phase", fs.C_BAD, "grilla nominal (lo que se hace hoy)", "nominal", 13)]
    for field, color, label, short, dy in lines:
        m, s = _curve(g1, order, field)
        ax.errorbar(x, m, yerr=s, color=color, marker="o", capsize=3,
                    elinewidth=1.2, label=label)
        fs.direct_label(ax, x[9], m[9], short, dx=-9, dy=dy, ha="right")  # z +7 mm
    _zero_line(ax)
    # staggered two-row tick labels: 11 categories do not fit on one row
    ticks = [f"{names[k]}\n({e:.2f})" if i % 2 == 0 else f"\n\n{names[k]}\n({e:.2f})"
             for i, (k, e) in enumerate(zip(order, kerr))]
    ax.set_xticks(x, ticks, fontsize=8.5)
    ax.set_xlim(-0.5, len(order) - 0.4)
    ax.set_ylim(-0.30, 0.79)
    ax.set_xlabel("error de posición de los LEDs  (entre paréntesis: error de k, en bins)")
    ax.set_ylabel("correlación de fase con la verdad")
    ax.set_title("La posición de los LEDs es el cuello de botella: con las\n"
                 "posiciones verdaderas la fase se recupera siempre")
    ax.legend(loc="lower right")
    ax.text(0.015, 0.985, "WF excluido: a recorte 32 su paso es ~0.02 del paso ePIE\n"
                         "(roadmap 6.9) y da 0.02–0.05 en todas las filas — mide un\n"
                         "solver congelado, no el algoritmo.",
            transform=ax.transAxes, ha="left", va="top", color=fs.INK, fontsize=9,
            bbox=dict(fc=fs.GRID, ec="none", pad=5))

    ax2 = fig.add_subplot(gs[0, 1])
    g3 = _group(p3, lambda r: r["err_scale"])
    sc = sorted(g3)
    kx = [_ms(g3[s], "k_err_bins")[0] for s in sc]
    ax2.axvspan(0.38, 0.76, color=BAND, alpha=0.7, lw=0, zorder=0)
    ax2.text(0.54, 0.60, "acantilado", ha="center", color=fs.INK_2, fontsize=9)
    for field, color, label, short, _dy in lines:
        m, s = _curve(g3, sc, field)
        ax2.errorbar(kx, m, yerr=s, color=color, marker="o", capsize=3,
                     elinewidth=1.2, label=label)
        fs.direct_label(ax2, kx[0], m[0], short, dx=-8, ha="right")
    _zero_line(ax2)
    ax2.set_xscale("log")
    ax2.set_xticks(kx, [f"{v:.2f}" for v in kx])
    ax2.minorticks_off()
    ax2.set_xlim(0.085, 4.2)
    ax2.set_ylim(-0.30, 0.79)
    ax2.set_xlabel("error de k (bins), error «combinado» × {0.1 … 2}")
    ax2.set_ylabel("correlación de fase con la verdad")
    ax2.set_title("El acantilado cae entre 0.4 y 0.8\nbins de error de k", fontsize=12)
    ax2.legend(loc="lower left", fontsize=9)

    fs.caption(fig, "Hito 16: lena_map+green, 9×9 LEDs sobre 48 mm, recorte 32 px, fase máx "
                    "0.3π, pico 1000; GD-amplitud, 2 semillas (4 en jitter 0.2 mm, offset "
                    "0.5 mm, z +2 mm y combinado ×0.25/×0.5); barras = desvío entre semillas. "
                    "No se grafica la variante per-LED: es la única que rescata el jitter "
                    "(0.32 contra 0.16–0.19), pero empata o sobreajusta en el resto. El "
                    "oráculo llega a ~0.5, no a 1, por la fase débil y el ruido de esta celda.")
    return fs.save(fig, "fig03_error_posicion_leds")


# ---------------------------------------------------------------- fig04

def fig04_fase_debil_y_techo() -> Path:
    """Weak phase is not recoverable; above pi the metric stops measuring.

    data/plan_e1_object_phase.json (E1, milestone 17, 36 jobs) and
    data/phase_ceiling_sweep_blue.json (milestone 19, 28 jobs). Both are crop 32,
    so the WF columns are excluded (frozen step, roadmap 6.9).
    """
    e1 = _group([r for r in _load("plan_e1_object_phase") if r["peak"] == 1000.0],
                lambda r: (r["kind"], round(r["phase_max"] / PI, 3)))
    ph = [0.05, 0.1, 0.3]
    objs = [("lena_map", fs.C_OK, "lena + mapa (amplitud y fase)"),
            ("blob", fs.C_BAD, "blob (amplitud y fase)"),
            ("phase_only", fs.C_THIRD, "fase pura (amplitud uniforme)")]

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13.2, 5.2),
                                  gridspec_kw={"wspace": 0.26})
    ax.axvspan(0.04, 0.115, color=BAND, alpha=0.7, lw=0, zorder=0)
    ax.text(0.062, -0.30, "fase débil\n(≤ 0.1π)", ha="center", va="bottom",
            color=fs.INK_2, fontsize=9)
    for kind, color, label in objs:
        m, s = _curve(e1, [(kind, p) for p in ph], "gd_phase")
        ax.errorbar(ph, m, yerr=s, color=color, marker="o", capsize=3,
                    elinewidth=1.2, label=label)
        fs.direct_label(ax, ph[-1], m[-1], label.split(" (")[0])
    ax.axhline(0.5, color=fs.NOISE_REF, lw=1.2, ls="--")
    ax.text(0.044, 0.52, "0.5: mínimo para hablar de recuperación",
            color=fs.INK_2, fontsize=9, va="bottom")
    _zero_line(ax)
    ax.set_xscale("log")
    ax.set_xticks(ph, ["0.05π", "0.1π", "0.3π"])
    ax.minorticks_off()
    ax.set_xlim(0.042, 0.53)
    ax.set_ylim(-0.42, 0.95)
    ax.set_xlabel("fase máxima del objeto (rad, en unidades de π)")
    ax.set_ylabel("correlación de fase con la verdad")
    ax.set_title("Con fase ≤ 0.1π no hay recuperación:\nningún objeto pasa de 0.25")
    ax.legend(loc="upper left", fontsize=9)

    c = _group([r for r in _load("phase_ceiling_sweep_blue") if r["peak"] == 1000.0],
               lambda r: round(r["phase_max"] / PI, 3))
    pk = sorted(c)
    ax2.axvspan(1.0, 3.6, color=BAND, alpha=0.7, lw=0, zorder=0)
    for field, color, label, short in [
            ("gd_phase_rmse", fs.C_OK, "GD-amplitud reconstruido", "GD"),
            ("flat_phase_rmse", fs.NOISE_REF, "referencia «no poner fase»", "sin fase")]:
        m, s = _curve(c, pk, field)
        ax2.errorbar(pk, m, yerr=s, color=color, marker="o", capsize=3,
                     elinewidth=1.2, label=label)
        fs.direct_label(ax2, pk[3], m[3], short, dx=-6, ha="right",
                        dy=-12 if field == "gd_phase_rmse" else 12)
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xticks(pk, [f"{v:g}π" for v in pk])
    ax2.set_yticks([0.1, 0.2, 0.5, 1.0, 2.0], ["0.1", "0.2", "0.5", "1.0", "2.0"])
    ax2.minorticks_off()
    ax2.set_xlim(0.26, 3.9)
    ax2.set_xlabel("fase máxima del objeto (canal azul)")
    ax2.set_ylabel("RMSE de fase (rad)")
    ax2.set_title("Hasta 1π GD mejora la referencia; por encima\nla métrica deja de medir",
                  fontsize=12)
    ax2.text(1.9, 0.14, "fase > π: la métrica envuelve\nla verdad → no comparable",
             ha="center", color=fs.INK, fontsize=9,
             bbox=dict(fc=fs.SURFACE, ec="none", pad=3))
    ax2.legend(loc="upper left")

    fs.caption(fig, "Izq.: hito 17 (E1), verde, recorte 32 px, 9×9, pico 1000, 2 semillas. "
                    "Der.: hito 19, canal azul, lena_map, pico 1000 (sin ruido da lo mismo), "
                    "2 semillas; barras = desvío entre semillas. Se excluyen las columnas WF "
                    "de ambos barridos: a recorte 32 su paso es ~0.02 del paso ePIE (roadmap "
                    "6.9). El caso de fase pura a 0.3π es el colapso de la fig01.")
    return fs.save(fig, "fig04_fase_debil_y_techo")


# ---------------------------------------------------------------- fig05

def fig05_bug_del_paso() -> Path:
    """The step bug: WF's effective step is 20/crop**2 of the ePIE unit step.

    results/led_geometry_2025-12-12/synthetic_step_size_control.json (roadmap
    6.9, control sintético sin ruido, 20 iteraciones, factor 5). results/ is not
    tracked: this figure needs that local directory.
    """
    rows = json.loads((RESULTS / "led_geometry_2025-12-12" /
                       "synthetic_step_size_control.json").read_text())
    g = _group(rows, lambda r: (r["crop"], r["step"]))
    crops = sorted({r["crop"] for r in rows})
    x = np.arange(len(crops))
    steps = [("epie_0.3", fs.C_OK, "paso relativo: 0.3 × ePIE", "0.3 × ePIE"),
             ("default_20", fs.C_BAD, "paso por defecto: step_max = 20", "por defecto")]

    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.0), gridspec_kw={"wspace": 0.24})
    panels = [("rel_improvement", "mejora relativa del residuo",
               "Con el paso por defecto la mejora del residuo\nse desvanece al crecer el recorte"),
              ("phase_correlation", "correlación de fase con la verdad",
               "Con paso relativo al ePIE la fase se recupera\nigual en todos los recortes")]
    for ax, (field, ylab, title) in zip(axes, panels):
        for step, color, label, short in steps:
            y = [g[(c, step)][0][field] for c in crops]
            ax.plot(x, y, color=color, marker="o", label=label)
            if step == "epie_0.3":
                fs.direct_label(ax, x[-1], y[-1], short, dx=-6, dy=13, ha="right")
            else:
                fs.direct_label(ax, x[0], y[0], short, dx=8, dy=13, ha="left")
        ax.set_xticks(x, [f"{c}²\n{20 / c ** 2:.2g} × ePIE" for c in crops], fontsize=9.5)
        ax.set_xlim(-0.25, len(crops) - 0.75)
        ax.set_ylim(-0.07, 1.08)
        ax.set_xlabel("recorte LR (píxeles por lado)  y paso efectivo por defecto")
        ax.set_ylabel(ylab)
        ax.set_title(title)
        ax.legend(loc="center right")

    fs.caption(fig, "Roadmap 6.9: `reconstruct` divide el gradiente por el número de píxeles "
                    "LR, así que a `step_max = 20` fijo el paso efectivo es 20/recorte² del "
                    "paso unitario de ePIE (0.078 a 16 px, 0.0049 a 64, 0.0012 a 128, y "
                    "~1/8000 a los 400 px de los datos reales). Control sintético sin ruido, "
                    "20 iteraciones, factor de superresolución 5, una corrida por celda: "
                    "los hitos sintéticos usan recortes de 16–32 px, donde el defecto todavía "
                    "es una fracción razonable — por eso el bug nunca se vio ahí.")
    return fs.save(fig, "fig05_bug_del_paso")


FIGURES = {
    "fig01_contraste_amplitud": fig01_contraste_amplitud,
    "fig02_cadena_acoplada": fig02_cadena_acoplada,
    "fig03_error_posicion_leds": fig03_error_posicion_leds,
    "fig04_fase_debil_y_techo": fig04_fase_debil_y_techo,
    "fig05_bug_del_paso": fig05_bug_del_paso,
}
