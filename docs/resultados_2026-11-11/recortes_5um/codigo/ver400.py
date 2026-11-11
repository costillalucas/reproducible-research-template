import numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
B="/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04/"
d=np.load(B+"epocas_400b/datos/prep.npz"); keys=[tuple(k) for k in d["keys"]]; i=keys.index((17,15))
q=d["S"][i].astype(float)/d["F"][i].astype(float); np.save("datos/q_bf400.npy",q)
fig,ax=plt.subplots(figsize=(13,13)); ax.imshow(q,cmap="gray",vmin=0.4,vmax=1.2)
ax.set_xticks(range(0,400,20)); ax.set_yticks(range(0,400,20)); ax.grid(alpha=.35); ax.tick_params(labelsize=7)
ax.add_patch(plt.Rectangle((99.5,99.5),200,200,fill=False,ec="y"))
plt.tight_layout(); plt.savefig("datos/ver400.png",dpi=60)
