"""vista_campo.py (21/10 tarde) -- vista del ROI entero (BF/flat, un DF) para elegir el recorte; figura al scratchpad (no se versiona)."""
import glob, numpy as np, tifffile as T, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, os
B=os.path.expanduser('~/Documents/AleYLu/imagenes_tomadas')
def m(d): return np.mean([T.imread(f).astype(float) for f in sorted(glob.glob(d+'/imagen_frame_*.tiff'))],0)
dk5=m(B+'/2026-10-21-dark/fila17_col15_colorr/5ms'); dk8=m(B+'/2026-10-21-dark/fila17_col15_colorr/8ms'); dk257=m(B+'/2026-10-21-dark/fila17_col18_colorr/257ms')
s=(m(B+'/2026-10-21.500/fila17_col15_colorr/8ms')-dk8)/7.8; f=(m(B+'/2026-10-21-sinmuestra/fila17_col15_colorr/5ms')-dk5)/4.8
s2=(m(B+'/2026-10-21.500/fila14_col15_colorr/257ms')-dk257)/256.8
print(s.shape, s.mean(), f.mean(), (s/f).mean())
fig,ax=plt.subplots(1,3,figsize=(21,7))
q=s/f; ax[0].imshow(q,cmap='gray',vmin=np.percentile(q,1),vmax=np.percentile(q,99.5)); ax[0].set_title('BF/flat')
ax[1].imshow(s2,cmap='magma',vmax=np.percentile(s2,99.5)); ax[1].set_title('DF (14,15)')
for a in ax[:2]:
  a.add_patch(plt.Rectangle((360,310),400,400,fill=False,ec='c')); a.set_xticks(range(0,1121,80)); a.set_yticks(range(0,1121,80)); a.grid(alpha=.3)
ax[2].imshow(f,cmap='gray'); 
plt.tight_layout(); plt.savefig('/tmp/claude-1000/-home-chanoscopio-Documents-LucasC-reproducible-research-template/60cb657e-df2c-418d-93d2-3317ece6f19e/scratchpad/look.png',dpi=60)
fig,ax=plt.subplots(1,1,figsize=(10,10))
ax.imshow(q[160:960,160:960],cmap='gray',vmin=np.percentile(q,1),vmax=np.percentile(q,99.5),extent=(160,960,960,160))
ax.set_xticks(range(160,961,40)); ax.set_yticks(range(160,961,40)); ax.grid(alpha=.4); ax.tick_params(labelsize=7)
plt.tight_layout(); plt.savefig('zoom.png',dpi=80)
