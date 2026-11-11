#!/usr/bin/env python3
"""recortes.py -- reconstrucción de recortes chicos (20 px; opcional 40/80) alrededor de cada esfera de 5 µm aislada.
Adaptado de plan_2026-11-11/recortes/codigo/recortes_chicos.py (agente hermano, perlas de 500 nm), sin tocar el driver:
  * datos = SUB-ARREGLO de plan_2026-11-04/epocas_400b/datos/prep.npz (recorte 400 px, filas 360:760, cols 80:480 del ROI;
    idéntico píxel a píxel a epocas_200/datos/prep.npz en el solape): S, F (cuentas/ms, oscuro restado), SAT, DUST, misma
    exposición por LED. F.load_real (BF = S/F·<F>, DF = S - gauss(F, 8)) se aplica sobre el recorte chico, como haría el driver.
  * offset del LED (no telecéntrico) recalculado para el centro del recorte chico con la fórmula del driver (líneas 466-468);
  * misma geometría que la referencia: entorno sin Z_MM/NA_OBJ/LAM_NM -> z 102 mm, NA 0.069·1.25/1.29 = 0.06686, λ 0.63 µm
    (config.py), factor 3, mismo lazo IR.reconstruct_snap (A+init, paso 0.3 con rampa), mismas épocas (160);
  * --nulo: misma permutación de fxy entre LEDs DF que NULO_DF=1 del driver (seed 0 sobre los DF ordenados).
  * --centro F,C --tam 200: modo validación (recorte arbitrario en coordenadas del recorte de 400).
Salida: runs/r<tam>[_nulo]/<id>.npz
"""
import argparse, json, os, sys, time
os.environ.setdefault("OMP_NUM_THREADS", "1")
for v in ("Z_MM", "NA_OBJ", "LAM_NM", "PUPILA_W_NA", "NULO_DF"):
    os.environ.pop(v, None)
import numpy as np  # noqa: E402

DRV_DIR = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04/codigo"
PREP = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04/epocas_400b/datos/prep.npz"
P0 = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-11/recortes_5um"
ROI = (3968, 1966)       # OffsetX, OffsetY (captura.json de 2026-11-03-red)
ORIG400 = (360, 80)      # esquina (fila, col) del recorte de 400 px en el ROI
sys.path.insert(0, DRV_DIR)
import reconstruir_plan as RP  # noqa: E402

_D = dict(np.load(PREP))


def preparar(fy, fx, tam, ruta):
    h = tam // 2
    a0, b0 = fy - h, fx - h
    if a0 < 0 or b0 < 0 or a0 + tam > 400 or b0 + tam > 400:
        return None
    sl = (slice(None), slice(a0, a0 + tam), slice(b0, b0 + tam))
    out = dict(_D)
    for k in ("S", "F", "SAT"):
        out[k] = _D[k][sl]
    out["DUST"] = _D["DUST"][a0:a0 + tam, b0:b0 + tam]
    np.savez(ruta, **out)
    return ORIG400[0] + a0, ORIG400[1] + b0


def leds_que_cambian(F, geo, keys, tam):
    """LEDs cuyo estado BF/DF en el modelo discreto (bin DC desplazado dentro de la pupila binaria) difiere del exacto
    (|f| < NA/λ). Copiada de recortes_chicos.py del agente hermano (= codigo/redondeo.py)."""
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


def una(pid, fy, fx, tam, epocas, nulo, salida, snaps=None, excluir=False):
    t0 = time.time()
    ruta = os.path.join(salida, f"prep_{pid}.npz")
    pr = preparar(fy, fx, tam, ruta)
    if pr is None:
        return f"{pid} no entra en el recorte de 400 px"
    f0, c0 = pr
    F, IR = RP.cargar_solver("red", RP.FACTOR["red"])
    eje_x, eje_y = RP.ROI_CAL[0] + RP.ROI_CAL[2] / 2, RP.ROI_CAL[1] + RP.ROI_CAL[2] / 2
    off_y = (eje_y - (ROI[1] + f0 + tam / 2)) * RP.MM_POR_PX
    off_x = (eje_x - (ROI[0] + c0 + tam / 2)) * RP.MM_POR_PX
    geo = F.geometry(RP.Z_MM, offset_mm=(off_x, off_y), crop=tam)
    keys = [tuple(int(v) for v in k) for k in _D["keys"]]
    if nulo:
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
    if excluir:
        keys = [k for k in keys if k not in cambian]
    I = {k: D["I"][k] for k in keys}
    snaps = snaps or [epocas]
    guard = {}

    def cb(ep, spec, hist):
        guard[ep] = np.fft.ifft2(np.fft.ifftshift(spec)).astype(np.complex64)
    obj, hist = IR.reconstruct_snap(F, I, keys, geo, snaps, cb, mask={k: D["mask"][k] for k in keys})
    extra = {f"obj_e{ep:03d}": o for ep, o in guard.items()}
    np.savez_compressed(os.path.join(salida, f"{pid}.npz"), obj=obj.astype(np.complex64),
                        lr_bf=D["I"][RP.CENTRO_LED].astype(np.float32), hrpx=geo["hrpx"], lrpx=geo["lrpx"],
                        offset_mm=(off_x, off_y), f0c0=(f0, c0), centro400=(fy, fx), bf=np.array(bf), n_leds=len(keys),
                        hist=np.array(hist), t_s=time.time() - t0, factor=geo["factor"], na=geo["na"], lam=geo["lam"],
                        z_mm=RP.Z_MM, cambian=np.array(cambian).reshape(-1, 2), epocas=epocas, nulo=nulo, **extra)
    os.remove(ruta)
    return (f"{pid} ok {time.time() - t0:.1f} s, BF {bf}, LEDs {len(keys)}, cambian BF/DF {cambian}, offset ({off_x:+.3f},{off_y:+.3f}) mm, "
            f"NA {geo['na']:.5f} λ {geo['lam']} z {RP.Z_MM}, err final {hist[-1]:.4g}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tam", type=int, default=20)
    ap.add_argument("--epocas", type=int, default=160)
    ap.add_argument("--nulo", action="store_true")
    ap.add_argument("--ids", default=None)
    ap.add_argument("--centro", default=None, help="F,C en coords del recorte de 400 (modo validación)")
    ap.add_argument("--snaps", default=None, help="épocas a guardar, coma")
    ap.add_argument("--salida", default=None)
    ap.add_argument("--excluir-cambian", action="store_true", help="diagnóstico: sin los LEDs que cambian BF/DF por redondeo")
    a = ap.parse_args()
    salida = a.salida or os.path.join(P0, "runs", f"r{a.tam}" + ("_nulo" if a.nulo else "") + ("_sincambian" if a.excluir_cambian else ""))
    os.makedirs(salida, exist_ok=True)
    snaps = [int(s) for s in a.snaps.split(",")] if a.snaps else None
    if a.centro:
        fy, fx = (int(v) for v in a.centro.split(","))
        tareas = [(f"c{fy}_{fx}", fy, fx)]
    else:
        J = json.load(open(os.path.join(P0, "particulas.json")))["particulas"]
        if a.ids:
            J = [p for p in J if p["id"] in a.ids.split(",")]
        tareas = [(p["id"], p["fila400"], p["col400"]) for p in J]
    print(f"tam {a.tam}, épocas {a.epocas}, nulo {a.nulo}, {len(tareas)} recortes -> {salida}", flush=True)
    t0 = time.time()
    for t in tareas:
        print(una(*t, a.tam, a.epocas, a.nulo, salida, snaps, a.excluir_cambian), flush=True)
    print(f"total {time.time() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    main()
