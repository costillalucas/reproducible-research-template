#!/usr/bin/env python3
"""reconstruir.py -- reconstrucción FPM de una captura 15x15 del microscopio, de punta a punta, sin tocar código.

Lo llama ./reconstruir.sh (que encuentra solo la carpeta, los darks y el flat). Se puede usar directo:

    python3 scripts/reconstruir.py <carpeta_muestra> --flat <carpeta_flat> --dark <oscuros_muestra> [--dark-flat <oscuros_flat>]
            [--recorte F,C | --recorte auto] [--tam 400] [--epocas 160] [--guardar-cada 20] [--validar] [--color r]
            [--salida DIR] [--nucleos 3]

Si no se dan --epocas o --guardar-cada y se corre en una terminal, los pregunta. Con --guardar-cada N guarda cada N épocas
una fila de métricas en snapshots/metricas_<tarea>.csv (época, error del solver, R de ajuste o R held-out en las mitades,
tiempo) y una imagen de la amplitud (snapshots/amplitud_<tarea>_eNNN.png). Los objetos de esas épocas
(snapshots/objeto_<tarea>_eNNN.npy, ~11.5 MB cada uno) solo con --guardar-objetos: los necesitan el panel "acuerdo entre
mitades" de ./comparar.sh y ./puntos.sh --epoca N. Los objetos finales (objeto_complejo.npy y mitades) se guardan siempre.

Qué hace (es el pipeline de results/captura_2026-10-21_500/, sin reescribir el solver):
  1. Preprocesado (= prep_500.py generalizado):
     * por LED, la exposición que haya (si hay varias, la más larga sin saturar en el recorte);
     * promedio de frames, DESCARTANDO un frame casi a oscuras (defecto de adquisición del 21/10: el primer frame tras un
       cambio de exposición puede salir a oscuras, p. ej. (15,15) a 128 ms). Regla: señal sobre oscuro del frame < 60 % de la
       del mejor frame (o de la mediana si hay >= 3) y la diferencia > 2 cuentas -> se descarta y se avisa;
     * se resta el oscuro de la MISMA exposición píxel a píxel (si falta, el más cercano, con aviso) y se normaliza por
       t_ef = t - 0.20 ms (muestra y flat por separado, cada uno con su exposición);
     * máscara = saturados (4095, cualquier frame de la muestra) U polvo del sensor (flat del LED (17,15) / suavizado < 0.8,
       dilatado 4 px).
  2. Solver y objetivo de rojo_500 / rojo_centrado (results/captura_2026-10-21_500/r500_red/fpm_red.py, lazo A+init de
     results/iteraciones_2026-09-30/iter_runner.py): BF = S/F·<F>, DF = S - gauss(F, 8); paso 0.3 con rampa.
     Geometría: z 102 mm, lrpx 1.29 µm (aumento 3.2/1.29), NA 0.069·1.25/1.29 = 0.0669, factor 3, LEDs filas 10-24 col 8-22,
     eje sobre el LED (17,15) en el centro del ROI (ROI 1120 en OffsetX 4000 / OffsetY 1942).
  3. Offset del LED según el recorte Y el ROI de la cámara (sistema NO telecéntrico): el eje local se corre 6 mm / 3538 px =
     0.001696 mm por píxel (= 1.315 · 1.29 µm) que el centro del recorte, en coordenadas del SENSOR, se aparta del eje calibrado
     (ROI 4000,1942 de 1120 px -> eje sobre (17,15) en el píxel de sensor x 4560, y 2502):
         offset_y = (2502 - (OffsetY + centro_recorte_filas)) · 0.001696 mm,   offset_x = (4560 - (OffsetX + centro_recorte_col)) · ...
     El ROI de la toma sale de <carpeta>/captura.json (scripts/leer_offset.py; si no está, el proyecto de la cámara = ROI ACTUAL,
     con aviso) o de --offset-roi X,Y. Con el ROI calibrado se reduce a corrimiento del recorte respecto del centro del ROI:
     Recorte de la mañana (filas 310:710, col 360:760) -> y +0.085 mm; recorte .500 (140:540, 560:960) -> y +0.373, x -0.339 mm
     (los INFORME redondean a 0.0017 mm/px: +0.374 / -0.340). C1 es plano en ±0.6 mm, así que el redondeo no importa.
  4. --validar: además reconstruye con cada mitad de los LEDs ((fila+col) par / impar) y mide qué tan bien predice la mitad
     que NO vio (R held-out, anillos < 7, = C1 de los INFORME pero con 2 mitades en vez de 5 folds). Corre en paralelo.

Salida en <salida>/: objeto_complejo.npy (complex64, píxel HR en resumen.txt), reconstruccion.png, resumen.txt, datos/prep.npz.
"""
import argparse
import glob
import json
import os
import re
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "1")
import multiprocessing as mp  # noqa: E402

import numpy as np  # noqa: E402
import tifffile  # noqa: E402
from scipy.ndimage import gaussian_filter, binary_dilation  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
# copias versionadas del solver (originales en results/captura_2026-10-21_500/r500_red/ y results/iteraciones_2026-09-30/)
SOLVER_DIR = os.path.join(REPO, "scripts", "fpm_solver")
ITER_DIR = os.path.join(REPO, "scripts", "fpm_solver")

