"""detectar.py -- (paso 2) partículas aisladas en las reconstrucciones A (recortes de 200 px crudos) para los recortes B.

Cambio respecto del plan: la segmentación de octubre (umbral de FASE desenvuelta, results/rojo_fase_2026-10-20/analisis.py;
ver detectar_v1_fase_octubre.py) encuentra solo 6 objetos en el recorte por defecto y casi ninguno de los puntos oscuros que
se ven en la imagen cruda: en esta toma las partículas reconstruyen con amplitud ~0 en el centro (vórtices de fase) y la
fase desenvuelta no es confiable. Se detecta entonces por desvío complejo D = |o/fondo − 1| (detec_comun.py) y se usan
varios recortes A de 200 px (el por defecto + los 4 cuadrantes del recorte de 400 px del 18/11) porque uno solo no tiene
15 partículas aisladas.

Criterios de 'aislada': grupo (centro + anillos dilatados 3 µm) con D_max >= 0.3, extensión <= 15 µm, elongación <= 1.7,
y NINGÚN otro grupo con D_max >= 0.2 con algún píxel dentro de la ventana B20 (20 px crudos = 25.8 µm) centrada en la
partícula; la ventana B20 dentro del recorte A con >= 10 px crudos de margen. Si la partícula aparece en varios A, se queda
con el A donde está más lejos del borde.

Uso: python3 detectar.py <OUT>   -> OUT/seleccion.json, OUT/fig_seleccion.png
"""
import glob, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detec_comun as DC  # noqa: E402
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt  # noqa: E402

OUT = sys.argv[1]
NMAX = int(os.environ.get("NMAX", 15))
EXT_MAX = float(os.environ.get("EXT_MAX", 15)); EL_MAX = float(os.environ.get("EL_MAX", 1.7))
cands, todas, As = [], [], {}
for dA in sorted(glob.glob(os.path.join(OUT, "A_200*"))):
    if not os.path.isdir(dA) or not os.path.exists(os.path.join(dA, "objeto_complejo.npy")): continue
    met = json.load(open(os.path.join(dA, "datos", "metricas.json")))
    f0, c0, n = met["recorte"]; hr = met["hrpx"]
    o = np.load(os.path.join(dA, "objeto_complejo.npy")); fac = o.shape[0] // n
    G, info, D, gl = DC.grupos(o, hr, 0)
    nomA = os.path.basename(dA)
    As[nomA] = dict(recorte=[f0, c0, n], fac=fac, hr=hr, info=info, C1=float(np.mean(list(met["heldout"].values()))))
    print(f"{nomA}: recorte {f0},{c0} ({n}); {len(G)} grupos; umbral {info['thr']:.3f}")
    for g in G:
        g["A"] = nomA; g["fil_roi"] = f0 + g["cy"] / fac; g["col_roi"] = c0 + g["cx"] / fac
        todas.append(g)
    for g in G:
        mot = []
        if g["Dmax"] < 0.3: mot.append("D_max < 0.3")
        if g["ext"] > EXT_MAX: mot.append(f"ext {g['ext']:.1f} µm")
        if g["elong"] > EL_MAX: mot.append(f"elong {g['elong']:.2f}")
        rb, cb = int(round(g["fil_roi"] - 10)), int(round(g["col_roi"] - 10))
        if not (f0 + 10 <= rb and rb + 20 <= f0 + n - 10 and c0 + 10 <= cb and cb + 20 <= c0 + n - 10):
            mot.append("B20 fuera del interior de A")
        else:
            i0, j0 = (rb - f0) * fac, (cb - c0) * fac
            win = gl[i0:i0 + 20 * fac, j0:j0 + 20 * fac]
            otros = [h for h in G if h["k"] != g["k"] and h["Dmax"] >= 0.2 and (win == h["k"]).any()]
            if otros: mot.append(f"{len(otros)} vecino(s) en la ventana B20")
        g["motivo"] = mot
        g["margen_borde_px"] = float(min(g["fil_roi"] - f0, f0 + n - g["fil_roi"], g["col_roi"] - c0, c0 + n - g["col_roi"]))
        if not mot: cands.append(g)
