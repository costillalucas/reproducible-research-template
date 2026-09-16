"""ptyco_full_simulator -- Fourier Ptychographic Microscopy (FPM)
simulation and reconstruction.

Modules:
  config           physical/geometric setup (LED array, objective, sensor)
  led_array        LED grid geometry -> illumination spatial frequency
  optics           pupil function, HR/LR pixel sizes, upsampling factor
  spectral_ops     the HR-spectrum crop window shared by forward + inverse
  forward_model    simulate a LR image stack from a known HR complex object
  reconstruction   ptychographic Wirtinger flow HR reconstruction
  metrics          ground-truth comparison / convergence diagnostics
  io_utils         load reference images and real lab TIFF captures

See pipelines/simulate_and_reconstruct.py and
pipelines/reconstruct_real_images.py for the two runnable entry points,
and references/bibliography.yaml's `priority_focus` for the ranked list
of algorithm improvements (pupil recovery, LED self-calibration, adaptive
step size, ...) not yet implemented on top of the Wirtinger flow baseline.
"""
