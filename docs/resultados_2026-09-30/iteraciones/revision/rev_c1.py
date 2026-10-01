"""Revisión independiente: C1, train, brecha, por anillo, por LED, desde metrics.jsonl."""
import json, os, glob, sys
import numpy as np
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(H, "out")
REF = os.path.join(H, "..", "captura_2026-09-28b")
CM = {"b_red": "red", "b_green": "green", "b_blue": "blue"}
def rd(ds, t):
    p = glob.glob(f"{OUT}/{ds}/real_A+init_z98.0_{t}/metrics.jsonl")[0]
    return {L["epoch"]: L for L in map(json.loads, open(p))}
res = {}
for ds, c in CM.items():
    F = [rd(ds, f"f{i}") for i in range(5)]
    eps = sorted(F[0])
    # held-out sets disjoint? union?
    hs = [set(k for k, v in f[0]["per_led"].items() if not v[3] and v[2] < 7) for f in F]
    inter = max(len(hs[i] & hs[j]) for i in range(5) for j in range(i+1, 5))
    trs = [set(k for k, v in f[0]["per_led"].items() if v[3]) for f in F]
    jacc = np.mean([len(trs[i] & trs[j]) / len(trs[i] | trs[j]) for i in range(5) for j in range(i+1, 5)])
    print(f"\n== {c}: heldout sizes {[len(h) for h in hs]}, max overlap {inter}, train Jaccard mean {jacc:.3f}")
    C1 = np.array([[np.mean([v[0] for v in f[e]["per_led"].values() if not v[3] and v[2] < 7]) for e in eps] for f in F])
    chk = np.array([[f[e]["heldout_R_ring_lt7"] for e in eps] for f in F])
    print("  max |mi C1 - heldout_R_ring_lt7|", np.abs(C1 - chk).max())
    TR = np.array([[f[e]["train_R"] for e in eps] for f in F])
    m, s, s1 = C1.mean(0), C1.std(0), C1.std(0, ddof=1)
    i40 = eps.index(40)
    print("  ep   C1    sd0   sd1   train  gap   d(e-40) mean sd  n_folds_e<40")
    for j, e in enumerate(eps):
        d = C1[:, j] - C1[:, i40]
        print(f"  {e:3d} {m[j]:.3f} {s[j]:.3f} {s1[j]:.3f} {TR[:,j].mean():.3f} {m[j]-TR[:,j].mean():.3f}  {d.mean():+.4f} {d.std():.4f} {d.std(ddof=1):.4f} {np.sum(d<0)}")
    print("  argmin C1:", eps[int(np.argmin(m))], round(m.min(), 4))
    # LED-level paired 5 vs 40 (each heldout LED appears in one fold)
    for ea in (5, 8, 400):
        rows = []
        for f in F:
            for k, v in f[ea]["per_led"].items():
                if not v[3] and v[2] < 7:
                    rows.append((k, v[2], v[0] - f[40]["per_led"][k][0], v[1], f[40]["per_led"][k][0]))
        d = np.array([r[2] for r in rows]); rg = np.array([r[1] for r in rows])
        rng = np.random.default_rng(0)
        bs = [rng.choice(d, d.size).mean() for _ in range(5000)]
        print(f"  LED-level R({ea})-R(40): n={d.size} mean {d.mean():+.4f} boot95 [{np.percentile(bs,2.5):+.4f},{np.percentile(bs,97.5):+.4f}] frac<0 {np.mean(d<0):.2f}")
        for lo, hi in [(0, 1.3), (1.3, 2.5), (2.5, 4), (4, 5.5), (5.5, 7)]:
            mm = (rg >= lo) & (rg < hi)
            if mm.any():
                print(f"     ring [{lo},{hi}) n={mm.sum():3d} mean {d[mm].mean():+.4f} sum-contrib {d[mm].sum()/d.size:+.4f} frac<0 {np.mean(d[mm]<0):.2f}")
        if ea == 5:
            o = np.argsort(d)[:8]
            print("     most-improved-at-5 LEDs:", [(rows[i][0], round(rows[i][1], 1), round(rows[i][2], 3), round(rows[i][4], 3), round(rows[i][3], 3)) for i in o])
    # BF LEDs train R in full
    full = rd(ds, "full")
    for e in (5, 40, 120, 400):
        bf = [v[0] for v in full[e]["per_led"].values() if v[2] < 1.3]
        print(f"  full e{e}: BF R mean {np.mean(bf):.3f} (n={len(bf)}) solver_err {full[e]['solver_err']} lattice {full[e]['lattice']:.5f} train_R {full[e]['train_R']:.3f}")
    print("  lattice max over eps (full):", max(full[e]["lattice"] for e in eps))
    nf = json.load(open(f"{REF}/{c}/out/tasks/real_nofpm_z98.0.json"))["per_led"]
    print("  nofpm C1 (ring<7):", round(np.mean([v[0] for v in nf.values() if v[2] < 7]), 4))
    # oficial 40 ref
    off = [np.mean([v[0] for v in json.load(open(p))["per_led"].values() if v[2] < 7 and not v[3]]) for p in sorted(glob.glob(f"{REF}/{c}/out/tasks/real_A+init_z98.0_f[0-9].json"))]
    print("  oficial C1 40:", round(np.mean(off), 6), "mine:", round(m[i40], 6), "sd0", round(np.std(off), 4))
    res[c] = dict(eps=eps, C1=C1.tolist(), TR=TR.tolist())
json.dump(res, open(os.path.join(H, "revision", "rev_c1.json"), "w"))
