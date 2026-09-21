"""Multi-seed sweep behind the noise caveat in docs/roadmap_agentic_multispectral_pipeline.md
milestone 11: Wirtinger flow (200 epochs) vs Adam gradient descent (100
iterations), paired by seed, 3 channels x peak photon counts (100, 20, 5) x
8 seeds. Run from the repo root: python3 scripts/sweep_gd_vs_wf_noise.py out.json
(~5 min on 4 cores). Not part of the provenance pipeline (reproduce.sh)."""
import os
os.environ["OMP_NUM_THREADS"]="1"; os.environ["OPENBLAS_NUM_THREADS"]="1"; os.environ["MKL_NUM_THREADS"]="1"
import sys, json, numpy as np
from multiprocessing import Pool
sys.path.insert(0,"src"); sys.path.insert(0,"tests")
from ptyco_full_simulator import config, forward_model, led_array, metrics, optics, reconstruction, joint_calibration as jc
from test_joint_calibration import _synthetic_object
CROP=16
# (result key, loss, iterations); the first is the original sweep's GD
VARIANTS=[("gd","intensity",100),("gd_amp","amplitude",100),("gd_poisson","poisson",100),("gd_poisson30","poisson",30)]
def job(a):
    ch,peak,seed=a
    setup=config.default_setup(channel=ch,grid_size=9,objective="current",resolution_px=(CROP,CROP))
    factor=optics.upsampling_factor(setup); hp=optics.actual_hr_pixel_size_um(setup,factor); hs=optics.hr_shape((CROP,CROP),factor)
    truth=_synthetic_object(hs); dk=1/(hs[1]*hp)
    grid=[{**e,"fx":round(e["fx"]/dk)*dk,"fy":round(e["fy"]/dk)*dk} for e in led_array.build_led_grid(setup.led_array,setup.wavelength_um)]
    lp,na,wl=setup.lr_pixel_size_um,setup.objective.na,setup.wavelength_um
    raw=forward_model.simulate_lr_stack(truth,hp,grid,(CROP,CROP),lp,na,wl,peak_photon_count=peak,rng=np.random.default_rng(seed))
    wf=reconstruction.reconstruct(raw,grid,hp,lp,na,wl,factor,iterations=200)["object"]
    scale=(hs[0]*hs[1])/(CROP*CROP); meas={k:v/scale**2 for k,v in raw.items()}
    init=jc.initial_object_from_center_led(meas[(grid[0]["row"],grid[0]["col"])],hs)
    f=lambda o:metrics.compare_to_ground_truth(o,truth)["phase_correlation"]
    out={"ch":ch,"peak":peak,"seed":seed,"wf":f(wf)}
    for name,loss,iters in VARIANTS:
        gd=jc.reconstruct_and_calibrate(meas,grid,hs,hp,(CROP,CROP),lp,na,wl,init,n_iterations=iters,calibrate_leds=False,loss=loss)["object"]
        out[name]=f(gd)
    return out
if __name__=="__main__":
    jobs=[(c,p,s) for c in ("green","red","blue") for p in (100,20,5) for s in range(8)]
    with Pool(os.cpu_count()) as pool: res=pool.map(job,jobs,chunksize=1)
    json.dump(res,open(sys.argv[1],"w"))
