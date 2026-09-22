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


def _real_image_path_candidates(root: str | Path, channel: str, grid_size: int, crop: int,
                                 row: int, col: int) -> list[Path]:
    """Both filename spellings seen in the wild: the convention this
    module documents (`columna`) and the lab's actual 2025-12-12 capture
    (`col`). Tried in that order; first existing one wins."""
    subdir = f"{grid_size}x{grid_size}_recortada_{crop}"
    base = Path(root) / channel / subdir
    return [base / f"fila{row}_columna{col}.tiff", base / f"fila{row}_col{col}.tiff"]


def load_real_lr_stack(root: str | Path, channel: str, grid_size: int, crop: int,
                        index_base: int = 1,
                        row_index_base: int | None = None,
                        col_index_base: int | None = None,
                        crop_to: tuple[int, int] | None = None
                        ) -> dict[tuple[int, int], np.ndarray]:
    """Load every fila<row>_columna<col>.tiff (or fila<row>_col<col>.tiff)
    under root/channel/<grid_size>x<grid_size>_recortada_<crop>/ for row in
    [row_index_base, row_index_base + grid_size - 1] and col in
    [col_index_base, col_index_base + grid_size - 1]. `row_index_base`/
    `col_index_base` default to `index_base` when not given -- the lab's
    own numbering doesn't always share one base between rows and columns
    (e.g. rows 13-21, columns 11-19 for the same on-axis-centered 9x9
    scan; see `config.LEDArrayConfig`'s docstring). Missing files are
    skipped (so a partial/interrupted scan still reconstructs with fewer
    LEDs, at reduced resolution/SNR). The TIFFs are already cropped to
    `crop` per the lab's own folder naming; `crop_to`, if given,
    center-crops further (a no-op if the file is already exactly that
    size) -- use it only if the on-disk images turn out bigger than their
    folder name says.
    """
    row_base = index_base if row_index_base is None else row_index_base
    col_base = index_base if col_index_base is None else col_index_base
    stack = {}
    for row in range(row_base, row_base + grid_size):
        for col in range(col_base, col_base + grid_size):
            candidates = _real_image_path_candidates(root, channel, grid_size, crop, row, col)
            path = next((c for c in candidates if c.exists()), None)
            if path is None:
                continue
            img = _load_grayscale(path)
            if crop_to is not None:
                img = _center_crop(img, crop_to)
            stack[(row, col)] = img
    if not stack:
        raise FileNotFoundError(
            f"no fila*_columna*.tiff or fila*_col*.tiff files found under "
            f"{Path(root) / channel / f'{grid_size}x{grid_size}_recortada_{crop}'} "
            f"for rows [{row_base}, {row_base + grid_size - 1}], "
            f"cols [{col_base}, {col_base + grid_size - 1}]"
        )
    return stack


def defocus_image_path(root: str | Path, channel: str, grid_size: int, crop: int,
                        sign: str) -> Path:
    """New convention introduced alongside `propagation.solve_tie`
    (docs/roadmap_agentic_multispectral_pipeline.md section 1 point 6's
    fix): two EXTRA on-axis captures per channel, one defocused each
    direction, next to the normal LED-grid scan folder --
    `defocus_plus.tiff` / `defocus_minus.tiff`. Not something the lab's
    existing capture protocol produces yet -- this is a proposed
    convention, matching `real_image_path`'s folder layout, for whoever
    adds this capture step. `sign` is "plus" or "minus".
    """
    if sign not in ("plus", "minus"):
        raise ValueError(f"sign must be 'plus' or 'minus', got {sign!r}")
    subdir = f"{grid_size}x{grid_size}_recortada_{crop}"
    return Path(root) / channel / subdir / f"defocus_{sign}.tiff"


def load_defocus_pair(root: str | Path, channel: str, grid_size: int, crop: int
                       ) -> tuple[np.ndarray, np.ndarray]:
    """Load the (intensity_plus, intensity_minus) on-axis defocused
    capture pair for one channel -- see `defocus_image_path` for the
    (proposed) file convention. Raises FileNotFoundError with both
    expected paths if either is missing, since TIE needs both.
    """
    path_plus = defocus_image_path(root, channel, grid_size, crop, "plus")
    path_minus = defocus_image_path(root, channel, grid_size, crop, "minus")
    if not path_plus.exists() or not path_minus.exists():
        raise FileNotFoundError(
            f"TIE needs both defocus captures; missing one or both of {path_plus}, {path_minus}"
        )
    return _load_grayscale(path_plus), _load_grayscale(path_minus)


def _center_crop(img: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    h, w = shape
    y0 = (img.shape[0] - h) // 2
    x0 = (img.shape[1] - w) // 2
    if y0 < 0 or x0 < 0:
        raise ValueError(f"crop_to {shape} is larger than image {img.shape}")
    return img[y0:y0 + h, x0:x0 + w]
