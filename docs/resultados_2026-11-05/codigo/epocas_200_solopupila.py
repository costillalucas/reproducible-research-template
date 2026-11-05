"""Curvas vs épocas (03/11 rojo, recorte 200 px): R train, C1 mitades, C2 (banda [0.212,0.45]), cruce 1/7 Hann, fase (pico/volumen)."""
import sys, json, csv, importlib.util, numpy as np
sys.path.insert(0, "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04/codigo"); import comun_plan as C
REPO = "/home/chanoscopio/Documents/LucasC/reproducible-research-template"
spec = importlib.util.spec_from_file_location("analisis", REPO + "/results/rojo_fase_2026-10-20/analisis.py")
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)
D = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04/epocas_200_solopupila/snapshots/"
PX, LAM, NA, DN = 0.43, 0.63, 0.0715, 0.046
rd = lambda f: {int(r["epoca"]): r for r in csv.DictReader(open(D + f))}
full, m0, m1 = rd("metricas_full.csv"), rd("metricas_mitad0.csv"), rd("metricas_mitad1.csv")
out = []
for ep in sorted(full):
    h0, h1 = np.load(D + f"objeto_mitad0_e{ep:03d}.npy"), np.load(D + f"objeto_mitad1_e{ep:03d}.npy")
    o = np.load(D + f"objeto_full_e{ep:03d}.npy").astype(complex)
    fr = C.frc_fino(h0, h1, PX); k = C.cruce(fr, k0=2 * NA / LAM)
    rows, info = A.particulas(o, PX); ok = A.tabla(rows)
    V = np.array([x["V"] for x in ok]); pk = np.array([x["phi"] for x in ok])
    dv = A.dvol(V, DN) / 1.0499; dp = pk * LAM / (2 * np.pi * DN)
    out.append(dict(ep=ep, R_train=float(full[ep]["R_ajuste"]), err=float(full[ep]["error_solver"]),
                    C1=(float(m0[ep]["R_heldout_C1"]) + float(m1[ep]["R_heldout_C1"])) / 2,
                    C1_A=float(m0[ep]["R_heldout_C1"]), C1_B=float(m1[ep]["R_heldout_C1"]),
                    C2=C.c2(h0, h1, PX, NA, LAM), C2_bandaB=C.c2(h0, h1, PX, 0.0669, 0.63), k_cruce=k, N=len(ok),
                    pico_med=float(np.median(pk)), V_med=float(np.median(V)),
                    d_vol=float(np.median(dv)), d_pico=float(np.median(dp)),
                    d_pico_sobre_d_vol=float(np.median(dp / dv))))
json.dump(out, open(D + "../curvas.json", "w"), indent=1)
print(f"{'ep':>4} {'Rtr':>6} {'C1':>6} {'C1A':>6} {'C1B':>6} {'C2':>6} {'kx':>6} {'N':>3} {'pico':>5} {'Vmed':>6} {'dvol':>5} {'dpico':>5} {'dp/dv':>5}")
for r in out:
    print(f"{r['ep']:>4} {r['R_train']:6.3f} {r['C1']:6.3f} {r['C1_A']:6.3f} {r['C1_B']:6.3f} {r['C2']:6.3f} {(r['k_cruce'] or 0):6.3f} {r['N']:>3} {r['pico_med']:5.2f} {r['V_med']:6.1f} {r['d_vol']:5.2f} {r['d_pico']:5.2f} {r['d_pico_sobre_d_vol']:5.2f}")
