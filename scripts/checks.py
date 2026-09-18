#!/usr/bin/env python3
"""checks.py -- the correctness suite for this project's claims.

Two kinds of check, same discipline as the template's worked example
(examples/pi_estimator/checks.py):
  - positive checks: things that MUST agree with the derivation.
  - a negative control: a case built to disagree on purpose, run through
    the identical check, which MUST be caught disagreeing -- proving the
    check is capable of failing, not just capable of passing. A suite with
    no negative control cannot be trusted when it passes.

These checks re-derive the same thresholds already asserted in
tests/test_multispectral_end_to_end.py, tests/test_led_calibration.py --
this script exists for the provenance report, the pytest files are the
development-time source of truth. See scripts/compute_numbers.py for how
the numbers themselves are computed.

Run: python scripts/checks.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))

results = []


def check(name, ok, detail=""):
    ok = bool(ok)
    results.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if detail:
        print(f"       {detail}")


with open(os.path.join(ROOT, "data", "numbers.json")) as fh:
    numbers = json.load(fh)

check(
    "multispectral pipeline recovers sample thickness shape (correlation > 0.5)",
    numbers["multispectral_thickness_correlation"]["value"] > 0.5,
    f"got {numbers['multispectral_thickness_correlation']['value']:.4f}",
)
check(
    "unwrapping+dispersion fit beats naive (k=0) baseline by at least 20x on a large dispersion signal",
    numbers["unwrapping_error_reduction_factor"]["value"] > 20,
    f"got {numbers['unwrapping_error_reduction_factor']['value']:.2f}x",
)
check(
    "LED spectral-correlation calibration recovers a known misalignment's scale within 0.01",
    numbers["led_calibration_scale_recovery_error"]["value"] < 0.01,
    f"got {numbers['led_calibration_scale_recovery_error']['value']:.5f}",
)
check(
    "TIE-informed solver initialization beats the default zero-phase start by at least 0.5 "
    "phase_correlation on a weak/mixed-frequency phase object",
    numbers["tie_informed_init_phase_correlation"]["value"]
    > numbers["tie_informed_init_baseline_phase_correlation"]["value"] + 0.5,
    f"baseline={numbers['tie_informed_init_baseline_phase_correlation']['value']:.4f}  "
    f"TIE-informed={numbers['tie_informed_init_phase_correlation']['value']:.4f}",
)

# Negative control: the SAME 30-point similarity-transform fit, with the SAME 10% of points
# corrupted, MUST have a much smaller rotation error under RANSAC than under plain least
# squares -- proving this check can catch the plain fit's known outlier sensitivity.
check(
    "NEGATIVE CONTROL: RANSAC recovers the true rotation far more accurately than plain "
    "least squares when 10% of calibration points are corrupted outliers",
    numbers["ransac_robust_fit_rotation_error_rad"]["value"]
    < numbers["ransac_plain_fit_rotation_error_rad"]["value"] / 10,
    f"plain={numbers['ransac_plain_fit_rotation_error_rad']['value']:.4f}rad  "
    f"RANSAC={numbers['ransac_robust_fit_rotation_error_rad']['value']:.6f}rad",
)

# Negative control: the SAME phase field, reconstructed with only 5% amplitude contrast
# instead of 0%, MUST score meaningfully higher -- proving this check is capable of
# catching the phase-only failure mode (docs/roadmap_agentic_multispectral_pipeline.md
# section 1 point 6), not just praising a working reconstruction.
check(
    "NEGATIVE CONTROL: uniform-amplitude (phase-only) object reconstructs far worse "
    "than the same phase field with 5% amplitude contrast",
    numbers["five_percent_contrast_object_phase_correlation"]["value"]
    > numbers["phase_only_object_phase_correlation"]["value"] + 0.5,
    f"uniform={numbers['phase_only_object_phase_correlation']['value']:.4f}  "
    f"5%_contrast={numbers['five_percent_contrast_object_phase_correlation']['value']:.4f}",
)

check(
    "EPRY pupil recovery (ou2014) meaningfully beats assuming the ideal pupil when a real "
    "defocus aberration is present",
    numbers["epry_corrected_phase_correlation"]["value"]
    > numbers["epry_uncorrected_phase_correlation"]["value"] + 0.05,
    f"uncorrected={numbers['epry_uncorrected_phase_correlation']['value']:.4f}  "
    f"EPRY={numbers['epry_corrected_phase_correlation']['value']:.4f}  "
    f"recovered_pupil_vs_true_aberration_correlation="
    f"{numbers['epry_recovered_pupil_phase_correlation']['value']:.4f}",
)

# Negative control: on this project's small synthetic testbed, EPRY MUST regress an
# already-healthy channel with no aberration present -- proving the checks suite can catch
# EPRY's own known failure mode (docs/roadmap_agentic_multispectral_pipeline.md milestone 8),
# not just praise the cases where it helps.
check(
    "NEGATIVE CONTROL: at this project's small (9x9 LED, 12x12px) testbed scale, EPRY "
    "regresses an already-well-converging channel even with no aberration present",
    numbers["epry_small_scale_corrected_phase_correlation"]["value"]
    < numbers["epry_small_scale_baseline_phase_correlation"]["value"] - 0.2,
    f"baseline={numbers['epry_small_scale_baseline_phase_correlation']['value']:.4f}  "
    f"EPRY={numbers['epry_small_scale_corrected_phase_correlation']['value']:.4f}",
)
check(
    "that small-testbed regression does NOT reproduce at a scale close to ou2014's own real "
    "demonstration (225 LEDs, 64x64px) -- confirms a testbed-scale artifact, not a general "
    "EPRY failure",
    abs(numbers["epry_paper_scale_corrected_phase_correlation"]["value"]
        - numbers["epry_paper_scale_baseline_phase_correlation"]["value"]) < 0.1,
    f"baseline={numbers['epry_paper_scale_baseline_phase_correlation']['value']:.4f}  "
    f"EPRY={numbers['epry_paper_scale_corrected_phase_correlation']['value']:.4f}",
)

check(
    "adaptive step size (zuo2016) beats the fixed exponential ramp under heavy Poisson noise "
    "and enough iterations for the paper's described failure mode to manifest",
    numbers["adaptive_step_adaptive_phase_correlation"]["value"]
    > numbers["adaptive_step_fixed_ramp_phase_correlation"]["value"] + 0.03,
    f"fixed_ramp={numbers['adaptive_step_fixed_ramp_phase_correlation']['value']:.4f}  "
    f"adaptive={numbers['adaptive_step_adaptive_phase_correlation']['value']:.4f}",
)

passed = sum(1 for _, ok in results if ok)
total = len(results)
print()
print("=" * 60)
print(f"COVERAGE: {passed}/{total} passed")
print("=" * 60)

with open(os.path.join(ROOT, "data", "checks_results.json"), "w") as fh:
    json.dump(
        {"results": [{"name": n, "passed": ok} for n, ok in results],
         "passed": passed, "total": total},
        fh, indent=2,
    )
    fh.write("\n")

sys.exit(0 if passed == total else 1)
