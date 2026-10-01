"""Tres figuras livianas para la slide de validación de la charla de 5 minutos (una por prueba). Solo datos reales y cálculos
que ya están en el repo. Correr desde la raíz del repo: python3 report/informe/make_fig_validacion.py [1 2 3]
(el paso previo `python3 report/informe/make_fig_validacion.py fold` reconstruye UN fold, ver 2).

1. fig_valid_1_simulacion.png: la simulación de results/captura_2026-09-24/synth_overlap/run.py (verde, 13×13 LEDs,
   objetivo 2,5×, recorte 128, sin ruido, 100 iteraciones, paso relativo 0,3, metrics.compare_to_ground_truth) a 75 y a
   100 mm. Control: primero se corre con la muestra de synth_overlap (Lena/Map) y se exige reproducir summary.json
   (0,995 / 0,867 / 0,973, los números del resumen). Después se cambia SOLO la muestra: amplitud skimage.data.camera en
   [0,1; 1] y fase skimage.data.moon en [0; 1,2 rad], el mismo escalado que lena_map_object(phase_max_rad=1,2) y la misma
   muestra que make_informe_figs.py. Con esa muestra: amplitud 0,997, fase 0,64 a 75 mm y 0,97 a 100 mm (distintos de
   los de Lena: la fase depende de la muestra).
2. fig_valid_2_prediccion.png: rojo, en su foco, matriz a 98 mm (results/captura_2026-09-28b/red). Criterio 1 = error de
   fotos no usadas con fpm_red.affine_residual (ajuste afín medida ≈ s·predicha + b; R = ||medida − ajuste|| / ||medida −
   media||; 0 = perfecto, 1 = no mejor que una constante), promediado sobre LEDs apartados de anillo < 7 (criterios_b.py).
   - LED mostrado: (16,19), campo oscuro, anillo 4,3, apartado en el fold 1; R = 0,484, cerca de la mediana de los 148
     LEDs apartados (no es el mejor). El objeto de ese fold no estaba guardado: `... fold` lo reconstruye igual que
     run.py (A+init, 40 épocas, paso 0,3, entrenando sin los LEDs del fold 1 de fpm_red.folds) y lo guarda en
     results/captura_2026-09-28b/red/out/obj_real_A+init_z98.0_f1.npy; el script comprueba que su R coincide con el de
     tasks/real_A+init_z98.0_f1.json.
   - "Sin reconstruir": la predicción desde el objeto inicial (initial_object fourier_avg), como la tarea nofpm de run.py.
   - Mapa 15×15: R de cada LED apartado (tasks/real_A+init_z98.0_f*.json, per_led), gris = campo claro (nunca apartado).
3. fig_valid_3_mitades.png: las dos reconstrucciones con la mitad de los LEDs (out/obj_real_A+init_z98.0_half{0,1}.npy),
   la curva FRC entre los objetos complejos (como criterios_b.py) y la del nulo (mitades con los LEDs mezclados, _scr) con fpm_red.frc; límite del objetivo 2NA/λ,
   umbral 0,143 y banda [2NA/λ, 0,45] 1/µm donde se promedia el criterio 2 (criterios_b.py). Reparto de LEDs entre mitades:
   run.half_tasks, (fila + columna) par o impar = tablero de ajedrez (intercalado).
"""
import importlib.util
import json
import os
import sys

import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

B = "results/captura_2026-09-28b/red"
OUT = "report/informe/img"
plt.rcParams.update({"font.size": 15, "axes.titlesize": 21})  # como fig_fase_2809b
LED, FOLD = (16, 19), 1


def panels3():  # ancho 1210 px como fig_fase_2809b (11 in a 110 dpi); alto justo para 3 cuadrados + rótulo
    g = 0.008; W = (1 - 0.02 - 2 * g) / 3; lado = W * 1210; HPX = round(lado + 8 + 42)
    fig = plt.figure(figsize=(11, HPX / 110))
    return fig, [fig.add_axes([0.01 + i * (W + g), 8 / HPX, W, lado / HPX]) for i in range(3)]


def F():
    sys.path.insert(0, B)
    s = importlib.util.spec_from_file_location("fpm_red_b", f"{B}/fpm_red.py"); m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m); return m


