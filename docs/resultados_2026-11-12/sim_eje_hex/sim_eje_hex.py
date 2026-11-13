"""sim_eje_hex.py -- eje de la matriz desplazado y grilla hexagonal: conjuntos BF, ventanas de z y margen (12/11).
Uso: python sim_eje_hex.py [geo] [sim] [fig]   (sin argumentos corre todo).
Reutiliza SIN modificar ../sim_z/sim_z.py y ../sim_z_clave/sim_z_clave.py (modelo directo sin crimen inverso,
ruido, solver ePIE 20 epocas, metricas). Escribe geometria.json, runs.jsonl (una linea por corrida), tablas.md, figuras.
Semillas fijas (objetos 100/101, ruido 1000/1001).
"""
import json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "sim_z"))
sys.path.insert(0, os.path.join(HERE, "..", "sim_z_clave"))
import sim_z as S                                     # noqa: E402
import sim_z_clave as K                               # noqa: E402

T0 = time.time()
NA, P = S.NA, S.PITCH
IJ = [(i, j) for i in range(-7, 8) for j in range(-7, 8)]
H = np.sqrt(3) / 2


def posiciones(disp):
    """dict k -> (x, y) en mm de los 225 LEDs respecto del eje optico."""
    if disp == "a_sobre_LED":
        return {k: (k[1] * P, k[0] * P) for k in IJ}
    if disp == "b_medio_medio":
        return {k: ((k[1] + 0.5) * P, (k[0] + 0.5) * P) for k in IJ}
    if disp == "c_medio_0":
        return {k: ((k[1] + 0.5) * P, k[0] * P) for k in IJ}
    hexa = {k: ((k[1] + 0.5 * (k[0] % 2)) * P, k[0] * H * P) for k in IJ}
    if disp == "d_hex_sobre_LED":
        return hexa
    if disp == "e_hex_centroide":                     # eje en el centro de un triangulo de 3 LEDs
        return {k: (x - 0.5 * P, y - P * H / 3) for k, (x, y) in hexa.items()}
    if disp == "f_hex_arista":                        # eje en el punto medio entre 2 LEDs
        return {k: (x - 0.5 * P, y) for k, (x, y) in hexa.items()}
    raise ValueError(disp)


DISPS = ["a_sobre_LED", "b_medio_medio", "c_medio_0", "d_hex_sobre_LED", "e_hex_centroide", "f_hex_arista"]
ZS = np.arange(40.0, 262.01, 0.5)


def nas(xy, z):
    r = np.hypot(xy[:, 0], xy[:, 1])
    return r / np.sqrt(r * r + z * z)


def ventanas(xy):
    """Barrido de z: lista de ventanas (n_BF constante) con z de margen maximo, n DF y NA_syn."""
    rows = []
    for z in ZS:
        v = nas(xy, z)
        rows.append((float(z), int((v < NA).sum()), float(np.abs(v - NA).min())))
    out, i = [], 0
    while i < len(rows):
        j = i
        while j + 1 < len(rows) and rows[j + 1][1] == rows[i][1]:
            j += 1
        best = max(rows[i:j + 1], key=lambda r: r[2])
        ok = [r[0] for r in rows[i:j + 1] if r[2] >= 0.010]
        z = best[0]; v = nas(xy, z)
        ext = min(-xy[:, 0].min(), xy[:, 0].max(), -xy[:, 1].min(), xy[:, 1].max())
        out.append(dict(n_BF=rows[i][1], z_min=rows[i][0], z_max=rows[j][0], z_opt=z, margen_max=best[2],
                        z_ok010=[min(ok), max(ok)] if ok else None, n_DF=int((v >= NA).sum()),
                        NA_syn_lado_corto=float(NA + ext / np.hypot(ext, z)), NA_syn_max=float(NA + v.max()),
                        completa=bool(rows[i][0] > ZS[0] and rows[j][0] < ZS[-1])))
        i = j + 1
    return out, rows


