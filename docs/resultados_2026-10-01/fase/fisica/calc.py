import numpy as np
lam={'R':0.630,'G':0.530,'B':0.470}; ndmso={'R':1.477,'G':1.485,'B':1.492}
pix={'R':0.4267,'G':0.256,'B':0.256}
Bn=0.006; An=1.525-Bn/0.5893**2   # nylon Cauchy anchored n_d=1.525, B=0.006 (Abbe~45)
NAo,NAs=0.07,0.48
for c,l in lam.items():
    nn=An+Bn/l**2; dn=nn-ndmso[c]; dn_sim=0.045+0.0015/l**2
    k=2*np.pi*dn/l
    print(c,f"n_nylon={nn:.4f} dn={dn:.4f} dn_sim={dn_sim:.4f} k={k:.3f} rad/um tpi={np.pi/k:.2f} t2pi={2*np.pi/k:.2f}",
      "phi(D)=",[round(k*D,2) for D in (1,2,5,8,10)], "phi(D) dn=0.05:",[round(2*np.pi*0.05*D/l,2) for D in (1,2,5,8,10)])
    gpix=np.pi/pix[c]; gband=2*np.pi*NAs/l
    for g,nm in((gpix,'pix'),(gband,'band')):
        u=g/(2*k); f=u/np.sqrt(1+u*u); print(f"   {nm}: gmax={g:.2f} rad/um frac r/R={f:.4f}")
    print(f"   DOF obj={l/NAo**2:.0f} um syn={l/NAs**2:.2f} um ; R where edge-pixel step>pi: {(np.pi/(2*k))**2/(2*pix[c]):.1f} um")
for c in 'GB':
    kR=2*np.pi*(An+Bn/0.63**2-1.477)/0.63
    print(c,'/R ratio')
