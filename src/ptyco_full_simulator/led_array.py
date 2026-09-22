"""led_array.py -- LED grid geometry: (row, col) -> illumination spatial
frequency (fx, fy), in cycles/micron, at the sample plane.

Uses exact direction cosines (dx/distance, dy/distance), not the
paraxial small-angle approximation -- at 31x31 LEDs and 6mm pitch the
outermost LEDs sit past 45 degrees off-axis, where tan(theta) noticeably
overstates sin(theta).
"""
from __future__ import annotations

import numpy as np

from .config import LEDArrayConfig


def led_position_mm(row: int, col: int, cfg: LEDArrayConfig) -> tuple[float, float]:
    """Lateral (x, y) offset of LED (row, col) from the on-axis LED, in mm."""
    dx = (col - cfg.center_col) * cfg.pitch_mm
    dy = (row - cfg.center_row) * cfg.pitch_mm
    return dx, dy


def illumination_spatial_freq(row: int, col: int, cfg: LEDArrayConfig,
                               wavelength_um: float) -> tuple[float, float]:
    """(fx, fy) in cycles/micron that this LED's plane wave adds to the
    object's spectrum, i.e. the shift applied when cropping the object's
    Fourier transform to simulate/reconstruct this LED's low-res image.
    """
    dx_mm, dy_mm = led_position_mm(row, col, cfg)
    distance_mm = np.sqrt(dx_mm**2 + dy_mm**2 + cfg.z_distance_mm**2)
    sin_x = dx_mm / distance_mm
    sin_y = dy_mm / distance_mm
    fx = sin_x / wavelength_um
    fy = sin_y / wavelength_um
    return fx, fy


def build_led_grid(cfg: LEDArrayConfig, wavelength_um: float) -> list[dict]:
    """Every (row, col) in the grid with its position and spatial frequency,
    ordered by distance from the center LED (matches how a real raster/
    spiral scan is usually processed: center first, most information
    first) -- reconstruction quality after N images is more meaningful
    that way.
    """
    entries = []
    row_lo, row_hi = cfg.row_base, cfg.row_base + cfg.grid_size - 1
    col_lo, col_hi = cfg.col_base, cfg.col_base + cfg.grid_size - 1
    for row in range(row_lo, row_hi + 1):
        for col in range(col_lo, col_hi + 1):
            fx, fy = illumination_spatial_freq(row, col, cfg, wavelength_um)
            dx, dy = led_position_mm(row, col, cfg)
            entries.append({
                "row": row, "col": col, "fx": fx, "fy": fy,
                "radial_mm": float(np.hypot(dx, dy)),
            })
    entries.sort(key=lambda e: e["radial_mm"])
    return entries


def max_illumination_na(cfg: LEDArrayConfig) -> float:
    """sin(theta) of the array's outermost LED -- the largest illumination
    angle actually available, used to size the synthetic-aperture NA.
    """
    row_hi = cfg.row_base + cfg.grid_size - 1
    col_hi = cfg.col_base + cfg.grid_size - 1
    corner_dx, corner_dy = led_position_mm(row_hi, col_hi, cfg)
    distance = np.sqrt(corner_dx**2 + corner_dy**2 + cfg.z_distance_mm**2)
    return float(np.hypot(corner_dx, corner_dy) / distance)


def adjacent_led_overlap_ratio(cfg: LEDArrayConfig, wavelength_um: float, na: float) -> float:
    """Fraction of the pupil's own area (radius na/wavelength_um in
    cycles/um) shared between two NEAREST-NEIGHBOR LEDs' sub-aperture
    circles in Fourier space -- the standard FPM design quantity
    (`eckert2018`'s introduction: "requires at least 35% overlap between
    adjacent angles of illumination [...] providing significant
    redundancy in the dataset", citing it as the widely-used minimum for
    phase retrieval to work at all).

    Found empirically while investigating why reconstruction quality
    jumps sharply at a specific `LEDArrayConfig.z_distance_mm` for a
    fixed objective/grid (2026-09-17, see
    docs/roadmap_agentic_multispectral_pipeline.md): the jump lands
    almost exactly at this ratio crossing 35%, on this project's own
    simulator -- a solver-independent confirmation that this simulator
    reproduces a real, well-known ptychography constraint, not a
    solver-specific quirk.

    Standard two-equal-circles overlap-area formula: for circles of
    radius R separated by center distance d < 2R,
    area = 2*R^2*acos(d/2R) - (d/2)*sqrt(4R^2 - d^2); returned as a
    fraction of one circle's own area (pi*R^2). Returns 0.0 if the
    circles don't overlap at all (d >= 2R) -- e.g. a synthetic aperture
    scan with big enough LED spacing to have gaps, not full coverage.
    """
    grid = build_led_grid(cfg, wavelength_um)
    center = grid[0]  # on-axis, radial_mm == 0.0 by construction (build_led_grid sorts by it)
    neighbor = grid[1]  # nearest ring of LEDs to the center, by radial_mm
    d = np.hypot(neighbor["fx"] - center["fx"], neighbor["fy"] - center["fy"])
    radius = na / wavelength_um
    if d >= 2 * radius:
        return 0.0
    area = 2 * radius**2 * np.arccos(d / (2 * radius)) - (d / 2) * np.sqrt(4 * radius**2 - d**2)
    return float(area / (np.pi * radius**2))