RANGO = 4095                      # Mono12
T0 = -0.20                        # ms, t_ef = t + T0 (inv/exposicion.json de octubre)
MM_POR_PX = 6.0 / 3538.0          # corrimiento del eje en la matriz por px de ROI (visionpoint 21/10; = 1.315 · 1.29 µm)
LRPX, NA_OBJ, Z_MM = 1.29, 0.069 * 1.25 / 1.29, 102.0
FACTOR = {"red": 3, "green": 5, "blue": 5}
COLOR = {"r": "red", "g": "green", "b": "blue"}
CENTRO_LED = (17, 15)
ROI_CAL = (4000, 1942, 1120)      # ROI calibrado (OffsetX, OffsetY, lado): eje sobre el LED (17,15) en su centro (visionpoint 21/10)
FILAS, COLS = range(10, 25), range(8, 23)
RX_LED = re.compile(r"^fila(\d+)_col(\d+)_color([rgb])$")
RX_T = re.compile(r"^(\d+(?:\.\d+)?)ms$")
DESCARTAR = True                  # --no-descartar lo apaga (solo para comparar con los INFORME, que promediaban todo)
RX_FR = re.compile(r"imagen_frame_(\d+)\.tiff?$")


def msg(s=""):
    print(s, flush=True)


# ---------------------------------------------------------------------------------------------------- lectura
def indexar(carpeta, color):
    """{(fila, col): {t_ms: [frames ordenados]}} para un color."""
    out = {}
    for d in sorted(os.listdir(carpeta)):
        m = RX_LED.match(d)
        if not m or m.group(3) != color:
            continue
        ent = out.setdefault((int(m.group(1)), int(m.group(2))), {})
        for e in os.listdir(os.path.join(carpeta, d)):
            mt = RX_T.match(e)
            if not mt:
                continue
            fs = [f for f in glob.glob(os.path.join(carpeta, d, e, "imagen_frame_*.tif*")) if RX_FR.search(f)]
            if fs:
                ent[float(mt.group(1))] = sorted(fs, key=lambda f: int(RX_FR.search(f).group(1)))
    return {k: v for k, v in out.items() if v}


class Recorte:
    def __init__(self, f0, c0, n):
        self.f0, self.c0, self.n = f0, c0, n
        self.sl = (slice(f0, f0 + n), slice(c0, c0 + n))

    def __str__(self):
        return f"filas {self.f0}:{self.f0 + self.n}, columnas {self.c0}:{self.c0 + self.n}"


def leer_frames(fs, rec=None):
    out = []
    for f in fs:
        a = tifffile.imread(f)
        out.append((a[rec.sl] if rec else a).astype(np.float64))
    return out


class Oscuros:
    """Oscuro medio por exposición (recortado). Lista de carpetas en orden de preferencia; falta t -> el más cercano."""

    def __init__(self, carpetas, rec):
        self.img, self.origen = {}, {}
        for c in carpetas:
            if not c or not os.path.isdir(c):
                continue
            por_t = {}
            for d in sorted(os.listdir(c)):
                if not RX_LED.match(d):
                    continue
                for e in os.listdir(os.path.join(c, d)):
                    mt = RX_T.match(e)
                    if mt:
                        fs = sorted(glob.glob(os.path.join(c, d, e, "imagen_frame_*.tif*")))
                        if fs:
                            por_t.setdefault(float(mt.group(1)), []).extend(fs)
            for t, fs in por_t.items():
                if t not in self.img:   # la primera carpeta (la preferida) manda
                    self.img[t] = np.mean(leer_frames(fs[:4], rec), 0)
                    self.origen[t] = os.path.basename(c)
        self.avisos = set()

    def en(self, t):
        if not self.img:
            raise SystemExit("ERROR: no hay oscuros (darks). Tomá darks con la luz apagada y volvé a correr.")
        if t in self.img:
            return self.img[t]
        tc = min(self.img, key=lambda x: abs(x - t))
        if t not in self.avisos:
            self.avisos.add(t)
            msg(f"  [AVISO] no hay oscuro de {t:g} ms: uso el de {tc:g} ms ({self.origen[tc]}); el oscuro casi no depende de t.")
        return self.img[tc]


def promediar(fs, osc, t, rec, quien, descartes):
    """Promedio de frames con descarte de frames casi a oscuras. Devuelve (S cuentas/ms, var de S, sat, frames crudos)."""
    fr = leer_frames(fs, rec)
    d = osc.en(t)
    sig = np.array([float(np.mean(f - d)) for f in fr])
    keep = list(range(len(fr)))
    if len(fr) >= 2 and DESCARTAR:
        ref = float(np.median(sig)) if len(fr) >= 3 else float(sig.max())
        malos = [i for i in keep if sig[i] < 0.6 * ref and ref - sig[i] > 2.0]
        if malos and len(malos) < len(fr):
            for i in malos:
                descartes.append(f"{quien} {t:g} ms frame {i + 1}: {sig[i]:.1f} cuentas sobre oscuro contra {ref:.1f} de los otros")
            keep = [i for i in keep if i not in malos]
    fk = [fr[i] for i in keep]
    te = t + T0
    S = (np.mean(fk, 0) - d) / te
    sat = np.zeros(S.shape, bool)
    for f in fk:
        sat |= f >= RANGO
    V = None
    if len(fk) >= 2:
        dd = fk[0] - fk[1]
        V = (1.4826 * np.median(np.abs(dd - np.median(dd)))) ** 2 / 2 / len(fk) / te ** 2   # var de la media de n frames
    return S, V, sat, len(fk)


