import glob, re, numpy as np, tifffile
R='/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-11-19.2048ms.grilla.b-1000'
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
print('      '+' '.join(f'{c:5d}' for c in range(1,30)))
for r in range(3,32): print(f'{r:4d}  '+' '.join(f'{1000*M[r,c]:5.0f}' for c in range(1,30)))
# brillo medio por anillo y por dirección (8 sectores) para 9-14 pasos
ang=lambda r,c: (np.degrees(np.arctan2(-(r-17),c-15)))%180
print('\nsector (orientación del vector de red, 0°=columnas/horizontal, 90°=filas/vertical), media DF x1000 a 9–14 pasos y a 4–7 pasos:')
for a0 in range(0,180,15):
    v=[M[r,c] for r in range(3,32) for c in range(1,30) if 9<=np.hypot(r-17,c-15)<=14 and abs(((ang(r,c)-a0+90)%180)-90)<7.5]
    w=[M[r,c] for r in range(3,32) for c in range(1,30) if 4<=np.hypot(r-17,c-15)<=7 and abs(((ang(r,c)-a0+90)%180)-90)<7.5]
    print(f'{a0:4d}°  9–14: {1000*np.nanmean(v):7.1f}   4–7: {1000*np.nanmean(w):7.1f}')
