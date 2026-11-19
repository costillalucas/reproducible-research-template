import numpy as np, runpy, io, contextlib
with contextlib.redirect_stdout(io.StringIO()): g=runpy.run_path('lobulos_1um.py')
M=g['M']
print('paso  arriba(fila 17-k)  abajo(fila 17+k)   [máx de cols 13–18, x1000]   ref col dir (filas 16-18, col 15±k)')
for k in range(2,15):
    up=np.nanmax(M[17-k,13:19]) if 17-k>=3 else np.nan; dn=np.nanmax(M[17+k,13:19]) if 17+k<=31 else np.nan
    co=np.nanmean([M[16:19,15-k].mean(), M[16:19,15+k].mean()]) if 15+k<=29 and 15-k>=1 else np.nan
    print(f'{k:4d}  {1000*up:9.1f}  {1000*dn:9.1f}   {1000*co:9.1f}')
