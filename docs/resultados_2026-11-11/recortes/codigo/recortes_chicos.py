#!/usr/bin/env python3
"""recortes_chicos.py -- brazo de recortes chicos (20 px; opcional 40/80 px) alrededor de cada partícula aislada.

Envoltorio mínimo alrededor del MISMO pipeline que reconstruir_plan.py (plan_2026-11-04/codigo), sin tocarlo:
  * los datos de cada recorte chico son el SUB-ARREGLO de datos/prep.npz del recorte de 200 px de su región
    (S muestra y F flat en cuentas/ms ya con oscuro restado, máscara SAT = saturados U polvo, V varianza) -> mismos píxeles,
    misma exposición elegida, mismo oscuro y flat que la referencia. Lo único que cambia es el tamaño del dominio.
  * F.load_real (BF = S/F·<F>, DF = S - gauss(F, 8)) se aplica sobre el recorte chico, igual que haría el driver con --tam 20
    (el gauss de 8 px del flat se calcula sobre 20 px: diferencia menor, el flat es suave);
  * offset del LED (sistema no telecéntrico) recalculado para el centro del recorte chico con la fórmula del driver;
  * misma geometría (env Z_MM, NA_OBJ, LAM_NM), mismo factor 3, mismo lazo IR.reconstruct_snap (A+init, paso 0.3 con rampa),
    mismas épocas;
  * --nulo: misma permutación de fxy entre LEDs DF que NULO_DF=1 del driver (seed 0 sobre los DF ordenados).

Uso: Z_MM=99.5 NA_OBJ=0.0720 LAM_NM=617 python3 recortes_chicos.py --tam 20 [--nulo] [--ids A01,B02] [--procs 2]
Salida: runs/chicos_<tam>[_nulo]/<id>.npz  (obj complejo, lr_bf = I del LED (17,15), hrpx, lrpx, offset, tiempo, hist)
"""
import argparse
import json
import os
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "1")
import multiprocessing as mp  # noqa: E402
import numpy as np  # noqa: E402

DRV_DIR = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04/codigo"
P0 = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-11/recortes"
ROI = (3968, 1966)
sys.path.insert(0, DRV_DIR)
import reconstruir_plan as RP  # noqa: E402  (lee Z_MM / NA_OBJ del entorno al importar)

_S = {}


def preparar(p, tam, salida):
    """Sub-recorte del prep.npz de 200 px de la región de la partícula. Devuelve (ruta npz temporal, f0, c0 en el ROI)."""
    reg = p["region"]
    d = dict(np.load(os.path.join(P0, "runs", f"ref_{reg}", "datos", "prep.npz")))
    h = tam // 2
    fr, cr = p["fila_rec"], p["col_rec"]
    a0, b0 = fr - h, cr - h
    if a0 < 0 or b0 < 0 or a0 + tam > d["S"].shape[1] or b0 + tam > d["S"].shape[2]:
        return None
    sl = (slice(None), slice(a0, a0 + tam), slice(b0, b0 + tam))
    out = dict(d)
    for k in ("S", "F", "SAT"):
        out[k] = d[k][sl]
    out["DUST"] = d["DUST"][a0:a0 + tam, b0:b0 + tam]
    ruta = os.path.join(salida, f"prep_{p['id']}.npz")
    np.savez(ruta, **out)
    J = json.load(open(os.path.join(P0, "particulas.json")))
    f0r, c0r, _ = J["regiones"][reg]
    return ruta, f0r + a0, c0r + b0


def leds_que_cambian(F, geo, keys, tam):
    """LEDs cuyo estado BF/DF en el modelo discreto (bin DC desplazado dentro de la pupila binaria) difiere del exacto
    (|f| < NA/λ). Misma lógica que codigo/redondeo.py."""
    H = tam * geo["factor"]
    Pm = F.circular_pupil((tam, tam), geo["lrpx"], geo["na"], geo["lam"])
    kc = geo["na"] / geo["lam"]
    out = []
    for k in keys:
        fx, fy = geo["fxy"][k]
        ys, xs = F.led_crop_window((H, H), geo["hrpx"], (tam, tam), fx, fy)
        iy, ix = tam // 2 - (ys.start + tam // 2 - H // 2), tam // 2 - (xs.start + tam // 2 - H // 2)
        bfm = bool(0 <= iy < tam and 0 <= ix < tam and Pm[iy, ix])
        if bfm != (np.hypot(fx, fy) < kc):
            out.append(k)
    return out