cands.sort(key=lambda g: -g["margen_borde_px"])
unicas = []
for g in cands:
    if all(np.hypot(g["fil_roi"] - u["fil_roi"], g["col_roi"] - u["col_roi"]) > 5 for u in unicas):
        unicas.append(g)
print(f"candidatas aisladas únicas: {len(unicas)}")
for g in sorted(unicas, key=lambda g: (g["fil_roi"], g["col_roi"])):
    print(f"  {g['A']:16s} ROI ({g['fil_roi']:6.1f},{g['col_roi']:6.1f}) ext {g['ext']:5.1f} d_eq {g['d_eq']:5.1f} el {g['elong']:.2f} "
          f"Dmax {g['Dmax']:.2f} ncomp {g['n_comp']} margen {g['margen_borde_px']:.0f}")
# orden: primero las que ya tienen su B20 reconstruido (para no descartar corridas hechas), después por D_max
hecha = lambda g: os.path.exists(os.path.join(OUT, "B20", "f%d_c%d" % (round(g["fil_roi"] - 10), round(g["col_roi"] - 10)), "resumen.txt"))
unicas.sort(key=lambda g: (not hecha(g), -g["Dmax"]))
eleg = sorted(unicas[:NMAX], key=lambda g: (g["fil_roi"], g["col_roi"]))
out = []
for i, g in enumerate(eleg, 1):
    d = dict(id=f"P{i:02d}", A=g["A"], fil_roi=g["fil_roi"], col_roi=g["col_roi"], ext=g["ext"], d_eq=g["d_eq"], elong=g["elong"],
             Dmax=g["Dmax"], n_comp=g["n_comp"], margen_borde_px=g["margen_borde_px"])
    f0, c0, n = As[g["A"]]["recorte"]
    for t in (20, 40):
        d[f"rec{t}"] = [int(round(g["fil_roi"] - t / 2)), int(round(g["col_roi"] - t / 2))]
    rr, cc = d["rec40"]; d["B40_dentro_de_A"] = bool(f0 <= rr and rr + 40 <= f0 + n and c0 <= cc and cc + 40 <= c0 + n)
    out.append(d)
json.dump(dict(As=As, criterios=dict(EXT_MAX=EXT_MAX, EL_MAX=EL_MAX, Dmax_min=0.3, vecino_Dmax=0.2, nota="ver docstring de detectar.py"), elegidas=out, todas=todas),
          open(os.path.join(OUT, "seleccion.json"), "w"), indent=1, default=float)
fig, ax = plt.subplots(figsize=(11, 11))
orden = sorted(As, key=lambda k: k == "A_200")          # el por defecto encima
for nomA in orden:
    f0, c0, n = As[nomA]["recorte"]
    o = np.load(os.path.join(OUT, nomA, "objeto_complejo.npy"))
    ax.imshow(np.abs(o), cmap="gray", extent=(c0, c0 + n, f0 + n, f0), vmin=0.4, vmax=1.0)
for nomA in orden:
    f0, c0, n = As[nomA]["recorte"]
    col = "c" if nomA == "A_200" else "y"
    ax.add_patch(plt.Rectangle((c0, f0), n, n, fill=False, ec=col, lw=1.5 if nomA == "A_200" else 0.8))
    ax.text(c0 + 2, f0 + 6, nomA, color=col, fontsize=8)
for g in todas:
    if g["Dmax"] >= 0.3:
        ax.plot(g["col_roi"], g["fil_roi"], "x", color="0.5", ms=4)
for d in out:
    rr, cc = d["rec20"]
    ax.add_patch(plt.Rectangle((cc, rr), 20, 20, fill=False, ec="r", lw=1.2))
    ax.text(cc + 21, rr + 5, f"{d['id']} ({d['A'].replace('A_200', 'A')})", color="r", fontsize=8, weight="bold")
ax.set_xlim(370, 790); ax.set_ylim(735, 315)
ax.set_title("Recortes A (200 px; cian = por defecto, encima; amarillo = cuadrantes) y ventanas B20 elegidas (rojo). "
             "Ejes en px del ROI.\nx gris = objetos con D_max >= 0.3. Fondo = amplitud |o| de cada A.", fontsize=9)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_seleccion.png"), dpi=100)
print("elegidas:", [(d["id"], d["A"], d["rec20"], round(d["Dmax"], 2)) for d in out])
