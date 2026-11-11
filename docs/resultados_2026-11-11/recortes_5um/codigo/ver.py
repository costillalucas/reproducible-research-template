import numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
B="/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04/"
d=np.load(B+"epocas_200/datos/prep.npz"); keys=[tuple(k) for k in d["keys"]]; i=keys.index((17,15))
S,F=d["S"][i].astype(float),d["F"][i].astype(float); q=S/F
np.save("datos/q_bf.npy",q)
o=np.load(B+"epocas_200/snapshots/objeto_full_e160.npy")
print(S.shape,o.shape,q.mean(),q.std(), d["S"].shape, list(d.keys()))
fig,ax=plt.subplots(1,3,figsize=(21,7))
ax[0].imshow(q,cmap="gray");ax[0].set_title("BF/flat")
ax[1].imshow(np.abs(o),cmap="gray");ax[1].set_title("amp e160")
ph=np.angle(o*np.exp(-1j*np.angle(o.mean())));ax[2].imshow(ph,cmap="twilight")
for a in ax: a.set_xticks(range(0,a.get_images()[0].get_array().shape[1],20 if a is ax[0] else 60)); a.grid(alpha=.3)
plt.tight_layout();plt.savefig("datos/ver.png",dpi=70)
