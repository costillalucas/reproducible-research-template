import json, numpy as np
OUT = "results/fase_2026-10-01/epocas/"
for c in ["red", "green", "blue"]:
    r = json.load(open(OUT + f"fase_epocas_{c}.json"))[c]; ep = r["ep"]
    print(f"== {c} px={r['px']:.4f} cand={r['ncand']} umbral={r['thr']:.2f}")
    print("ep  bgstd_rob bgstd_hp lf_bg sup_ptp frac>pi frac_wrap rel_ph rel_c")
    for e in ep:
        g = r["g"][str(e)]
        print(e, *[f"{g[k]:.3f}" if g[k] is not None else "-" for k in ["bgstd_rob","bgstd_hp","lf_bg_std","sup_ptp","frac_gt_pi","frac_wrap","rel_ph","rel_c"]])
    d = [p["d_um"] for p in r["parts"]]
    P = np.array([[r["p"][str(e)][i]["peak"] for e in ep] for i in range(len(d))])
    V = np.array([[r["p"][str(e)][i]["vol"] for e in ep] for i in range(len(d))])
    S = np.array([[r["p"][str(e)][i]["bgstd"] for e in ep] for i in range(len(d))])
    ix = {e: k for k, e in enumerate(ep)}
    print("d_um  peak@5 @40 @120 @400 | vol@5 @40 @120 @400 | ringstd@40 @400 | ep90_peak")
    for i in range(len(d)):
        p = P[i]; fin = p[-1]
        e90 = next((e for e in ep if all(abs(p[ix[x]] - fin) <= 0.1 * abs(fin) for x in ep if x >= e)), None)
        print(f"{d[i]:5.2f}", *[f"{P[i,ix[e]]:.2f}" for e in (5,40,120,400)], "|", *[f"{V[i,ix[e]]:.1f}" for e in (5,40,120,400)], "|", f"{S[i,ix[40]]:.2f} {S[i,ix[400]]:.2f}", "|", e90)
    for lo, hi in [(0, 3), (3, 6), (6, 99)]:
        m = (np.array(d) >= lo) & (np.array(d) < hi)
        if m.any():
            rp = (P[m, ix[400]] / P[m, ix[40]]).mean(); rv = (V[m, ix[400]] / V[m, ix[40]]).mean()
            rv2 = (V[m, ix[400]] / V[m, ix[120]]).mean()
            print(f"  d∈[{lo},{hi}) n={m.sum()} peak400/40={rp:.2f} vol400/40={rv:.2f} vol400/120={rv2:.2f}")
