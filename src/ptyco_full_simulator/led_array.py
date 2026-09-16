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
    dx = (col - cfg.center_index) * cfg.pitch_mm
    dy = (row - cfg.center_index) * cfg.pitch_mm
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
    lo = cfg.index_base
    hi = cfg.index_base + cfg.grid_size - 1
    for row in range(lo, hi + 1):
        for col in range(lo, hi + 1):
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
    lo = cfg.index_base
    hi = cfg.index_base + cfg.grid_size - 1
    corner_dx, corner_dy = led_position_mm(hi, hi, cfg)
    distance = np.sqrt(corner_dx**2 + corner_dy**2 + cfg.z_distance_mm**2)
    return float(np.hypot(corner_dx, corner_dy) / distance)