def elegir_t(ts, rec):
    """La exposición más larga sin saturación apreciable en el recorte; si todas saturan, la más corta."""
    if len(ts) == 1:
        return next(iter(ts))
    for t in sorted(ts, reverse=True):
        fr = leer_frames(ts[t][:1], rec)[0]
        if (fr >= RANGO).mean() < 1e-4:
            return t
    return min(ts)


# ---------------------------------------------------------------------------------------------------- recorte
def mapa_bf(SM, FL, oscm, oscf):
    """Cociente muestra/flat del LED central en el ROI entero, y máscaras de saturación y polvo (para elegir recorte)."""
    tm, tf = max(SM[CENTRO_LED]), max(FL[CENTRO_LED])
    s = np.mean(leer_frames(SM[CENTRO_LED][tm]), 0)
    f = np.mean(leer_frames(FL[CENTRO_LED][tf]), 0)
    sat = s >= RANGO
    s = (s - oscm.en(tm)) / (tm + T0); f = (f - oscf.en(tf)) / (tf + T0)
    q = s / np.maximum(gaussian_filter(f, 2), 1e-6)
    q = q / np.median(q)
    polvo = f / np.maximum(gaussian_filter(f, 15), 1e-6) < 0.8
    return q, sat, polvo


def puntaje(q, sat, polvo, f0, c0, n, ejef, ejec):
    """Fracción oscura + saturados + polvo, con una leve preferencia por estar cerca del eje óptico (ejef, ejec en px del ROI)."""
    sl = (slice(f0, f0 + n), slice(c0, c0 + n))
    oscuro = float((q[sl] < 0.5).mean())
    dist = np.hypot(f0 + n / 2 - ejef, c0 + n / 2 - ejec) / 560.0
    return oscuro + 10 * float(sat[sl].mean()) + float(polvo[sl].mean()) + 0.04 * dist ** 2, oscuro


def sugerir(q, sat, polvo, n, ejef, ejec, paso=20, margen=60):
    H, W = q.shape
    best = None
    for f0 in range(margen, H - n - margen + 1, paso):
        for c0 in range(margen, W - n - margen + 1, paso):
            p, o = puntaje(q, sat, polvo, f0, c0, n, ejef, ejec)
            if best is None or p < best[0]:
                best = (p, o, f0, c0)
    return best


# ---------------------------------------------------------------------------------------------------- solver
def cargar_solver(color, factor):
    """fpm_red de r500_red (sin el offset x del recorte .500: lo ponemos nosotros) + objetivo medido + factor fijo."""
    os.environ["R500_XOFF"] = "0"
    sys.path.insert(0, ITER_DIR)
    import importlib.util
    spec = importlib.util.spec_from_file_location("fpm_red", os.path.join(SOLVER_DIR, "fpm_red.py"))
    F = importlib.util.module_from_spec(spec); sys.modules["fpm_red"] = F; spec.loader.exec_module(F)
    import iter_runner as IR
    from dataclasses import replace as _rep
    from ptyco_full_simulator import config, optics as _opt

    def _setup(z_mm=98.0, offset_mm=(0.0, 0.0), crop=400):
        s0 = config.default_setup(color, 15, objective=F.cc.OBJECTIVE, resolution_px=(crop, crop), row_index_base=10,
                                  col_index_base=8, z_distance_mm=z_mm, led_center_offset_mm=offset_mm)
        return _rep(s0, objective=_rep(s0.objective, magnification=3.2 / LRPX, na=NA_OBJ, name=s0.objective.name + "+medido"))
    F.setup = _setup
    F.cc.factor_for = lambda s0: max(factor, _opt.canvas_upsampling_factor(s0))
    return F, IR


def rel_phase(o, sig=20):
    """Fase relativa a la fase suavizada (como eval/comun.py): saca la fase de baja frecuencia para ver los objetos."""
    from scipy import ndimage as ndi
    sm = ndi.gaussian_filter(o.real, sig) + 1j * ndi.gaussian_filter(o.imag, sig)
    return np.angle(o * np.exp(-1j * np.angle(sm)))


_G = {}


def barra(ep, epocas, dt, err, ancho=30):
    """Barra de progreso en una sola línea (se reescribe con \\r)."""
    lleno = int(ancho * ep / epocas)
    falta = dt / ep * (epocas - ep)
    return (f"\r  [{'#' * lleno}{'-' * (ancho - lleno)}] época {ep}/{epocas} ({100 * ep / epocas:3.0f} %)  "
            f"error {err:.4f}  lleva {dt / 60:4.1f} min, faltan ~{falta / 60:4.1f} min ")


