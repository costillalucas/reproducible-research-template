"""Rojo a 98 mm: en su foco (red/) contra desenfocado (red_foco_green/, red_foco_blue/), misma geometría y campo.
C1 = error de predicción de LEDs no vistos (5 grupos, anillos < 7) y sin FPM; C2 = FRC entre mitades en [2NA/lambda, 0.45] 1/um.
Escribe criterios_foco.json (solo los sets terminados)."""
import glob, importlib.util, json, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
s = importlib.util.spec_from_file_location("F", os.path.join(HERE, "red", "fpm_red.py")); F = importlib.util.module_from_spec(s); s.loader.exec_module(F)
g = F.geometry(98.0); lo = 2 * 0.07 / 0.63; out = {}
for d in ("red", "red_foco_green", "red_foco_blue"):
    T = os.path.join(HERE, d, "out", "tasks"); O = os.path.join(HERE, d, "out")
    fs = sorted(glob.glob(f"{T}/real_A+init_z98.0_f[0-9].json"))
    if len(fs) < 5 or not os.path.exists(f"{O}/obj_real_A+init_z98.0_half1.npy"):
        continue
    c1 = np.mean([np.mean([v[0] for v in json.load(open(p))["per_led"].values() if v[2] < 7 and not v[3]]) for p in fs])
    nf = np.mean([v[0] for v in json.load(open(f"{T}/real_nofpm_z98.0.json"))["per_led"].values() if v[2] < 7])
    ld = lambda n: np.load(f"{O}/obj_real_A+init_z98.0_{n}.npy")
    fr = F.band_mean(F.frc(ld("half0"), ld("half1"), g["hrpx"]), lo, 0.45)
    out[d] = dict(C1_R=float(c1), C1_sin_fpm=float(nf), C2_mitades=float(fr))
    print(d, {k: round(v, 3) for k, v in out[d].items()})
json.dump(out, open(os.path.join(HERE, "criterios_foco.json"), "w"), indent=1)
