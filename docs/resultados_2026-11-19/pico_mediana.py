import sys, numpy as np
DX=0.43
def esp(a):
    n=a.shape[0]; w=np.outer(np.hanning(n),np.hanning(n))
    F=np.abs(np.fft.fftshift(np.fft.fft2(w*(a-a.mean()))))
    f=np.fft.fftshift(np.fft.fftfreq(n,DX)); FX,FY=np.meshgrid(f,f); return F,np.hypot(FX,FY)
for nom,d in [('21x21','/home/chanoscopio/Documents/AleYLu/reconstrucciones/2026-11-18/red500/recon'),('19x19','/home/chanoscopio/Documents/AleYLu/reconstrucciones/2026-11-19/barrido_lado/lado19')]:
    for arch in ('objeto_complejo.npy','objeto_mitadA.npy'):
        o=np.load(f'{d}/{arch}'); F,fr=esp(np.abs(o)); m=(fr>.35)&(fr<.75)
        pk=F[m].max(); med=np.median(F[m])
        # mediana en sub-bandas
        sb=[np.median(F[(fr>a)&(fr<b)]) for a,b in ((.35,.45),(.55,.65),(.67,.75))]
        print(f'{nom} {arch:20s} pico {pk:9.1f}  mediana {med:7.2f}  cociente {pk/med:6.1f}   mediana .35-.45 {sb[0]:6.2f} .55-.65 {sb[1]:6.2f} .67-.75 {sb[2]:6.2f}')
