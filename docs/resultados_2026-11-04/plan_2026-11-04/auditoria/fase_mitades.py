"""Auditoría ítem 7b: ¿las mitades coinciden partícula a partícula en volumen de fase? (mismo método 20/10)."""
import json, numpy as np, importlib.util
REPO = "/home/chanoscopio/Documents/LucasC/reproducible-research-template"
spec = importlib.util.spec_from_file_location("analisis", REPO + "/results/rojo_fase_2026-10-20/analisis.py")
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)
R = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/2026-11-03-red_1311/"
ok = {}
for n in ("objeto_complejo", "objeto_mitadA", "objeto_mitadB"):
    rows, _ = A.particulas(np.load(R + n + ".npy").astype(complex), 0.43); ok[n] = A.tabla(rows)
out = {}
for a, b in [("objeto_mitadA", "objeto_mitadB"), ("objeto_complejo", "objeto_mitadA"), ("objeto_complejo", "objeto_mitadB")]:
    pr = A.emparejar(ok[a], ok[b], tol=2.0)
    va = np.array([p[0]["V"] for p in pr]); vb = np.array([p[1]["V"] for p in pr])
    pa = np.array([p[0]["phi"] for p in pr]); pb = np.array([p[1]["phi"] for p in pr])
    out[f"{a}~{b}"] = dict(N_pares=len(pr), N_a=len(ok[a]), N_b=len(ok[b]), pearson_V=float(np.corrcoef(va, vb)[0, 1]),
                           mediana_cociente_V=float(np.median(vb / va)), pearson_pico=float(np.corrcoef(pa, pb)[0, 1]),
                           mediana_cociente_pico=float(np.median(pb / pa)))
print(json.dumps(out, indent=1)); json.dump(out, open("fase_mitades.json", "w"), indent=1)