def geo():
    out = {"nota": "z 40-262 mm paso 0.5; margen = min |NA_ilum - 0.070| sobre los 225 LEDs", "disposiciones": {}, "barrido": {}}
    for d in DISPS:
        xy = np.array(list(posiciones(d).values()))
        w, rows = ventanas(xy)
        out["disposiciones"][d] = w
        out["barrido"][d] = [[r[0], r[1], round(r[2], 5)] for r in rows]
    # barrido 2D del desplazamiento del eje en la grilla cuadrada (matriz rotada = mismo conjunto: la pupila es circular)
    best = {}
    base = np.array([(k[1] * P, k[0] * P) for k in IJ])
    for ox in np.arange(0, 0.501, 0.05):
        for oy in np.arange(0, ox + 1e-9, 0.05):
            w, _ = ventanas(base + np.array([ox, oy]) * P)
            for x in w:
                n = x["n_BF"]
                if n >= 3 and x["completa"] and x["margen_max"] > best.get(n, dict(margen_max=0))["margen_max"]:
                    best[n] = dict(ox=round(float(ox), 2), oy=round(float(oy), 2), z_opt=x["z_opt"], margen_max=x["margen_max"])
    out["mejor_desplazamiento_por_nBF"] = {str(n): best[n] for n in sorted(best)}
    json.dump(out, open(os.path.join(HERE, "geometria.json"), "w"), indent=1)
    return out


# ---------------- simulacion ----------------
CASOS = [("b_medio_medio", 4), ("b_medio_medio", 12), ("b_medio_medio", 16), ("d_hex_sobre_LED", 7), ("a_sobre_LED", 9),
         ("a_sobre_LED", 5), ("d_hex_sobre_LED", 19), ("e_hex_centroide", 3), ("e_hex_centroide", 12), ("c_medio_0", 6),
         ("a_sobre_LED", 1)]


def geom_xy(pos, z):
    g = {}
    for k, (x, y) in pos.items():
        d = np.sqrt(x * x + y * y + z * z)
        g[k] = (x / d / S.LAM, y / d / S.LAM, z / d)
    return g


def sim():
    G = json.load(open(os.path.join(HERE, "geometria.json")))["disposiciones"]
    objs = [S.make_object(0), S.make_object(1)]
    S.KEYS = IJ
    for d, n in CASOS:
        w = [x for x in G[d] if x["n_BF"] == n and x["z_opt"] >= 80.0]
        if not w:
            print("sin ventana", d, n); continue
        w = w[0]; z = w["z_opt"]
        if d == "a_sobre_LED" and n == 1:
            z = 80.0                                  # 1 BF: z minimo que entra en el espectro HR (margen 0.005, no optimo)
        g = geom_xy(posiciones(d), z)
        v = np.array([S.ill_na(g, k) for k in IJ])
        for io, (spec, truth, mask) in enumerate(objs):
            I = S.forward(spec, g)
            for s in range(2):
                In, ts = S.add_noise(I, g, z, np.random.default_rng(1000 + s))
                o = S.reconstruct(In, g, IJ)
                row = dict(disp=d, n_BF=int((v < NA).sum()), z=z, margen=float(np.abs(v - NA).min()), obj=io, seed=s,
                           NA_syn_lado_corto=w["NA_syn_lado_corto"], **S.metrics(o, truth, mask), **K.extra(o, truth),
                           t=round(time.time() - T0, 1))
                with open(os.path.join(HERE, "runs.jsonl"), "a") as f:
                    f.write(json.dumps(row) + "\n")
                print(d, row["n_BF"], z, io, s, round(row["err"], 4), round(row["e_c23"], 4), round(row["ph_esf"], 3), row["t"], flush=True)


