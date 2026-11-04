"""Auditoría ítems 1-3 y 7: números de geometría y física recalculados (sin el solver)."""
import numpy as np, json
lam, p = 0.63, 6.0
out = {}
for na in (0.0669, 0.070, 0.072, 0.074):
    out[f"NA{na}"] = dict(coh_periodo_um=lam / na, nyq_int_um=lam / (4 * na), nyq_campo_lr_um=lam / (2 * na))
for z in (102.0, 97.4):
    for na in (0.0669, 0.072, 0.074):
        ax = 7 * p / np.hypot(7 * p, z); co = 7 * np.sqrt(2) * p / np.hypot(7 * np.sqrt(2) * p, z)
        out[f"z{z}_NA{na}"] = dict(sin_eje=ax, sin_esq=co, NAsyn_eje=ax + na, NAsyn_esq=co + na,
                                   nyq_campo_eje_um=lam / (2 * (ax + na)), nyq_campo_esq_um=lam / (2 * (co + na)),
                                   borde_BF_mm=z * np.tan(np.arcsin(na)))
# física de la esfera
for dn in (0.0488, 0.046, 0.05):
    out[f"dn{dn}"] = dict(pico_5um=2 * np.pi * dn * 5 / lam, V_5um=2 * np.pi * dn / lam * np.pi / 6 * 125,
                          d_pi_um=lam / (2 * dn))
nm = 1.477
for na in (0.0669, 0.27, 0.30, 0.45, 0.573):
    out[f"DOF_NA{na}"] = dict(lam_NA2_aire_um=lam / na ** 2, n_lam_NA2_medio_um=nm * lam / na ** 2,
                              ancho_kz_inv_um=1 / (nm / lam - np.sqrt((nm / lam) ** 2 - (na / lam) ** 2)))
# ángulo dentro de DMSO / vidrio para el LED de esquina (z 102)
s = 0.5034
out["angulos_esquina"] = dict(sin_aire=s, sin_vidrio_1p52=s / 1.52, sin_DMSO=s / nm, k_transversal_um=s / lam)
# corrimiento de z efectivo por 1 mm de portaobjetos (paraxial): z_ef = z_aire + t/n
out["z_ef_por_1mm_vidrio_mm"] = -(1 - 1 / 1.52)
print(json.dumps(out, indent=1)); json.dump(out, open("numeros.json", "w"), indent=1)
