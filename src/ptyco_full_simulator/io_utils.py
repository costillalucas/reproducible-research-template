"""io_utils.py -- load the two kinds of input this project consumes.

1. A synthetic HR complex object for script 1 (simulate_and_reconstruct),
   built from two ordinary images: one for amplitude, one for phase.
2. A real captured LR stack for script 2 (reconstruct_real_images), TIFFs
   named fila<R>_columna<C>.tiff (the lab's own raster-scan convention).

Real capture layout (the lab's own convention):
<root>/<channel>/<grid_size>x<grid_size>_recortada_<crop>/fila<R>_columna<C>.tiff
e.g. data/green/9x9_recortada_400/fila12_columna9.tiff -- "recortada_<crop>"
names the center-crop size already applied when the lab saved the TIFFs.
If your real layout differs, adjust `real_image_path()` below -- everything
else in this module and in reconstruct_real_images.py is layout-agnostic.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from PIL import Image

FILENAME_RE = re.compile(r"fila(\d+)_columna(\d+)\.tiff?$", re.IGNORECASE)


def _load_grayscale(path: str | Path, target_shape: tuple[int, int] | None = None) -> np.ndarray:
    img = Image.open(path).convert("F")  # float32 grayscale, no clipping
    if target_shape is not None:
        h, w = target_shape
        img = img.resize((w, h), Image.LANCZOS)
    return np.asarray(img, dtype=np.float64)


def load_reference_object(amplitude_path: str | Path, phase_path: str | Path,
                           target_shape: tuple[int, int] | None = None,
                           phase_range_rad: float = np.pi) -> np.ndarray:
    """Build a complex HR ground-truth object from two real images: one
    drives amplitude (normalized to [0, 1]), the other phase (normalized
    to [-phase_range_rad, phase_range_rad]). Both are resized to
    `target_shape` (the HR canvas size the run needs) if given, otherwise
    they must already be the same shape as each other.
    """
    amp_img = _load_grayscale(amplitude_path, target_shape)
    phase_img = _load_grayscale(phase_path, target_shape)
    if amp_img.shape != phase_img.shape:
        raise ValueError(
            f"amplitude image {amp_img.shape} and phase image {phase_img.shape} "
            "must be the same shape (pass target_shape to resize both)"
        )

    amp = amp_img / amp_img.max() if amp_img.max() > 0 else amp_img
    phase = (phase_img / phase_img.max() * 2 - 1) * phase_range_rad if phase_img.max() > 0 else phase_img
    return amp * np.exp(1j * phase)


def save_complex_as_images(obj: np.ndarray, output_dir: str | Path, prefix: str) -> None:
    """Save amplitude (0-255, normalized) and phase (wrapped to
    [-pi, pi] then mapped to 0-255) as PNGs -- for eyeballing results,
    not for further numeric processing (use the .npy / JSON outputs for that).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    amp = np.abs(obj)
    amp_img = (amp / amp.max() * 255 if amp.max() > 0 else amp).astype(np.uint8)
    Image.fromarray(amp_img).save(output_dir / f"{prefix}_amplitude.png")

    phase = np.angle(obj)
    phase_img = ((phase + np.pi) / (2 * np.pi) * 255).astype(np.uint8)
    Image.fromarray(phase_img).save(output_dir / f"{prefix}_phase.png")


def real_image_path(root: str | Path, channel: str, grid_size: int, crop: int,
                     row: int, col: int) -> Path:
    subdir = f"{grid_size}x{grid_size}_recortada_{crop}"
    return Path(root) / channel / subdir / f"fila{row}_columna{col}.tiff"


def load_real_lr_stack(root: str | Path, channel: str, grid_size: int, crop: int,
                        index_base: int = 1,
                        crop_to: tuple[int, int] | None = None
                        ) -> dict[tuple[int, int], np.ndarray]:
    """Load every fila<row>_columna<col>.tiff under
    root/channel/<grid_size>x<grid_size>_recortada_<crop>/ for row, col in
    [index_base, index_base + grid_size - 1]. Missing files are skipped
    (so a partial/interrupted scan still reconstructs with fewer LEDs, at
    reduced resolution/SNR). The TIFFs are already cropped to `crop` per
    the lab's own folder naming; `crop_to`, if given, center-crops further
    (a no-op if the file is already exactly that size) -- use it only if
    the on-disk images turn out bigger than their folder name says.
    """
    stack = {}
    hi = index_base + grid_size - 1
    for row in range(index_base, hi + 1):
        for col in range(index_base, hi + 1):
            path = real_image_path(root, channel, grid_size, crop, row, col)
            if not path.exists():
                continue
            img = _load_grayscale(path)
            if crop_to is not None:
                img = _center_crop(img, crop_to)
            stack[(row, col)] = img
    if not stack:
        raise FileNotFoundError(
            f"no fila*_columna*.tiff files found under "
            f"{Path(root) / channel / f'{grid_size}x{grid_size}_recortada_{crop}'}"
        )
    return stack


def _center_crop(img: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    h, w = shape
    y0 = (img.shape[0] - h) // 2
    x0 = (img.shape[1] - w) // 2
    if y0 < 0 or x0 < 0:
        raise ValueError(f"crop_to {shape} is larger than image {img.shape}")
    return img[y0:y0 + h, x0:x0 + w]