def tarea(arg):
    nombre, train, epocas = arg
    F, IR, D, geo = _G["F"], _G["IR"], _G["D"], _G["geo"]
    cada, salida, keys, n = _G["cada"], _G["salida"], _G["keys"], _G["n"]
    I = {k: D["I"][k] for k in train}
    t0 = time.time()
    snaps = list(range(1, epocas + 1))          # callback en cada época: barra de progreso + guardado cada `cada`
    # LEDs con que se mide R en cada guardado: todos (completa) o los no vistos de anillo < 7 (mitades, = C1)
    if nombre == "full":
        evalk = keys
    else:
        h = int(nombre[-1])
        evalk = [k for k in keys if (k[0] + k[1]) % 2 != h and F.ring(k) < 7]
    csv = os.path.join(salida, "snapshots", f"metricas_{nombre}.csv") if cada else None
    if csv:
        with open(csv, "w") as f:
            f.write("epoca,error_solver," + ("R_ajuste" if nombre == "full" else "R_heldout_C1") + ",minutos\n")

    def cb(ep, spec, hist):
        dt = time.time() - t0
        if nombre == "full":
            sys.stdout.write(barra(ep, epocas, dt, hist[-1])); sys.stdout.flush()
            if ep == epocas:
                sys.stdout.write("\n"); sys.stdout.flush()
        if cada and (ep % cada == 0 or ep == epocas):
            obj = np.fft.ifft2(np.fft.ifftshift(spec)).astype(np.complex64)
            if _G["objetos"]:
                np.save(os.path.join(salida, "snapshots", f"objeto_{nombre}_e{ep:03d}.npy"), obj)
            import matplotlib.pyplot as plt
            plt.imsave(os.path.join(salida, "snapshots", f"amplitud_{nombre}_e{ep:03d}.png"), np.abs(obj), cmap="gray")
            R = r_leds(F, obj, evalk, geo, D, n)
            with open(csv, "a") as f:
                f.write(f"{ep},{hist[-1]:.6f},{np.mean([v[0] for v in R.values()]):.5f},{dt / 60:.2f}\n")

    obj, hist = IR.reconstruct_snap(F, I, train, geo, snaps, cb, mask={k: D["mask"][k] for k in train})
    return nombre, obj.astype(np.complex64), hist, time.time() - t0


def r_leds(F, obj, keys, geo, D, n):
    pred = F.predict(obj, keys, geo, lr_shape=(n, n))
    return {k: F.affine_residual(pred[k], D["I"][k], D["V"][k], D["mask"][k]) for k in keys}


