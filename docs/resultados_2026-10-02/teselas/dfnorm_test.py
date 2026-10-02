"""dfnorm_test.py -- hipótesis: (18,14),(18,16) están en F.BF y se normalizan con flat (S/F·<F>); en la parte DF del campo
eso infla la señal. Prueba: die full, todos los LEDs, pero esos dos con el preprocesado DF (S − gauss(F, 8)). 5/20 épocas."""
import os, sys, json
import numpy as np
from scipy.ndimage import gaussian_filter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "iteraciones_2026-09-30")); sys.path.insert(0, os.path.join(HERE, "..", "offset_color_2026-10-02"))
import iter_runner as IR, rayas2
F, R = IR._load("b_red"); t = next(x for x in IR.task_defs("b_red", R) if x["kind"] == "full")
D = F.load_real(); d = np.load(IR.DATASETS["b_red"][0] + "/prep.npz"); keys = [tuple(map(int, k)) for k in d["keys"]]
for k in [(18, 14), (18, 16)]:
    i = keys.index(k); s, f = d["S"][i].astype(float), d["F"][i].astype(float)
    D["I"][k] = s - gaussian_filter(f, 8.0)
train = [k for k in D["keys"] if k in set(map(tuple, t["train"]))] if t.get("train") else D["keys"]
geo = F.geometry(98.0, offset_mm=(0, 4.06)); out = {}
ME = int(sys.argv[1]) if len(sys.argv) > 1 else 5
def cb(ep, spec, hist):
    if ep in (5, 20, 40):
        o = np.fft.ifft2(np.fft.ifftshift(spec)); np.save(os.path.join(HERE, "out", f"dfnorm_e{ep:03d}.npy"), o.astype(np.complex64))
        out[ep] = rayas2.rayas(o.astype(np.complex64)); print(ep, out[ep], flush=True)
IR.reconstruct_snap(F, {k: D["I"][k] for k in train}, train, geo, [0, 5, 20, 40][: 1 + sum(e <= ME for e in (5, 20, 40))], cb,
                    mask={k: D["mask"][k] for k in train})
json.dump(out, open(os.path.join(HERE, "dfnorm_test.json"), "w"), indent=1)
