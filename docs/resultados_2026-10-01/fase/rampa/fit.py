import numpy as np, sys
from skimage.restoration import unwrap_phase
d="results/iteraciones_2026-09-30/out/b_red/real_A+init_z98.0_full/"
hrpx=1.28/3
for e in sys.argv[1:]:
    o=np.load(d+f"obj_e{e}.npy"); N=o.shape[0]
    # spectrum peak offset (direct estimate of shift)
    F=np.fft.fftshift(np.fft.fft2(o)); p=np.unravel_index(np.argmax(abs(F)),F.shape)
    ph=unwrap_phase(np.angle(o)); m=8; ph=ph[m:-m,m:-m]
    y,x=np.mgrid[:ph.shape[0],:ph.shape[1]]*hrpx; x=x-x.mean(); y=y-y.mean()
    A=np.c_[np.ones(x.size),x.ravel(),y.ravel()]
    c,*_=np.linalg.lstsq(A,ph.ravel(),rcond=None); r=ph.ravel()-A@c
    A2=np.c_[A,x.ravel()**2,y.ravel()**2,(x*y).ravel()]
    c2,*_=np.linalg.lstsq(A2,ph.ravel(),rcond=None); r2=ph.ravel()-A2@c2
    print(e,N,"peak",(p[0]-N//2,p[1]-N//2),"slope rad/um x,y",c[1:].round(4),"ptp",np.ptp(A@c).round(2),
      "resid lin",r.std().round(3),"quad",r2.std().round(3),"quad coefs",c2[3:].round(6),"quad ptp",np.ptp(A2[:,3:]@c2[3:]).round(2))
    dk=np.hypot(*c[1:])/(2*np.pi); ds=0.63*dk
    print("   dk cyc/um",dk.round(5),"bins(1/512um)",(c[1:]/(2*np.pi)*N*hrpx).round(2),"dsin",ds.round(5),"dx@98mm mm",(98*ds).round(3))
