"""chequeo_kernel.py -- el desenfoque de render_bloque (pupila corrida + exp(i2πd[kz(f+k)-kz(k)])) da la misma intensidad
que: inclinar el objeto con k EN LA GRILLA, propagar con angular_spectrum_propagate del repo (solo lectura) y filtrar con
la pupila centrada."""
import os, sys
os.environ['OMP_NUM_THREADS'] = '1'
sys.dont_write_bytecode = True
import numpy as np
sys.path.insert(0, '/home/chanoscopio/Documents/LucasC/reproducible-research-template/src')
from ptyco_full_simulator.propagation import angular_spectrum_propagate  # noqa: E402
import sim_eje_foco as S  # noqa: E402
obj, _ = S.objeto(0, 40)
n = obj.shape[0]
f = np.fft.fftfreq(n, d=S.FPX)
NA = 7.35 / 99.5
for dz in (0.0, 50.0, -100.0):
    for m in ((0, 0), (14, -9)):
        k = (m[0] / (n * S.FPX), m[1] / (n * S.FPX))   # k en la grilla
        S.DZ = dz
        I1 = S.render_bloque(np.fft.fft2(obj), n, k, NA, 0.0)
        yy, xx = np.mgrid[:n, :n] * S.FPX
        tilt = obj * np.exp(2j * np.pi * (k[0] * yy + k[1] * xx))
        E = angular_spectrum_propagate(tilt, dz, S.FPX, S.LAM)
        Fy, Fx = np.meshgrid(f, f, indexing='ij')
        E = np.fft.ifft2(np.fft.fft2(E) * (np.hypot(Fy, Fx) * S.LAM < NA))
        I2 = np.abs(E) ** 2
        print(f'dz {dz:+6.0f} k {m}: dif rel máx {np.abs(I1 - I2).max() / I2.mean():.2e}; contraste {I1.std() / I1.mean():.3f}')
