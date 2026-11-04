"""Diseño 2 (Lucas 04/11): BF central (17,15) en ambas mitades; cruz 2:2 ((16,15),(18,15) -> 0; (17,14),(17,16) -> 1);
DF: por clase de distancia al LED (17,15) (misma |Δ|), ordenados por azimut y asignados 0,1,1,0 -> equilibrado por anillo y dirección."""
import json, math, collections
part = {(17, 15): 2, (16, 15): 0, (18, 15): 0, (17, 14): 1, (17, 16): 1}
clases = collections.defaultdict(list)
for r in range(10, 25):
    for c in range(8, 23):
        if (r, c) in part: continue
        clases[round(math.hypot(r - 17, c - 15), 6)].append((r, c))
for d, ks in sorted(clases.items()):
    ks.sort(key=lambda k: math.atan2(k[0] - 17, k[1] - 15))
    for i, k in enumerate(ks): part[k] = (0, 1, 1, 0)[i % 4]   # cada mitad cubre x e y, y una diagonal mixta (fila 18) cada una
out = {f"{k[0]},{k[1]}": h for k, h in part.items()}
json.dump(out, open("/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04/particion2/particion.json", "w"), indent=0)
cnt = collections.Counter(part.values()); print("conteo", dict(cnt))
print("diagonales anillo 1:", {k: part[k] for k in [(16, 14), (16, 16), (18, 14), (18, 16)]})
for d, ks in sorted(clases.items())[:6]: print(round(d, 3), [(k, part[k]) for k in ks])
