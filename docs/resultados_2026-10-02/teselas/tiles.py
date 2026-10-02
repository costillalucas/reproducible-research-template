"""tiles.py -- FPM por teselas (2026-10-02). No toca src/ ni iter_runner.py.
Cada tesela: k_LED calculado desde el centro de la tesela en la muestra:
  offset_eff = offset_die - (x_t, y_t) [mm], x = eje 1 (columnas imagen), y = eje 0 (filas),
  respecto del centro del campo de 400 px (signo verificado con los flats: (18,14) es brillante a fila alta / col baja).
Reconstrucción por tesela = IR.reconstruct_snap (A+init idéntico), LEDs de la tarea full (todos, sin excluir).
Uso: python3 tiles.py run NPROC NT:TILE:Z:AUTO [...]  (40 épocas; AUTO=1 excluye LEDs a horcajadas por tesela)   |  python3 tiles.py sanity MAXEP
"""
import json, os, sys, time
os.environ.setdefault("OMP_NUM_THREADS", "1")
import multiprocessing as mp
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "iteraciones_2026-09-30"))
import iter_runner as IR
DS, OFF, N = "b_red", (0.0, 4.06), 400
SAVE = {3, 5, 20, 40, 80}
MAXEP = 40


def starts(nt, tile):
    return [int(round(i * (N - tile) / (nt - 1))) for i in range(nt)] if nt > 1 else [0]


def run_tile(arg):
    tag, y0, x0, tile, maxep, shift = arg[:6]
    Z = arg[6] if len(arg) > 6 else None; AUTO = len(arg) > 7 and arg[7]
    od = os.path.join(HERE, "out", tag, f"t{y0:03d}_{x0:03d}")
    if os.path.exists(os.path.join(od, "done.json")):
        return tag, y0, x0, "skip"
    os.makedirs(od, exist_ok=True)
    F, R = IR._load(DS)
    t = next(x for x in IR.task_defs(DS, R) if x["kind"] == "full")
    D = F.load_real()
    keys = D["keys"]
    train = [k for k in keys if k in set(map(tuple, t["train"]))] if t.get("train") else keys
    z = Z or t["z"]
    lrpx = F.geometry(z, offset_mm=OFF)["lrpx"]
    excl = []
    if AUTO:   # LEDs cuyo estado BF/DF cambia dentro de la tesela (malla 7x7 de puntos) -> fuera solo en esta tesela
        sgn = {}
        for py in np.linspace(y0, y0 + tile, 7):
            for px in np.linspace(x0, x0 + tile, 7):
                g = F.geometry(z, offset_mm=(OFF[0] - (px - N / 2) * lrpx / 1000, OFF[1] - (py - N / 2) * lrpx / 1000))
                r = g["na"] / g["lam"]
                for k in keys:
                    sgn.setdefault(k, set()).add(bool(np.hypot(*g["fxy"][k]) < r))
        excl = [k for k, v in sgn.items() if len(v) > 1]
        train = [k for k in train if k not in excl]
    cy, cx = y0 + tile / 2 - N / 2, x0 + tile / 2 - N / 2   # px respecto del centro
    yt, xt = (cy * lrpx / 1000, cx * lrpx / 1000) if shift else (0.0, 0.0)
    off = (OFF[0] - xt, OFF[1] - yt)
    geo = F.geometry(z, offset_mm=off, crop=tile)
    sl = (slice(y0, y0 + tile), slice(x0, x0 + tile))
    I = {k: D["I"][k][sl] for k in train}
    M = {k: D["mask"][k][sl] for k in train}
    t0 = time.time()

    def cb(ep, spec, hist):
        if ep in SAVE:
            np.save(os.path.join(od, f"obj_e{ep:03d}.npy"), np.fft.ifft2(np.fft.ifftshift(spec)).astype(np.complex64))
        print(f"[{tag} {y0},{x0}] ep {ep} {time.time()-t0:.0f}s", flush=True)

    snaps = [e for e in IR.SNAPS if e <= maxep]
    _, hist = IR.reconstruct_snap(F, I, train, geo, snaps, cb, mask=M)
    json.dump(dict(y0=y0, x0=x0, tile=tile, offset_mm=off, factor=geo["factor"], hrpx=geo["hrpx"], n_train=len(train), z=z, excl=[list(k) for k in excl],
                   hist=hist, wall_s=time.time() - t0), open(os.path.join(od, "done.json"), "w"))
    return tag, y0, x0, "done %.0fs" % (time.time() - t0)


if __name__ == "__main__":
    if sys.argv[1] == "sanity":
        print(run_tile(("sanity", 0, 0, N, int(sys.argv[2]), True)))
    else:
        T = []
        for spec in sys.argv[3:]:   # NT:TILE:Z:AUTO
            nt, tile, z, auto = spec.split(":"); nt, tile, z, auto = int(nt), int(tile), float(z), auto == "1"
            tag = f"g{nt}x{nt}_{tile}" + (f"_z{z:g}" if z != 98 else "") + ("_auto" if auto else "")
            T += [(tag, y, x, tile, MAXEP, True, z, auto) for y in starts(nt, tile) for x in starts(nt, tile)]
        nproc = int(sys.argv[2])
        with mp.get_context("fork").Pool(nproc, maxtasksperchild=1) as p:
            for r in p.imap_unordered(run_tile, T):
                print("FIN", *r, flush=True)