def una(arg):
    p, tam, epocas, nulo, salida, excluir = arg
    t0 = time.time()
    pr = preparar(p, tam, salida)
    if pr is None:
        return p["id"], "no entra en el recorte de 200 px"
    ruta, f0, c0 = pr
    F, IR = RP.cargar_solver("red", RP.FACTOR["red"])
    eje_x, eje_y = RP.ROI_CAL[0] + RP.ROI_CAL[2] / 2, RP.ROI_CAL[1] + RP.ROI_CAL[2] / 2
    off_y = (eje_y - (ROI[1] + f0 + tam / 2)) * RP.MM_POR_PX
    off_x = (eje_x - (ROI[0] + c0 + tam / 2)) * RP.MM_POR_PX
    geo = F.geometry(RP.Z_MM, offset_mm=(off_x, off_y), crop=tam)
    keys = sorted(tuple(int(v) for v in k) for k in np.load(ruta)["keys"])
    if nulo:   # = PARCHE NULO_DF del driver
        fc = geo["na"] / geo["lam"]
        df = sorted(k for k in keys if np.hypot(*geo["fxy"][k]) >= fc)
        perm = np.random.default_rng(0).permutation(len(df))
        v = [geo["fxy"][df[i]] for i in perm]
        geo["fxy"].update({k: x for k, x in zip(df, v)})
    fr = np.hypot(*np.array([geo["fxy"][k] for k in keys]).T)
    bf = sorted([k for k, f in zip(keys, fr) if f < geo["na"] / geo["lam"]], key=lambda k: (k != RP.CENTRO_LED, k))
    F.BF = bf
    D = F.load_real(ruta)
    keys = D["keys"]
    cambian = leds_que_cambian(F, geo, keys, tam)
    if excluir:   # variante diagnóstica: sacar los LEDs cuyo estado BF/DF cambia por el redondeo a la grilla
        keys = [k for k in keys if k not in cambian]
    I = {k: D["I"][k] for k in keys}
    obj, hist = IR.reconstruct_snap(F, I, keys, geo, [epocas], lambda *a: None, mask={k: D["mask"][k] for k in keys})
    np.savez_compressed(os.path.join(salida, f"{p['id']}.npz"), obj=obj.astype(np.complex64),
                        lr_bf=D["I"][RP.CENTRO_LED].astype(np.float32), hrpx=geo["hrpx"], lrpx=geo["lrpx"],
                        offset_mm=(off_x, off_y), f0c0=(f0, c0), bf=np.array(bf),
                        cambian=np.array(cambian).reshape(-1, 2), n_leds=len(keys), hist=np.array(hist),
                        t_s=time.time() - t0, factor=geo["factor"], na=geo["na"], lam=geo["lam"])
    os.remove(ruta)
    return p["id"], f"ok {time.time() - t0:.1f} s, BF {len(bf)}, LEDs {len(keys)}, cambian BF/DF {cambian}, err final {hist[-1]:.4g}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tam", type=int, default=20)
    ap.add_argument("--epocas", type=int, default=160)
    ap.add_argument("--nulo", action="store_true")
    ap.add_argument("--ids", default=None)
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--excluir-cambian", action="store_true", help="diagnóstico: sin los LEDs que cambian BF/DF por redondeo")
    a = ap.parse_args()
    J = json.load(open(os.path.join(P0, "particulas.json")))["particulas"]
    if a.ids:
        J = [p for p in J if p["id"] in a.ids.split(",")]
    salida = os.path.join(P0, "runs", f"chicos_{a.tam}" + ("_nulo" if a.nulo else "") + ("_sincambian" if a.excluir_cambian else ""))
    os.makedirs(salida, exist_ok=True)
    print(f"geometría: z {RP.Z_MM} mm, NA {RP.NA_OBJ}, LAM_NM {os.environ.get('LAM_NM')}, tam {a.tam}, épocas {a.epocas}, "
          f"nulo {a.nulo}, {len(J)} partículas", flush=True)
    t0 = time.time()
    tareas = [(p, a.tam, a.epocas, a.nulo, salida, a.excluir_cambian) for p in J]
    with mp.get_context("fork").Pool(a.procs) as pool:
        for r in pool.imap_unordered(una, tareas):
            print(*r, flush=True)
    print(f"total {time.time() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    main()
