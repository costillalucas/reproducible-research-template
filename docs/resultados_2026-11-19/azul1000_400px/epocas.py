import numpy as np, glob, csv, re, sys
D='/home/chanoscopio/Documents/AleYLu/reconstrucciones/2026-11-19/azul1000_lado400'; DX=0.258
def pico(o):
    a=np.abs(o); n=a.shape[0]; w=np.outer(np.hanning(n),np.hanning(n))
    F=np.abs(np.fft.fftshift(np.fft.fft2(w*(a-a.mean())))); f=np.fft.fftshift(np.fft.fftfreq(n,DX)); FX,FY=np.meshgrid(f,f); fr=np.hypot(FX,FY)
    m=(fr>0.8)&(fr<1.3); i=np.argmax(np.where(m,F,0)); return fr.flat[i], F.flat[i]/np.median(F[m])
for N in (29,27,25,23,21):
    s=f'{D}/lado{N}/snapshots'
    rd=lambda t:{int(r['epoca']):r for r in csv.DictReader(open(f'{s}/metricas_{t}.csv'))}
    full,mA,mB=rd('full'),rd('mitad0'),rd('mitad1')
    print(f'--- {N}x{N}:  época | R_ajuste | C1 (A,B prom) | error solver | pico completa f (pico/med) | mitad A f | mitad B f')
    for e in sorted(full):
        out=[]
        for t in ('full','mitad0','mitad1'):
            p=glob.glob(f'{s}/objeto_{t}_e{e:03d}.npy'); out.append(pico(np.load(p[0])) if p else (np.nan,np.nan))
        c1=(float(mA[e]['R_heldout_C1'])+float(mB[e]['R_heldout_C1']))/2 if e in mA else np.nan
        print(f'{e:5d} | {float(full[e]["R_ajuste"]):.4f} | {c1:.4f} | {float(full[e]["error_solver"]):.5f} | {out[0][0]:.3f} ({out[0][1]:5.0f}) | {out[1][0]:.3f} ({out[1][1]:4.0f}) | {out[2][0]:.3f} ({out[2][1]:4.0f})')