def fold_obj():
    Fm = F(); D = Fm.load_real(); geo = Fm.geometry(98.0); keys = D["keys"]
    test = Fm.folds(keys, 5)[FOLD]; train = [k for k in keys if k not in test]
    res = Fm.reconstruct({k: D["I"][k] for k in train}, train, geo, iterations=40, mask={k: D["mask"][k] for k in train},
                         init="fourier_avg")
    np.save(f"{B}/out/obj_real_A+init_z98.0_f{FOLD}.npy", res["object"].astype(np.complex64))
    print("guardado")


def fig1():
    # misma simulación que results/captura_2026-09-24/synth_overlap/run.py (verde, 13x13 LEDs, objetivo 2,5x, recorte 128,
    # sin ruido, 100 iteraciones, paso relativo 0,3), a 75 y a 100 mm; control con Lena, figura con cámara/luna
    sys.path.insert(0, "src")
    from ptyco_full_simulator import config, led_array, optics, forward_model, reconstruction, metrics
    from ptyco_full_simulator.test_objects import lena_map_object
    ref = {r["z_mm"]: r for r in json.load(open("results/captura_2026-09-24/synth_overlap/summary.json"))["runs"] if r["iterations"] == 100}
    import skimage.data as skd
    from PIL import Image as _I

    def camara_luna(H):  # misma receta que lena_map_object: amplitud en [0,1; 1], fase en [0; 1,2 rad], Lanczos a H x H
        rs = lambda a: (lambda x: (x - x.min()) / np.ptp(x))(np.asarray(_I.fromarray(a.astype(np.float32)).resize((H, H), _I.LANCZOS), float))
        return (0.1 + 0.9 * rs(skd.camera())) * np.exp(1j * 1.2 * rs(skd.moon()))
    R = {}
    for muestra in ("lena", "camara"):
      for z in (75.0, 100.0):
          s = config.default_setup("green", 13, objective="2_5x_na007", resolution_px=(128, 128), row_index_base=12,
                                   col_index_base=9, z_distance_mm=z, led_center_offset_mm=(0.0, 3.0))
          f = optics.upsampling_factor(s); hp = optics.actual_hr_pixel_size_um(s, f); lp = s.lr_pixel_size_um
          obj = lena_map_object((128 * f, 128 * f), phase_max_rad=1.2)[0] if muestra == "lena" else camara_luna(128 * f)
          grid = led_array.build_led_grid(s.led_array, s.wavelength_um)
          lr = forward_model.simulate_lr_stack(obj, hp, grid, (128, 128), lp, s.objective.na, s.wavelength_um)
          o = reconstruction.reconstruct(lr, grid, hp, lp, s.objective.na, s.wavelength_um, f, iterations=100,
                                         step_relative=0.3, normalize_initial_guess=True)["object"]
          cmp = metrics.compare_to_ground_truth(o, obj)
          print(muestra, z, cmp["amplitude_correlation"], cmp["phase_correlation"], "(summary lena:", ref[z]["amplitude_correlation"], ref[z]["phase_correlation"], ")")
          if muestra == "lena":  # control: con Lena se reproduce summary.json, así que solo cambia la muestra
              assert abs(cmp["phase_correlation"] - ref[z]["phase_correlation"]) < 1e-6 and abs(cmp["amplitude_correlation"] - ref[z]["amplitude_correlation"]) < 1e-6
              continue
          key = min(lr, key=lambda k: abs(k[0] - 17.5) + abs(k[1] - 15))
          R[z] = dict(obj=obj, rec=o * np.exp(-1j * np.angle(np.vdot(o, obj).conj())), photo=lr[key], cmp=cmp)
    a75, a100 = R[75.0], R[100.0]
    fig, ax = panels3()
    kw = dict(cmap="viridis", vmin=0, vmax=1.2)
    for a, im, tt in zip(ax, (np.angle(a75["obj"]), np.angle(a75["rec"]), np.angle(a100["rec"])), ("Verdad (fase)", "75 mm", "100 mm")):
        a.imshow(im, **kw); a.set_title(tt); a.axis("off")
    fig.savefig(f"{OUT}/fig_valid_1_simulacion.png", dpi=110); plt.close(fig)


