import numpy as np, json, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
B="/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04/"
o4=np.load(B+"epocas_400b/snapshots/objeto_full_e160.npy"); on=np.load(B+"red_nulo_df/objeto_complejo.npy")
J=json.load(open("particulas.json"))["particulas"][:4]
fig,ax=plt.subplots(4,7,figsize=(21,12))
for i,p in enumerate(J):
    y,x=3*p["fila400"],3*p["col400"]; w=lambda o:o[y-30:y+30,x-30:x+30]
    r=np.load(f"runs/r20/{p['id']}.npz"); o2=r["obj"]; lr=r["lr_bf"]
    for j,(o,t) in enumerate([(w(o4),"400"),(o2,"20"),(w(on),"nulo400")]):
        b=o.mean(); z=o/b
        ax[i,1+2*j].imshow(np.abs(z),cmap="gray"); ax[i,1+2*j].set_title(p["id"]+" amp "+t)
        ax[i,2+2*j].imshow(np.angle(z),cmap="RdBu_r",vmin=-2.5,vmax=2.5); ax[i,2+2*j].set_title("fase "+t)
    ax[i,0].imshow(lr,cmap="gray"); ax[i,0].set_title("LR BF")
plt.tight_layout(); plt.savefig("datos/mirar.png",dpi=55)
