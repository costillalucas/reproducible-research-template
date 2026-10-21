"""qc_frames.py (21/10 tarde) -- QC de los 2 frames por LED, en el recorte de r500 (filas 140:540, columnas 560:960):
(1) pares con medias que difieren > 5 % (muestra .500, muestra de la mañana y flat); (2) var(f1-f2) frente a la esperada por ruido
(ganancia del ajuste fotónico) y correlación f1-f2 en algunos LEDs: descarta movimiento de la muestra entre frames (~0.3 s)."""
import glob, os, numpy as np, tifffile as T
B=os.path.expanduser('~/Documents/AleYLu/imagenes_tomadas')
for SM in (B+'/2026-10-21.500',B+'/2026-10-21',B+'/2026-10-21-sinmuestra'):
  bad=[]
  for d in sorted(glob.glob(SM+'/fila*_colorr/*ms')):
    a,b=[T.imread(f)[140:540,560:960].astype(float)-188 for f in sorted(glob.glob(d+'/imagen_frame_*.tiff'))]
    r=a.mean()/b.mean()
    if abs(r-1)>0.05: bad.append((d.split('/')[-2][:-7],d.split('/')[-1],round(a.mean(),1),round(b.mean(),1)))
  print(os.path.basename(SM),len(bad),bad[:12])
import glob, os, numpy as np, tifffile as T, json
B=os.path.expanduser('~/Documents/AleYLu/imagenes_tomadas')
CY,CX=slice(140,540),slice(560,960)
def fr(d): return [T.imread(f)[CY,CX].astype(float) for f in sorted(glob.glob(d+'/imagen_frame_*.tiff'))]
dk={t:np.mean(fr(glob.glob(f'{B}/2026-10-21-dark/*/{t}ms')[0]),0) for t in (8,128,257)}
for SM,g in ((B+'/2026-10-21.500',0.282),(B+'/2026-10-21',0.19)):
  print(SM)
  for k in [(17,15),(16,16),(15,15),(14,15),(17,11),(13,13),(11,15)]:
    d=glob.glob(f'{SM}/fila{k[0]}_col{k[1]}_colorr/*ms')[0]; t=int(os.path.basename(d)[:-2])
    if t not in dk: dk[t]=np.mean(fr(glob.glob(f'{B}/2026-10-21-dark/*/{t}ms')[0]),0)
    a,b=fr(d); a-=dk[t]; b-=dk[t]; m=(a+b)/2; df=a-b
    vexp=2*(g*np.clip(m,0,None)+13.4)
    mad=(1.4826*np.median(np.abs(df-np.median(df))))**2
    # high-signal pixels
    hs=m>np.percentile(m,99)
    print(k,t,'mean %.1f'%m.mean(),'var(f1-f2)/exp %.2f'%(df.var()/vexp.mean()),'MAD/exp %.2f'%(mad/vexp.mean()),'top1%% var/exp %.2f'%(df[hs].var()/vexp[hs].mean()),
          'corr f1,f2 %.3f'%np.corrcoef(a.ravel(),b.ravel())[0,1])