def fig2():
    Fm = F(); D = Fm.load_real(); geo = Fm.geometry(98.0)
    o = np.load(f"{B}/out/obj_real_A+init_z98.0_f{FOLD}.npy").astype(complex)
    o0 = Fm.initial_object(D["I"], geo["factor"], "fourier_avg")
    meas = D["I"][LED]; p1 = Fm.predict(o, [LED], geo)[LED]; p0 = Fm.predict(o0, [LED], geo)[LED]
    r1 = Fm.affine_residual(p1, meas, D["V"][LED], D["mask"][LED])[0]; r0 = Fm.affine_residual(p0, meas, D["V"][LED], D["mask"][LED])[0]
    ref = json.load(open(f"{B}/out/tasks/real_A+init_z98.0_f{FOLD}.json"))["per_led"][f"{LED[0]},{LED[1]}"][0]
    ref0 = json.load(open(f"{B}/out/tasks/real_nofpm_z98.0.json"))["per_led"][f"{LED[0]},{LED[1]}"][0]
    print("R fold %.4f (tarea %.4f)  R sin reconstruir %.4f (tarea %.4f)" % (r1, ref, r0, ref0))
    assert abs(r1 - ref) < 0.02 and abs(r0 - ref0) < 0.02

    def fit(p):  # misma escala que la medida: el ajuste afín de affine_residual
        X = np.stack([p.ravel(), np.ones(p.size)], 1); c, *_ = np.linalg.lstsq(X, meas.ravel(), rcond=None)
        if c[0] < 0: c = np.array([0.0, meas.mean()])
        return (X @ c).reshape(p.shape)
    z = (slice(100, 300), slice(100, 300))
    lo, hi = np.percentile(meas[z], [0.5, 99.5])
    fig, ax = panels3()
    for a, im, tt in zip(ax, (meas, fit(p1), fit(p0)), ("Medida", "Predicha", "Sin reconstruir")):
        a.imshow(im[z], cmap="gray", vmin=lo, vmax=hi); a.set_title(tt); a.axis("off")
    fig.savefig(f"{OUT}/fig_valid_2_prediccion.png", dpi=110); plt.close(fig)


def fig3():
    Fm = F(); geo = Fm.geometry(98.0)
    ld = lambda n: np.load(f"{B}/out/obj_real_A+init_z98.0_{n}.npy")  # objeto complejo, como criterios_b.py
    fr = Fm.frc(ld("half0"), ld("half1"), geo["hrpx"]); fn = Fm.frc(ld("half0_scr"), ld("half1_scr"), geo["hrpx"])
    h0, h1 = np.abs(ld("half0")), np.abs(ld("half1"))
    lo = 2 * geo["na"] / geo["lam"]
    c2, c2n = Fm.band_mean(fr, lo, 0.45), Fm.band_mean(fn, lo, 0.45)
    print("C2 %.3f nulo %.3f" % (c2, c2n))
    z = (slice(450, 750), slice(450, 750))
    fig, ax = panels3(); ax[2].remove()
    for a, im, tt in zip(ax[:2], (h0, h1), ("Mitad A", "Mitad B")):
        l, h = np.percentile(im[z], [1, 99.5]); a.imshow(im[z], cmap="gray", vmin=l, vmax=h); a.set_title(tt); a.axis("off")
    HPX = fig.get_figheight() * 110; top = ax[0].get_position().y1
    c = fig.add_axes([0.72, 70 / HPX, 0.265, top - 70 / HPX])
    c.axvspan(lo, 0.45, color="#F6D9C6")
    c.plot(fr[:, 0], fr[:, 1], color="#2F6FB0", lw=2.5, label="A contra B")
    c.plot(fn[:, 0], fn[:, 1], color="0.5", lw=2, ls="--", label="nulo")
    c.axhline(0.143, color="#D9692B", lw=2, label="umbral")
    c.axvline(lo, color="k", lw=1.2)
    c.set_xlim(0, 0.8); c.set_ylim(0, 0.6); c.set_xlabel("frecuencia (1/µm)"); c.set_title("Coincidencia (FRC)")
    c.legend(fontsize=13, loc="upper right", frameon=False)
    fig.savefig(f"{OUT}/fig_valid_3_mitades.png", dpi=110); plt.close(fig)


pedidos = sys.argv[1:] or ["1", "2", "3"]
for k in pedidos:
    {"fold": fold_obj, "1": fig1, "2": fig2, "3": fig3}[k]()
    print("figura", k)
