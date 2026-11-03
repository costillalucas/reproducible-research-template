"""Angulo relativo entre mitades A y B en funcion de k: theta(k) = arg sum_anillo F_A conj(F_B).
Paso 1 del plan 03/11 (Lucas). Desenfoque relativo dz entre mitades -> theta = -pi*lambda*dz*k^2 (+ const?).
Tambien por sectores angulares (8) para ver si depende de la direccion (corrimiento lateral -> fase lineal en k.d)."""
import numpy as np, json, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
R = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/"
CORR = {"real NA0.074": R+"plan_2026-11-03/red-c_na074/",
        "real NA0.0669": R+"2026-10-30-red-c/",
        "nulo DF": R+"plan_2026-11-03/red-c_nulo_df/"}
DX, LAM, M = 0.43, 0.63, 60
dk = 0.01; bordes = np.arange(0.02, 0.60 + dk, dk); kc = 0.5*(bordes[1:] + bordes[:-1])

def espectro(O):
    O = O / np.mean(O) - 1; O = O[M:-M, M:-M]
    n = O.shape[0]; w = np.hanning(n)[:, None]*np.hanning(n)[None, :]   # ventana: evita bordes
    return np.fft.fft2(O*w), np.fft.fftfreq(n, DX)

out = {}
fig, ax = plt.subplots(1, 3, figsize=(17, 5))
for nombre, d in CORR.items():
    FA, f = espectro(np.load(d+"objeto_mitadA.npy")); FB, _ = espectro(np.load(d+"objeto_mitadB.npy"))
    kx, ky = np.meshgrid(f, f); k = np.hypot(kx, ky); phi = np.arctan2(ky, kx)
    X = FA*np.conj(FB); th, frc, nring, sec = [], [], [], []
    for a, b in zip(bordes[:-1], bordes[1:]):
        m = (k >= a) & (k < b); s = X[m].sum()
        th.append(np.angle(s)); frc.append(abs(s)/np.sqrt((abs(FA[m])**2).sum()*(abs(FB[m])**2).sum())); nring.append(m.sum())
        # 4 sectores (sumando opuestos: phi y phi+pi juntos, porque el objeto es complejo -> no hay simetria hermitica; separo 8)
        sec.append([np.angle(X[m & (np.mod(phi - p0, 2*np.pi) < np.pi/4)].sum()) for p0 in np.arange(8)*np.pi/4])
    th, frc, sec = np.array(th), np.array(frc), np.array(sec)
    ruido = 3/np.sqrt(np.array(nring)/4)       # umbral ~3 sigma para correlacion aleatoria (aprox, ventana reduce n efectivo)
    ok = frc > ruido
    out[nombre] = {"k": kc.tolist(), "theta_deg": np.degrees(th).tolist(), "frc": frc.tolist(), "umbral3s": ruido.tolist(),
                   "sectores_deg": np.degrees(sec).tolist()}
    # ajuste theta = t0 + c k^2 en los anillos significativos (desenvuelto)
    if ok.sum() >= 4:
        tu = np.unwrap(th[ok]); A_ = np.c_[np.ones(ok.sum()), kc[ok]**2]
        (t0, c), *_ = np.linalg.lstsq(A_, tu, rcond=None)
        res = tu - A_ @ [t0, c]
        A1 = np.c_[np.ones(ok.sum()), kc[ok]]; p1, *_ = np.linalg.lstsq(A1, tu, rcond=None); res1 = tu - A1 @ p1
        out[nombre]["ajuste"] = {"t0_deg": float(np.degrees(t0)), "c_rad_um2": float(c), "dz_um": float(-c/(np.pi*LAM)),
                                 "rms_res_deg_k2": float(np.degrees(res.std())), "rms_res_deg_lineal": float(np.degrees(res1.std())),
                                 "n_anillos": int(ok.sum()), "k_rango": [float(kc[ok].min()), float(kc[ok].max())]}
    ax[0].plot(kc, frc, label=nombre); ax[0].plot(kc, ruido, "k:", lw=0.8)
    ax[1].plot(kc[ok], np.degrees(np.unwrap(th[ok])), "o-", ms=3, label=nombre)
    if nombre == "real NA0.074":
        for j in range(8): ax[2].plot(kc[ok], np.degrees(np.unwrap(sec[ok, j])), lw=0.8, label=f"sector {45*j}°")
for x in (0.0669/LAM, 2*0.0669/LAM): ax[0].axvline(x, c="gray", ls="--", lw=0.7); ax[1].axvline(x, c="gray", ls="--", lw=0.7)
ax[0].set(xlabel="k (1/µm)", ylabel="|correlación compleja A-B| por anillo", title="FRC complejo entre mitades (punteado: ~3σ azar)"); ax[0].legend()
ax[1].set(xlabel="k (1/µm)", ylabel="θ(k) = arg(A·B*) (°, desenvuelto)", title="Ángulo relativo entre mitades (solo anillos > 3σ)"); ax[1].legend()
ax[2].set(xlabel="k (1/µm)", ylabel="θ (°)", title="real NA0.074 por sector de dirección"); ax[2].legend(fontsize=7)
plt.tight_layout(); plt.savefig("fig_theta_k.png", dpi=90)
json.dump(out, open("theta_k.json", "w"), indent=1)
for n, v in out.items(): print(n, v.get("ajuste"))
