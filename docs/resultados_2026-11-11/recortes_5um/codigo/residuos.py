#!/usr/bin/env python3
"""residuos.py -- ¿qué tan bien explica cada reconstrucción las 225 imágenes medidas DENTRO de la huella de 20 px de cada esfera?
R = sqrt( sum_k sum_px (pred_k - I_k)^2 / sum_k sum_px (I_k - <I_k>)^2 ), con pred_k = |IFFT(spec[ventana_k] · P)|^2 (el mismo
modelo directo que reconstruct_snap, s = 1, b = 0), sobre los píxeles no enmascarados; también separado BF / DF.
  * r400 y n400: modelo directo sobre el recorte de 400 px entero y recorte de la predicción a la huella; datos = I de load_real
    del prep de 400 px (lo que vio ese solver).
  * r20 / n20 / r20_sincambian: modelo directo de 20 px; datos = I de load_real del recorte de 20 px (lo que vio ese solver).
    Además r400 evaluado contra los datos del recorte de 20 px (r400_vs_datos20) para comparar sobre los mismos datos.
Ojo: R del 20 px es AJUSTE (datos de entrenamiento), no validación: un dominio chico puede ajustar mejor sin ser más correcto.
Salida: residuos.json."""
import json, os, sys
import numpy as np
sys.path.insert(0, "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-11/recortes_5um/codigo")
import recortes as RC  # noqa: E402  (limpia el entorno -> geometría B; carga el prep de 400)
RP = RC.RP
P0, B = RC.P0 + "/", "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04/"


def geo_y_datos(ruta, f0, c0, tam, nulo):
    F, IR = RP.cargar_solver("red", RP.FACTOR["red"])
    eje_x, eje_y = RP.ROI_CAL[0] + RP.ROI_CAL[2] / 2, RP.ROI_CAL[1] + RP.ROI_CAL[2] / 2
    off_y = (eje_y - (RC.ROI[1] + f0 + tam / 2)) * RP.MM_POR_PX
    off_x = (eje_x - (RC.ROI[0] + c0 + tam / 2)) * RP.MM_POR_PX
    geo = F.geometry(RP.Z_MM, offset_mm=(off_x, off_y), crop=tam)
    keys = [tuple(int(v) for v in k) for k in RC._D["keys"]]
    if nulo:
        fc = geo["na"] / geo["lam"]
        df = sorted(k for k in keys if np.hypot(*geo["fxy"][k]) >= fc)
        perm = np.random.default_rng(0).permutation(len(df))
        v = [geo["fxy"][df[i]] for i in perm]
        geo["fxy"].update({k: x for k, x in zip(df, v)})
    fr = np.hypot(*np.array([geo["fxy"][k] for k in keys]).T)
    F.BF = sorted([k for k, f in zip(keys, fr) if f < geo["na"] / geo["lam"]], key=lambda k: (k != RP.CENTRO_LED, k))
    D = F.load_real(ruta)
    return F, geo, D


def predecir(F, geo, obj, keys, n):
    P = F.circular_pupil((n, n), geo["lrpx"], geo["na"], geo["lam"]).astype(complex)
    spec = np.fft.fftshift(np.fft.fft2(obj))
    out = {}
    for k in keys:
        ys, xs = F.led_crop_window(spec.shape, geo["hrpx"], (n, n), *geo["fxy"][k])
        out[k] = np.abs(np.fft.ifft2(np.fft.ifftshift(spec[ys, xs] * P))) ** 2
    return out


def R(pred, D, keys, sl=(slice(None), slice(None)), solo=None):
    num = den = 0.0
    for k in keys:
        if solo is not None and (k in D["bf"]) != solo:
            continue
        m = D["mask"][k][sl]; I = D["I"][k][sl]; p = pred[k][sl]
        num += ((p - I)[m] ** 2).sum(); den += ((I - I[m].mean())[m] ** 2).sum()
    return float(np.sqrt(num / den))


def main():
    J = json.load(open(P0 + "particulas.json"))["particulas"]
    tmp = P0 + "runs/_prep400.npz"
    np.savez(tmp, **RC._D)
    full = {}
    for nom, f, nulo in (("r400", B + "epocas_400b/snapshots/objeto_full_e160.npy", False),
                         ("n400", B + "red_nulo_df/objeto_complejo.npy", True)):
        F, geo, D = geo_y_datos(tmp, 360, 80, 400, nulo)
        D["bf"] = set(F.BF)
        full[nom] = (predecir(F, geo, np.load(f).astype(complex), D["keys"], 400), D)
        print(nom, "predicho", flush=True)
    os.remove(tmp)
    out = []
    for p in J:
        y, x = p["fila400"], p["col400"]
        sl = (slice(y - 10, y + 10), slice(x - 10, x + 10))
        fila = dict(id=p["id"])
        for nom, (pred, D) in full.items():
            fila[nom] = R(pred, D, D["keys"], sl); fila[nom + "_BF"] = R(pred, D, D["keys"], sl, True)
            fila[nom + "_DF"] = R(pred, D, D["keys"], sl, False)
        ruta = P0 + f"runs/_prep_{p['id']}.npz"
        f0, c0 = RC.preparar(y, x, 20, ruta)
        for nom, carpeta, nulo in (("r20", "r20", False), ("n20", "r20_nulo", True), ("r20_sincambian", "r20_sincambian", False)):
            fz = P0 + f"runs/{carpeta}/{p['id']}.npz"
            if not os.path.exists(fz):
                continue
            F, geo, D = geo_y_datos(ruta, f0, c0, 20, nulo)
            D["bf"] = set(F.BF)
            keys = D["keys"]
            if nom == "r20_sincambian":
                keys = [k for k in keys if k not in {tuple(c) for c in np.load(fz)["cambian"]}]
            pred = predecir(F, geo, np.load(fz)["obj"].astype(complex), keys, 20)
            fila[nom] = R(pred, D, keys); fila[nom + "_BF"] = R(pred, D, keys, solo=True); fila[nom + "_DF"] = R(pred, D, keys, solo=False)
            if nom == "r20":   # r400 contra los datos del recorte de 20 px
                pr4 = {k: full["r400"][0][k][sl] for k in keys}
                fila["r400_vs_datos20"] = R(pr4, D, keys)
        os.remove(ruta)
        out.append(fila)
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in fila.items()}, flush=True)
    json.dump(out, open(P0 + "residuos.json", "w"), indent=1)


if __name__ == "__main__":
    main()