# ---------------------------------------------------------------------------------------------------- figura
def figura(path, raw_bf, obj, hrpx, titulo):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    O = obj * np.exp(-1j * np.angle(np.sum(obj)))
    H = O.shape[0]
    ph = rel_phase(O)
    z = min(int(50 / hrpx), H // 2); c = H // 2
    L = H * hrpx
    fig, ax = plt.subplots(2, 3, figsize=(15, 10))
    filas = ((np.s_[:, :], f"recorte entero ({L:.0f} µm)"), (np.s_[c - z:c + z, c - z:c + z], f"zoom central ({2 * z * hrpx:.0f} µm)"))
    cols = ((raw_bf, "imagen cruda LED (17,15) / flat\n(amplitud, lo que ve el microscopio solo)", "gray"),
            (np.abs(O), "reconstrucción: amplitud", "gray"),
            (ph, "reconstrucción: fase relativa (rad)", "twilight"))
    for i, (sl, tt) in enumerate(filas):
        for j, (img, t, cm) in enumerate(cols):
            im = img[sl]
            ext = (0, im.shape[1] * hrpx, im.shape[0] * hrpx, 0)
            lo, hi = np.percentile(im, [0.5, 99.5])
            h = ax[i, j].imshow(im, cmap=cm, vmin=lo, vmax=hi, extent=ext, interpolation="nearest")
            plt.colorbar(h, ax=ax[i, j], fraction=0.046)
            ax[i, j].set_title(f"{t} — {tt}", fontsize=9)
            ax[i, j].set_xlabel("µm", fontsize=8); ax[i, j].set_ylabel("µm", fontsize=8)
            if i == 0:
                r = ax[i, j].add_patch(plt.Rectangle(((c - z) * hrpx, (c - z) * hrpx), 2 * z * hrpx, 2 * z * hrpx,
                                                     fill=False, ec="yellow", lw=1, ls="--"))
                r.set_zorder(5)
    plt.suptitle(titulo, fontsize=11)
    plt.tight_layout()
    plt.savefig(path, dpi=110)
    plt.close()


# ---------------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Reconstrucción FPM de una captura 15x15 (ver docstring).")
    ap.add_argument("carpeta")
    ap.add_argument("--flat", required=True)
    ap.add_argument("--dark", required=True, help="oscuros de la muestra")
    ap.add_argument("--dark-flat", default=None, help="oscuros del flat (por defecto los mismos)")
    ap.add_argument("--recorte", default=None, help="F,C = esquina superior izquierda en px del ROI; 'auto' = sugerido")
    ap.add_argument("--tam", type=int, default=400)
    ap.add_argument("--epocas", type=int, default=None, help="iteraciones del solver (si no se da, se pregunta; 160 por defecto)")
    ap.add_argument("--guardar-cada", type=int, default=None,
                    help="guardar objeto, imagen y métricas cada N épocas (0 = solo al final; si no se da, se pregunta)")
    ap.add_argument("--guardar-objetos", action="store_true",
                    help="con --guardar-cada, guardar también el objeto (.npy) de cada época guardada (pesado)")
    ap.add_argument("--validar", action="store_true")
    ap.add_argument("--color", default="r", choices=["r", "g", "b"])
    ap.add_argument("--salida", default=None)
    ap.add_argument("--nucleos", type=int, default=3)
    ap.add_argument("--offset-roi", default=None, help="OffsetX,OffsetY del ROI de la cámara en esa toma (si no: scripts/leer_offset.py)")
    ap.add_argument("--anillo-max", type=int, default=None,
                    help="usar solo los LEDs con anillo = round(distancia al LED (17,15)) <= N (misma convención que precaptura)")
    ap.add_argument("--no-descartar", action="store_true", help="no descartar frames a oscuras (solo para comparar)")
    a = ap.parse_args()
    interactivo = sys.stdin.isatty()

    def preguntar(texto, defecto):
        if not interactivo:
            return defecto
        while True:
            r = input(texto).strip()
            if not r:
                return defecto
            if r.isdigit():
                return int(r)
            print("  (escribí un número entero, o Enter para el valor por defecto)")
    if a.epocas is None:
        a.epocas = preguntar("¿Cuántas épocas (iteraciones)? [160]  (40 ≈ 4 min, 80 ≈ 7 min, 160 ≈ 12 min): ", 160)
    if a.guardar_cada is None:
        a.guardar_cada = preguntar("¿Guardar métricas cada cuántas épocas? [0 = solo al final; p. ej. 10 o 20]: ", 0)
    a.epocas = max(1, a.epocas)
    a.guardar_cada = max(0, a.guardar_cada)
    global DESCARTAR
    DESCARTAR = not a.no_descartar
    T_INI = time.time()
    color = COLOR[a.color]
    carpeta = os.path.abspath(os.path.expanduser(a.carpeta))
    nombre = os.path.basename(carpeta.rstrip("/"))
    salida = a.salida or os.path.expanduser(f"~/Documents/AleYLu/reconstrucciones/{nombre}_{time.strftime('%H%M')}")
    os.makedirs(os.path.join(salida, "datos"), exist_ok=True)
    if a.color != "r":
        msg(f"  [AVISO] La geometría está calibrada SOLO para el rojo. En {color} el offset del die del LED, la NA efectiva y el")
        msg("          factor no están medidos con esta configuración: el resultado es orientativo.")

    msg("\n---------- 1. LEYENDO LA CAPTURA ----------")
    SM, FL = indexar(carpeta, a.color), indexar(a.flat, a.color)
    esperado = {(r, c) for r in FILAS for c in COLS}
    if set(SM) != esperado:
        falt = sorted(esperado - set(SM)); extra = sorted(set(SM) - esperado)
        raise SystemExit(f"ERROR: la carpeta tiene {len(SM)} LEDs de color '{a.color}'; hacen falta los 225 de filas 10-24, "
                         f"columnas 8-22.\n  faltan {falt[:8]}{'...' if len(falt) > 8 else ''}  sobran {extra[:8]}")
    falt_f = sorted(esperado - set(FL))
    if falt_f:
        raise SystemExit(f"ERROR: al flat ({a.flat}) le faltan {len(falt_f)} LEDs, p. ej. {falt_f[:5]}.")
    if a.offset_roi:
        roi_x, roi_y = (int(v) for v in a.offset_roi.split(","))
        roi_src = "--offset-roi (dado a mano)"
    else:
        import subprocess
        o = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "leer_offset.py"), carpeta],
                           capture_output=True, text=True).stdout.strip().split(None, 1)
        roi_x, roi_y = (int(v) for v in o[0].split(","))
        roi_src = o[1] if len(o) > 1 else "?"
    roi_ok = roi_src.startswith("captura.json") or roi_src.startswith("--offset-roi")
    shp = tifffile.imread(SM[CENTRO_LED][max(SM[CENTRO_LED])][0]).shape
    H, W = shp
    msg(f"  muestra: {carpeta}  (225 LEDs, imágenes {H}x{W})")
    msg(f"  flat:    {a.flat}")
    msg(f"  oscuros: muestra {a.dark}" + (f" | flat {a.dark_flat}" if a.dark_flat and a.dark_flat != a.dark else ""))
    msg(f"  ROI de la cámara: OffsetX {roi_x}, OffsetY {roi_y}  (origen: {roi_src})")
    if not roi_ok:
        msg("  [AVISO] ¡OJO! El offset del ROI NO viene de captura.json de esta carpeta: puede no ser el de esta toma")
        msg("          (el proyecto de la cámara guarda el ROI ACTUAL; p. ej. las tomas 2026-10-20-* fueron con 4032,3040).")
        msg("          Si sabés el ROI de esta toma, pasalo con --offset-roi X,Y. Si está mal, la geometría del eje está mal.")

    # oscuros del ROI entero solo para elegir el recorte
    full = Recorte(0, 0, max(H, W))
    oscm_full = Oscuros([a.dark, a.dark_flat], None)
    oscf_full = Oscuros([a.dark_flat or a.dark, a.dark], None)
    q, satm, polvo = mapa_bf(SM, FL, oscm_full, oscf_full)
    n = a.tam
    eje_x, eje_y = ROI_CAL[0] + ROI_CAL[2] / 2, ROI_CAL[1] + ROI_CAL[2] / 2   # eje (LED (17,15)) en px del sensor
    ejef, ejec = eje_y - roi_y, eje_x - roi_x                                  # ... y en px de este ROI
    if a.recorte in (None, "", "centro"):
        f0 = int(np.clip(round(ejef - n / 2), 0, H - n)); c0 = int(np.clip(round(ejec - n / 2), 0, W - n))
        modo = ("centrado en el ROI = sobre el eje óptico (por defecto)" if (f0, c0) == ((H - n) // 2, (W - n) // 2)
                else "lo más cerca posible del eje óptico (por defecto; el ROI no está centrado en el eje)")
    elif a.recorte == "auto":
        _, _, f0, c0 = sugerir(q, satm, polvo, n, ejef, ejec)
        modo = "automático (evita manchas oscuras, saturados y polvo)"
    else:
        f0, c0 = (int(x) for x in a.recorte.split(","))
        modo = "elegido a mano (--recorte)"
    if not (0 <= f0 <= H - n and 0 <= c0 <= W - n):
        raise SystemExit(f"ERROR: el recorte {f0},{c0} de {n} px se sale de la imagen {H}x{W}.")
    rec = Recorte(f0, c0, n)
    p, osc_frac = puntaje(q, satm, polvo, f0, c0, n, ejef, ejec)
    # centro del recorte en el sensor = offset del ROI + posición en el ROI; el eje es el del ROI calibrado
    off_y = (eje_y - (roi_y + f0 + n / 2)) * MM_POR_PX
    off_x = (eje_x - (roi_x + c0 + n / 2)) * MM_POR_PX
    msg(f"\n---------- 2. RECORTE ----------")
    msg(f"  {rec}  ({n} px = {n * LRPX:.0f} µm), {modo}")
    msg(f"  offset del LED por la posición del recorte en el sensor: y {off_y:+.3f} mm, x {off_x:+.3f} mm "
        f"({off_y / 6:+.3f} / {off_x / 6:+.3f} pasos de LED)")
    if max(abs(off_x), abs(off_y)) > 1.5:
        msg("  [AVISO] el recorte cae lejos del eje óptico (> 1/4 de paso de LED): la reconstrucción puede degradarse.")
    msg(f"  zonas muy oscuras (muestra/flat < 0.5) dentro del recorte: {100 * osc_frac:.1f} %")
    if a.recorte != "auto":
        sp, so, sf, sc = sugerir(q, satm, polvo, n, ejef, ejec)
        if osc_frac > 0.02 and so < 0.6 * osc_frac:
            msg(f"  [SUGERENCIA] hay bastantes manchas oscuras; un recorte más limpio: --recorte {sf},{sc} "
                f"({100 * so:.1f} % oscuro), o --recorte auto")
    del q, satm, polvo, oscm_full, oscf_full

    msg("\n---------- 3. PREPROCESADO (oscuro, flat, máscara, promedio de frames) ----------")
    tp = time.time()
    oscm = Oscuros([a.dark, a.dark_flat], rec)
    oscf = Oscuros([a.dark_flat or a.dark, a.dark], rec)
    msg("  oscuros (cuentas medias): " + ", ".join(f"{t:g} ms {v.mean():.1f}" for t, v in sorted(oscm.img.items())))
    tfc = max(FL[CENTRO_LED])
    f0c = np.mean(leer_frames(FL[CENTRO_LED][tfc], rec), 0) - oscf.en(tfc)
    DUST = binary_dilation(f0c / gaussian_filter(f0c, 15) < 0.8, iterations=4)
    msg(f"  polvo/manchas del sensor enmascarados: {DUST.sum()} px ({100 * DUST.mean():.2f} % del recorte)")
    keys = sorted(SM)
    if a.anillo_max is not None:
        keys = [k for k in keys if round(np.hypot(k[0] - CENTRO_LED[0], k[1] - CENTRO_LED[1])) <= a.anillo_max]
        msg(f"  --anillo-max {a.anillo_max}: se usan {len(keys)} de {len(SM)} LEDs")
    S, Fl, V, SAT, TT, TF, NF, descartes, sat_leds = [], [], [], [], [], [], [], [], []
    for i, k in enumerate(keys):
        t = elegir_t(SM[k], rec)
        tf = elegir_t(FL[k], rec) if len(FL[k]) > 1 else next(iter(FL[k]))
        s, v, sat, nf = promediar(SM[k][t], oscm, t, rec, f"muestra LED {k}", descartes)
        fl, _, _, _ = promediar(FL[k][tf], oscf, tf, rec, f"flat LED {k}", descartes)
        S.append(s.astype(np.float32)); Fl.append(fl.astype(np.float32)); SAT.append(sat | DUST); TT.append(t); TF.append(tf); NF.append(nf)
        V.append(v)
        if sat.any():
            sat_leds.append((k, int(sat.sum())))
        if (i + 1) % 45 == 0:
            msg(f"  {i + 1}/225 LEDs leídos ({time.time() - tp:.0f} s)")
    # LEDs con un solo frame: varianza = mediana de los de la misma exposición
    for i, v in enumerate(V):
        if v is None:
            vs = [V[j] for j in range(len(V)) if V[j] is not None and TT[j] == TT[i]] or [x for x in V if x is not None] or [0.0]
            V[i] = float(np.median(vs)) * 2   # un frame: el doble de la varianza de la media de 2
    ts = sorted(set(TT))
    msg("  exposiciones usadas en la muestra: " + ", ".join(f"{t:g} ms ({TT.count(t)} LEDs)" for t in ts))
    msg("  frames por LED: " + ", ".join(f"{x} frame{'s' if x > 1 else ''} ({NF.count(x)} LEDs)" for x in sorted(set(NF))))
    if descartes:
        msg(f"  [AVISO] se descartaron {len(descartes)} frame(s) casi a oscuras (defecto de adquisición):")
        for d in descartes:
            msg("     - " + d)
    else:
        msg("  ningún frame descartado (no hubo frames a oscuras)")
    if sat_leds:
        msg(f"  [AVISO] {len(sat_leds)} LEDs con píxeles saturados en el recorte (se enmascaran): "
            + ", ".join(f"{k} {n_}px" for k, n_ in sat_leds[:6]) + ("..." if len(sat_leds) > 6 else ""))
    else:
        msg("  sin píxeles saturados en el recorte")
    np.savez_compressed(os.path.join(salida, "datos", "prep.npz"), keys=np.array(keys), S=np.array(S), F=np.array(Fl),
                        V=np.array(V, float), VF=np.zeros(len(keys)), SAT=np.array(SAT), t=np.array(TT), gain=0.0, read_var=0.0, DUST=DUST)
    del S, Fl, SAT
    msg(f"  preprocesado listo en {time.time() - tp:.0f} s")

    msg("\n---------- 4. RECONSTRUCCIÓN ----------")
    F, IR = cargar_solver(color, FACTOR[color])
    geo = F.geometry(Z_MM, offset_mm=(off_x, off_y), crop=n)
    fr = np.hypot(*np.array([geo["fxy"][k] for k in keys]).T)
    bf = sorted([k for k, f in zip(keys, fr) if f < geo["na"] / geo["lam"]], key=lambda k: (k != CENTRO_LED, k))
    cerca = [k for k, f in zip(keys, fr) if abs(f / (geo["na"] / geo["lam"]) - 1) < 0.03]
    F.BF = bf
    D = F.load_real(os.path.join(salida, "datos", "prep.npz"))
    msg(f"  geometría: z {Z_MM:g} mm, píxel {geo['lrpx']:.3f} µm, NA {geo['na']:.4f}, λ {geo['lam']} µm, factor {geo['factor']} "
        f"-> píxel reconstruido {geo['hrpx']:.3f} µm")
    msg(f"  LEDs de campo claro (BF): {bf}")
    if cerca:
        msg(f"  [AVISO] LEDs casi en el borde de la pupila (pueden reconstruir peor): {cerca}")
    tareas = [("full", keys, a.epocas)]
    if a.validar:
        for h in (0, 1):
            tareas.append((f"mitad{h}", [k for k in keys if (k[0] + k[1]) % 2 == h], a.epocas))
    nproc = max(1, min(a.nucleos, len(tareas)))
    msg(f"  {a.epocas} épocas, {len(tareas)} reconstrucción(es) en {nproc} núcleo(s)"
        + (" (la completa + 2 mitades para validar)" if a.validar else ""))
    if a.guardar_cada:
        os.makedirs(os.path.join(salida, "snapshots"), exist_ok=True)
        nsnap = len(set(list(range(a.guardar_cada, a.epocas + 1, a.guardar_cada)) + [a.epocas])) * len(tareas)
        msg(f"  guardando métricas e imagen cada {a.guardar_cada} épocas en {os.path.join(salida, 'snapshots')}"
            + (f" (+ {nsnap} objetos .npy, ~{nsnap * 11.5:.0f} MB)" if a.guardar_objetos else
               " (sin objetos .npy; --guardar-objetos para guardarlos)"))
    _G.update(F=F, IR=IR, D=D, geo=geo, cada=a.guardar_cada, salida=salida, keys=keys, n=n, objetos=a.guardar_objetos)
    tr = time.time()
    res = {}
    if nproc == 1:
        for t in tareas:
            r = tarea(t); res[r[0]] = r[1:]
    else:
        with mp.get_context("fork").Pool(nproc) as pool:
            for r in pool.imap_unordered(tarea, tareas):
                res[r[0]] = r[1:]
    t_rec = time.time() - tr
    msg(f"  reconstrucción lista en {t_rec / 60:.1f} min")

    msg("\n---------- 5. MÉTRICAS Y FIGURA ----------")
    obj, hist, _ = res["full"]
    np.save(os.path.join(salida, "objeto_complejo.npy"), obj)
    Rall = r_leds(F, obj, keys, geo, D, n)
    train_R = float(np.mean([v[0] for v in Rall.values()]))
    lat = float(F.lattice_score(obj))
    o0 = F.initial_object(D["I"], geo["factor"], "fourier_avg")
    ks7 = [k for k in keys if k not in bf and F.ring(k) < 7]
    R0 = r_leds(F, o0, ks7, geo, D, n)
    sin_fpm = float(np.mean([v[0] for v in R0.values()]))
    val = None
    if a.validar:
        val = {}
        for h in (0, 1):
            o, _, _ = res[f"mitad{h}"]
            ho = [k for k in keys if (k[0] + k[1]) % 2 != h and F.ring(k) < 7]   # = heldout_R_ring_lt7 de runner_2110
            Rh = r_leds(F, o, ho, geo, D, n)
            val[h] = (float(np.mean([v[0] for v in Rh.values()])), float(np.mean([v[1] for v in Rh.values()])), len(ho))
        np.save(os.path.join(salida, "objeto_mitadA.npy"), res["mitad0"][0])
        np.save(os.path.join(salida, "objeto_mitadB.npy"), res["mitad1"][0])
    raw = np.real(F.fourier_upsample(np.sqrt(np.clip(D["I"][CENTRO_LED], 0, None)), geo["factor"]))
    figura(os.path.join(salida, "reconstruccion.png"), raw, obj, geo["hrpx"],
           f"{nombre}  —  {rec}  —  {a.epocas} épocas, color {color}")
    t_tot = time.time() - T_INI

    L = []
    L.append(f"RECONSTRUCCIÓN FPM de {nombre}   ({time.strftime('%d/%m/%Y %H:%M')})")
    L.append("=" * 78)
    L.append(f"muestra:            {carpeta}")
    L.append(f"flat:               {os.path.abspath(a.flat)}")
    L.append(f"oscuros muestra:    {a.dark}")
    L.append(f"oscuros flat:       {a.dark_flat or a.dark}")
    L.append(f"color:              {color}" + ("" if a.color == "r" else "  (NO calibrado: orientativo)"))
    L.append(f"recorte:            {rec}  ({n} px = {n * LRPX:.0f} µm), {modo}")
    L.append(f"ROI cámara:         OffsetX {roi_x}, OffsetY {roi_y}  (origen: {roi_src})"
             + ("" if roi_ok else "\n                    ¡OJO! no viene de captura.json: puede no ser el ROI de esta toma"))
    L.append(f"offset LED:         y {off_y:+.3f} mm, x {off_x:+.3f} mm  (0.001696 mm por px entre el centro del recorte en el sensor"
             f" y el eje calibrado, ROI {ROI_CAL[0]},{ROI_CAL[1]} + {ROI_CAL[2] // 2} px)")
    L.append(f"geometría:          z {Z_MM:g} mm, píxel cámara en la muestra {geo['lrpx']:.3f} µm, NA {geo['na']:.4f}, "
             f"factor {geo['factor']}, píxel reconstruido {geo['hrpx']:.4f} µm")
    L.append(f"LEDs BF:            {bf}")
    L.append(f"exposiciones:       " + ", ".join(f"{t:g} ms x{TT.count(t)}" for t in ts))
    L.append(f"frames descartados: {len(descartes)}" + "".join(f"\n                    - {d}" for d in descartes))
    L.append(f"saturados:          {len(sat_leds)} LEDs con píxeles saturados en el recorte (enmascarados)")
    L.append(f"polvo enmascarado:  {DUST.sum()} px ({100 * DUST.mean():.2f} %)")
    L.append(f"épocas:             {a.epocas}   (solver A+init, paso 0.3 con rampa)")
    if a.guardar_cada:
        L.append(f"guardado:           cada {a.guardar_cada} épocas en snapshots/ (metricas_*.csv, amplitud_*.png"
                 + (", objeto_*.npy)" if a.guardar_objetos else ")"))
    L.append(f"tiempo:             total {t_tot / 60:.1f} min (preprocesado {(tr - tp) / 60:.1f}, reconstrucción {t_rec / 60:.1f}), "
             f"{nproc} núcleo(s)")
    L.append("")
    L.append("MÉTRICAS")
    L.append("-" * 78)
    L.append(f"R de ajuste (todos los LEDs que usó):  {train_R:.3f}")
    L.append("    R = error de la predicción del modelo / variación de la imagen medida. 0 = perfecta, 1 = no explica nada.")
    L.append(f"C3 artefacto de grilla (lattice):      {lat:.1e}   ({'OK' if lat <= 0.01 else 'ALTO'}; pasa si <= 0.01)")
    if val:
        rm = float(np.mean([v[0] for v in val.values()])); pm = float(np.mean([v[1] for v in val.values()]))
        L.append(f"C1 R held-out (validación por mitades): {rm:.3f}   (mitad A {val[0][0]:.3f}, mitad B {val[1][0]:.3f}; "
                 f"{val[0][2] + val[1][2]} LEDs de anillo < 7 no vistos)")
        L.append(f"    sin FPM (solo la imagen BF agrandada): {sin_fpm:.3f};  piso de ruido: {pm:.3f}")
        ok = rm <= sin_fpm - 0.10
        L.append(f"    -> C1 {'PASA' if ok else 'NO PASA'} (pide R <= {sin_fpm - 0.10:.3f}). Con R = {rm:.2f} el modelo explica "
                 f"~{100 * (1 - rm ** 2):.0f} % de la variación de las imágenes que no vio.")
        L.append("    (los INFORME miden C1 con 5 folds y sin los LEDs BF; con 2 mitades el número es parecido pero no idéntico:")
        L.append("     en 2026-10-21.500 a 40 épocas, mitades 0.878 contra 5 folds 0.892. Comparar siempre mitades con mitades.)")
    else:
        L.append(f"sin FPM (referencia de R, anillos < 7): {sin_fpm:.3f}.  Para la validación (C1) correr con --validar.")
    L.append("")
    L.append("ARCHIVOS")
    L.append("-" * 78)
    L.append("reconstruccion.png   arriba: el recorte entero; abajo: zoom del centro (recuadro amarillo). Columnas:")
    L.append("                     1) imagen cruda del LED central dividida por el flat (resolución del objetivo solo),")
    L.append("                     2) amplitud reconstruida, 3) fase reconstruida relativa (sin la fase de baja frecuencia).")
    L.append("                     Si la reconstrucción funciona, 2 y 3 muestran más detalle que 1 en el mismo lugar.")
    L.append(f"objeto_complejo.npy  objeto complejo {obj.shape[0]}x{obj.shape[1]}, píxel {geo['hrpx']:.4f} µm "
             "(np.load; np.abs = amplitud, np.angle = fase)")
    if val:
        L.append("objeto_mitadA/B.npy  reconstrucciones con cada mitad de los LEDs (para comparar entre sí)")
    L.append("datos/prep.npz       imágenes preprocesadas (S muestra, F flat en cuentas/ms, máscara SAT)")
    L.append("registro.txt         todo lo que se imprimió en pantalla")
    txt = "\n".join(L)
    open(os.path.join(salida, "resumen.txt"), "w").write(txt + "\n")
    json.dump(dict(carpeta=carpeta, recorte=[f0, c0, n], offset_mm=[off_x, off_y], epocas=a.epocas, color=color, train_R=train_R,
                   lattice=lat, sin_fpm=sin_fpm, heldout=({str(h): v[0] for h, v in val.items()} if val else None),
                   descartes=descartes, hist=hist, t_total_s=t_tot, t_rec_s=t_rec, hrpx=geo["hrpx"], bf=[list(k) for k in bf]),
              open(os.path.join(salida, "datos", "metricas.json"), "w"), indent=1)
    msg(txt)
    msg(f"\nSALIDA: {salida}")


if __name__ == "__main__":
    main()