# ---------------- tablas y figuras ----------------
def fig():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    G = json.load(open(os.path.join(HERE, "geometria.json")))
    L = ["# Tablas (generadas por sim_eje_hex.py fig)\n", "## Ventanas de z por disposicion (n BF >= 2, ventana completa dentro de 40-262 mm)\n",
         "| disposicion | n BF | ventana z (mm) | z opt | margen max | z con margen >= 0.010 | n DF | NA_syn lado corto | NA_syn max |", "|---|---|---|---|---|---|---|---|---|"]
    for d in DISPS:
        for x in G["disposiciones"][d]:
            if x["completa"] and x["n_BF"] >= 1:
                ok = "%.1f-%.1f" % tuple(x["z_ok010"]) if x["z_ok010"] else "ninguno"
                L.append(f"| {d} | {x['n_BF']} | {x['z_min']:.1f}-{x['z_max']:.1f} | {x['z_opt']:.1f} | {x['margen_max']:.4f} | {ok} | {x['n_DF']} | {x['NA_syn_lado_corto']:.3f} | {x['NA_syn_max']:.3f} |")
    L += ["\n## Mejor desplazamiento del eje (grilla cuadrada, paso 0.05 pitch) por n BF\n", "| n BF | (ox, oy) pitch | z opt | margen max |", "|---|---|---|---|"]
    for n, b in G["mejor_desplazamiento_por_nBF"].items():
        L.append(f"| {n} | ({b['ox']}, {b['oy']}) | {b['z_opt']:.1f} | {b['margen_max']:.4f} |")
    fg, ax = plt.subplots(3, 2, figsize=(12, 9), sharex=True, sharey=True)
    for a, d in zip(ax.ravel(), DISPS):
        b = np.array(G["barrido"][d])
        a.plot(b[:, 0], b[:, 2], color="#1f5fa8", lw=1.3)
        a.axhline(0.012, color="#b03030", ls="--", lw=0.8); a.axhline(0.007, color="gray", ls=":", lw=0.8)
        for x in G["disposiciones"][d]:
            if x["completa"] and x["margen_max"] > 0.0015:
                a.annotate(str(x["n_BF"]), (x["z_opt"], x["margen_max"]), ha="center", va="bottom", fontsize=8)
        a.set_title(d, fontsize=10); a.set_ylim(0, 0.04); a.grid(alpha=0.3)
    for a in ax[-1]: a.set_xlabel("z (mm)")
    for a in ax[:, 0]: a.set_ylabel("margen min |NA_ilum - NA_obj|")
    fg.suptitle("Margen al borde de pupila vs z (numero = n BF de la ventana; rojo 0.012 = referencia 5/9 BF; gris 0.007)")
    fg.tight_layout(); fg.savefig(os.path.join(HERE, "fig1_margen_vs_z.png"), dpi=110); plt.close(fg)
    p = os.path.join(HERE, "runs.jsonl")
    if os.path.exists(p):
        R = [json.loads(l) for l in open(p)]
        cs = []
        for r in R:
            c = (r["disp"], r["n_BF"], r["z"])
            if c not in cs: cs.append(c)
        cols = ["err", "e_c23", "frc_BF", "frc_bajo", "frc_medio", "frc_alto", "ph_esf"]
        L += ["\n## Simulacion (media +- desvio, 2 objetos x 2 semillas)\n",
              "| disposicion | n BF | z | margen | NA_syn lado corto | n | " + " | ".join(cols) + " |", "|---|---|---|---|---|---|" + "---|" * len(cols)]
        st = []
        for c in cs:
            rr = [r for r in R if (r["disp"], r["n_BF"], r["z"]) == c]
            m = {k: (np.mean([r[k] for r in rr]), np.std([r[k] for r in rr])) for k in cols}
            st.append((c, m, rr[0]["margen"]))
            L.append(f"| {c[0]} | {c[1]} | {c[2]:.1f} | {rr[0]['margen']:.4f} | {rr[0]['NA_syn_lado_corto']:.3f} | {len(rr)} | " +
                     " | ".join(f"{m[k][0]:.3f}±{m[k][1]:.3f}" for k in cols) + " |")
        fg, ax = plt.subplots(1, 3, figsize=(14, 4.5))
        lab = [f"{c[0][0]}:{c[1]}BF\nz{c[2]:.0f}" for c, _, _ in st]
        for a, k, t in zip(ax, ["e_c23", "ph_esf", "frc_alto"], ["error banda comun NA<0.23", "RMS fase en esferas (rad)", "FRC banda alta (NA 0.35-0.5)"]):
            a.bar(range(len(st)), [m[k][0] for _, m, _ in st], yerr=[m[k][1] for _, m, _ in st],
                  color=["#888888" if c[0][0] == "a" else "#1f5fa8" for c, _, _ in st], capsize=3)
            a.set_xticks(range(len(st))); a.set_xticklabels(lab, fontsize=7); a.set_title(t, fontsize=10); a.grid(axis="y", alpha=0.3)
        ax[0].set_yscale("log")
        fg.suptitle("Reconstruccion en el centro de cada ventana (gris: eje sobre un LED; azul: disposiciones nuevas; a=sobre LED, b=(1/2,1/2), c=(1/2,0), d=hex, e=hex centroide)", fontsize=9)
        fg.tight_layout(); fg.savefig(os.path.join(HERE, "fig2_calidad.png"), dpi=110); plt.close(fg)
    open(os.path.join(HERE, "tablas.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    todo = sys.argv[1:] or ["geo", "sim", "fig"]
    if "geo" in todo: geo()
    if "sim" in todo: sim()
    if "fig" in todo: fig()
