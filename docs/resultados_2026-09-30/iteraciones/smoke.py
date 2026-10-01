"""smoke.py -- verificaciones antes de lanzar:
 (1) reconstruct_snap == F.reconstruct (A+init) bit a bit, a 3 épocas, rojo 28/09 b, tarea full;
 (2) fold f0 del rojo a 40 épocas reproduce per_led de captura_2026-09-28b/red/out/tasks/real_A+init_z98.0_f0.json;
 (3) s/época por dataset (tarea full, 3 épocas).  Escribe smoke.json. Salidas temporales en smoke_out/."""
import json, os, sys, time
import numpy as np
import iter_runner as IR
IR.outdir = lambda ds, name: os.path.join(IR.HERE, "smoke_out", ds, name)
res = {}
F, R = IR._load("b_red")
D = F.load_real(); geo = F.geometry(98.0); keys = D["keys"]
m = {k: D["mask"][k] for k in keys}
a = F.reconstruct(D["I"], keys, geo, iterations=3, mask=m, init="fourier_avg")["object"]
got = {}
IR.reconstruct_snap(F, D["I"], keys, geo, [3], lambda e, s, h: got.__setitem__(e, np.fft.ifft2(np.fft.ifftshift(s))), mask=m)
res["bitwise_3ep_maxabsdiff"] = float(np.max(np.abs(a - got[3])))
print("bitwise", res["bitwise_3ep_maxabsdiff"], flush=True)
# (2)
t0 = time.time()
IR.run_task(("b_red", "real_A+init_z98.0_f0", 40))
rows = [json.loads(l) for l in open(os.path.join(IR.outdir("b_red", "real_A+init_z98.0_f0"), "metrics.jsonl"))]
r40 = next(r for r in rows if r["epoch"] == 40)
ref = json.load(open(os.path.join(IR.DATASETS["b_red"][0], "out", "tasks", "real_A+init_z98.0_f0.json")))["per_led"]
d = [abs(r40["per_led"][k][0] - v[0]) for k, v in ref.items()]
res["f0_40ep_heldout_R_ring_lt7"] = r40["heldout_R_ring_lt7"]
res["f0_ref_heldout_R_ring_lt7"] = float(np.mean([v[0] for v in ref.values() if v[2] < 7 and not v[3]]))
res["f0_per_led_maxabsdiff"] = float(max(d)); res["f0_wall_s"] = time.time() - t0
print(res, flush=True)
# (3)
for ds in IR.ORDER:
    F, R = IR._load(ds); D = F.load_real(); geo = F.geometry(IR.DATASETS[ds][1]); keys = D["keys"]
    ts = []
    IR.reconstruct_snap(F, D["I"], keys, geo, [1, 3], lambda e, s, h: ts.append(time.time()), mask={k: D["mask"][k] for k in keys})
    res[f"s_per_epoch_{ds}"] = (ts[1] - ts[0]) / 2; res[f"factor_{ds}"] = geo["factor"]; res[f"n_leds_{ds}"] = len(keys)
    print(ds, res[f"s_per_epoch_{ds}"], geo["factor"], len(keys), flush=True)
json.dump(res, open("smoke.json", "w"), indent=1)
