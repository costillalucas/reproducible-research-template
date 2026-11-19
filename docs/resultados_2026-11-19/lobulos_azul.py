import glob, re, numpy as np, tifffile
R='/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-11-19.2048ms-grilla.a'
dk={}
for f in glob.glob(R+'-dark/fila*/*ms/*.tiff'):
    t=int(re.search(r'/(\d+)ms/',f).group(1)); dk.setdefault(t,[]).append(tifffile.imread(f).astype(float).mean())
dk={t:np.mean(v) for t,v in dk.items()}
M=np.full((33,33),np.nan)
for f in glob.glob(R+'/fila*/*ms/*.tiff'):
    m=re.search(r'fila(\d+)_col(\d+)_color.*/(\d+)ms/',f); r,c,t=map(int,m.groups())
    M[r,c]=(tifffile.imread(f).astype(float).mean()-dk[t])/t
np.set_printoptions(linewidth=250)
print('cuentas/ms medias (filas 9-25, col 7-23), x1000:')
print('      '+' '.join(f'{c:5d}' for c in range(7,24)))
for r in range(9,26): print(f'{r:4d}  '+' '.join(f'{1000*M[r,c]:5.0f}' for c in range(7,24)))
# perfiles por distancia a lo largo de filas (col 14-16) vs columnas (fila 16-18)
print('\npasos | a lo largo de FILAS (arriba/abajo, cols 14-16) | a lo largo de COLUMNAS (izq/der, filas 16-18)')
for k in range(2,9):
    fa=np.nanmean([M[17-k,14:17].mean(),M[17+k,14:17].mean()]) if 17+k<=25 else np.nanmean(M[17-k,14:17])
    co=np.nanmean([M[16:19,15-k].mean(),M[16:19,15+k].mean()])
    print(f'{k:5d} | {1000*fa:8.1f} | {1000*co:8.1f}   cociente {fa/co:5.2f}')
