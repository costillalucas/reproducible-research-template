"""FRC entre mitades por banda de k, épocas 20/160/400 (03/11 rojo, 400 px, geometría B). k en 1/µm; NA equivalente = k·λ."""
import sys, json, numpy as np
sys.path.insert(0, "."); import comun_plan as C
D = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04/epocas_400b/"
PX, LAM, NA = 0.43, 0.63, 0.0669
B = [(0.0, 2*NA/LAM, "BF (≤2NA_obj)"), (2*NA/LAM, 0.45, "banda C2"), (0.45, 0.45/LAM, "C2→NA_syn eje"),
     (0.45/LAM, 0.573/LAM, "eje→esquina NA_syn"), (0.573/LAM, 1/(2*PX), "más allá de NA_syn")]
out = {}
for vent in (False, True):
    res = {}
    for ep in (20, 160, 400):
        h0, h1 = np.load(D + f"snapshots/objeto_mitad0_e{ep:03d}.npy"), np.load(D + f"snapshots/objeto_mitad1_e{ep:03d}.npy")
        fr = C.frc_fino(h0, h1, PX, ventana=vent); res[ep] = fr
    out["hann" if vent else "sin_ventana"] = {str(ep): res[ep].tolist() for ep in res}
    print(f"\n=== FRC {'con Hann' if vent else 'sin ventana'} (media por banda) ===")
    print(f"{'banda':22s} {'k [1/µm]':>13s} {'NA eq':>11s} {'ep20':>7s} {'ep160':>7s} {'ep400':>7s} {'Δ160→400':>9s}")
    for lo, hi, nom in B:
        m = {ep: float(np.mean(res[ep][(res[ep][:,0]>=lo)&(res[ep][:,0]<hi),1])) for ep in res}
        print(f"{nom:22s} {lo:5.2f}–{hi:5.2f}  {lo*LAM:4.2f}–{hi*LAM:4.2f} {m[20]:7.3f} {m[160]:7.3f} {m[400]:7.3f} {m[400]-m[160]:+9.3f}")
json.dump(out, open(D + "frc_bandas.json", "w"))
