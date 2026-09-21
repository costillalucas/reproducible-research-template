"""test_objects.py -- complex test objects built from real photographs
instead of the synthetic blob phantom, so solver comparisons aren't limited
to one smooth, low-detail object.

`lena_map_object` follows the lab's convention: Lena is the amplitude and
the aerial-photo "Map" is the phase (both 512x512 8-bit grayscale, kept
outside the repo in `DEFAULT_DATA_DIR`; pass `data_dir` or set
PTYCO_DATA_SOURCE to point elsewhere).
"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image

DEFAULT_DATA_DIR = "/home/chanoscopio/Documents/LucasC/code/data_source"


def _load_resized(path: str, shape: tuple[int, int]) -> np.ndarray:
    img = Image.open(path).convert("L").resize((shape[1], shape[0]), Image.LANCZOS)
    return np.asarray(img, dtype=float) / 255.0


def lena_map_object(hr_shape: tuple[int, int], phase_max_rad: float = 0.3 * np.pi,
                    min_amplitude: float = 0.1, data_dir: str | None = None
                    ) -> tuple[np.ndarray, np.ndarray]:
    """Returns (complex object, phase array). Amplitude = Lena rescaled to
    [min_amplitude, 1] (a floor above 0 -- a pixel with zero amplitude has
    no phase to recover); phase = Map rescaled to [0, phase_max_rad].
    Images are Lanczos-resampled to `hr_shape`, so a small HR canvas keeps
    only the coarse structure.
    """
    data_dir = data_dir or os.environ.get("PTYCO_DATA_SOURCE", DEFAULT_DATA_DIR)
    lena = _load_resized(os.path.join(data_dir, "Lena_512.png"), hr_shape)
    mp = _load_resized(os.path.join(data_dir, "Map_512.tiff"), hr_shape)
    amp = min_amplitude + (1 - min_amplitude) * (lena - lena.min()) / max(np.ptp(lena), 1e-12)
    phase = phase_max_rad * (mp - mp.min()) / max(np.ptp(mp), 1e-12)
    return amp * np.exp(1j * phase), phase
