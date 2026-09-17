# ptyco-full-simulator

A multispectral (RGB) Fourier Ptychographic Microscopy pipeline: forward
model + Wirtinger flow reconstruction per channel
(`src/ptyco_full_simulator/`), registered onto one shared HR grid, coupled
via multi-wavelength phase unwrapping and a Cauchy dispersion fit, and
orchestrated by two Claude Code agents (reconstruction retry/accept, and
QC/confidence review). Full design and status:
`docs/roadmap_agentic_multispectral_pipeline.md`.

## Milestone 2: coupled multispectral reconstruction

On a synthetic 3-channel dispersion object, reconstructed through the
actual forward model and Wirtinger flow solver (not injected phase), the
milestone-2 coupled pipeline (shared HR grid → independent per-channel
reconstruction → piston removal → synthetic-wavelength unwrapping →
Cauchy dispersion fit) recovers the sample's thickness field with
correlation [srcnum:multispectral_thickness_correlation:0.88] to the true
field [src:multispectral_thickness_correlation].

On a larger, synthetic dispersion signal specifically constructed to
require real multi-wavelength unwrapping, the coupled pipeline's thickness
error is [srcnum:unwrapping_error_reduction_factor:183]x smaller than a
naive baseline that treats each channel's raw wrapped phase as
already-unwrapped optical path length [src:unwrapping_error_reduction_factor]
— evidence that the unwrapping/dispersion-fit step (milestone 2b) is
worth having, not just a coupling exercise.

## A real limitation of the baseline solver

The baseline Wirtinger flow reconstructor is far more sensitive to
amplitude contrast than previously documented: a uniform-amplitude (pure
phase) object reconstructs with phase correlation
[srcnum:phase_only_object_phase_correlation:-0.04]
[src:phase_only_object_phase_correlation] — worse than random — while the
identical phase field with just 5% amplitude contrast added reconstructs
with correlation [srcnum:five_percent_contrast_object_phase_correlation:0.65]
[src:five_percent_contrast_object_phase_correlation]. This matters because
this project's target samples (near-transparent biological specimens) are
exactly in the low-contrast regime where this baseline is weakest — see
`docs/roadmap_agentic_multispectral_pipeline.md` section 1, point 6.

## Milestone 4: LED position self-calibration

Given a good object-spectrum estimate, the spectral-correlation LED
calibration (adapted from `eckert2018`) recovers a known injected
misalignment's scale factor to within
[srcnum:led_calibration_scale_recovery_error:0.0015]
[src:led_calibration_scale_recovery_error] of the true value — the core
calibration math works. It does **not**, however, reliably rescue a
reconstruction that is already badly corrupted by an uncorrected
misalignment (see `tests/test_led_calibration.py`'s documented negative
result) — the paper's own brightfield pre-calibration bootstrap stage,
not implemented here, is a real prerequisite for this to help on real
data, not an optional extra.

## Correctness suite

[src:suite_coverage] — see `data/checks_results.json` for the full
pass/fail breakdown, including the negative control proving the
phase-only-object finding above is real (the check would fail if 5%
contrast did *not* score meaningfully better than uniform amplitude).
