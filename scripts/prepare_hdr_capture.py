#!/usr/bin/env python3
"""prepare_hdr_capture.py -- turn a bracketed capture (every LED at several
exposures, plus darks) into one exposure-normalized stack per channel, in the
layout pipelines/reconstruct_real_images.py reads.

Input layout (the lab's 2026-09-24 capture):
    <capture>_<focus>_enfocado/fila<R>_col<C>_color<r|g|b>/<N>ms/imagen_frame_{1,2}.tiff
    <capture>_dark/fila<R>_col<C>_color<r|g|b>/<N>ms/imagen_frame_{1,2}.tiff
The two frames are averaged in float (the lab's `organizado/` copies are the
same average truncated to an integer).

Per LED, the LONGEST exposure with no saturated pixel (>= --saturation, in
either frame, inside the crop) is used; bright-field LEDs fall back to a
shorter one. The matching dark frame is subtracted pixel by pixel (hot pixels
at 100 ms reach ~800 counts, so a constant is not enough). Every image is then
expressed in counts at --reference-ms using the MEASURED ratio between
exposures (the 2026-09-24 capture gives ~10.6x per decade, not 10x): the
median of mean(long)/mean(short) over LEDs that are unsaturated at the long
exposure and have > --min-counts at the short one.

Output: <out>/<channel>/<G>x<G>_recortada_<crop>/fila<R>_col<C>.tiff (float32)
plus <out>/<channel>/hdr_provenance.json. Reconstruct with
--no-exposure-normalization, since the images are already normalized.

Usage:
    python3 scripts/prepare_hdr_capture.py \\
        --capture ~/Documents/AleYLu/imagenes_tomadas/2026-09-24 \\
        --out results/captura_2026-09-24/hdr --crop 400
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import tifffile

LETTER = {"red": "r", "green": "g", "blue": "b"}
_DIR_RE = re.compile(r"^fila(\d+)_col(\d+)_color([rgb])$")
_MS_RE = re.compile(r"^(\d+(?:\.\d+)?)ms$")


def _mean_frames(folder: Path) -> tuple[np.ndarray, np.ndarray]:
    frames = [tifffile.imread(p) for p in sorted(folder.glob("imagen_frame_*.tiff"))]
    if not frames:
        raise FileNotFoundError(f"no imagen_frame_*.tiff in {folder}")
    stack = np.stack(frames)
    return stack.astype(np.float64).mean(0), stack.max(0)


def _crop(img: np.ndarray, crop: int) -> np.ndarray:
    y0 = (img.shape[0] - crop) // 2
    x0 = (img.shape[1] - crop) // 2
    return img[y0:y0 + crop, x0:x0 + crop]


def prepare_channel(capture: Path, focus: str, channel: str, crop: int, out: Path,
                    saturation: int, reference_ms: float, min_counts: float) -> dict:
    src = Path(f"{capture}_{focus}_enfocado")
    dark_root = Path(f"{capture}_dark")
    letter = LETTER[channel]
    leds = sorted((int(m.group(1)), int(m.group(2)))
                  for d in src.iterdir() if (m := _DIR_RE.match(d.name)) and m.group(3) == letter)
    if not leds:
        raise FileNotFoundError(f"no fila*_col*_color{letter} folders in {src}")
    exposures = sorted(float(_MS_RE.match(d.name).group(1))
                       for d in (src / f"fila{leds[0][0]}_col{leds[0][1]}_color{letter}").iterdir()
                       if _MS_RE.match(d.name))

    def ms_dir(ms: float) -> str:
        return f"{ms:g}ms"

    dark_dirs = [d for d in dark_root.iterdir() if (m := _DIR_RE.match(d.name)) and m.group(3) == letter]
    if len(dark_dirs) != 1:
        raise ValueError(f"expected one dark folder for colour {letter} in {dark_root}, got {dark_dirs}")
    darks = {ms: _crop(_mean_frames(dark_dirs[0] / ms_dir(ms))[0], crop) for ms in exposures}

    # dark-subtracted crops and saturation flags, every LED x exposure
    img, sat = {}, {}
    for led in leds:
        for ms in exposures:
            mean, peak = _mean_frames(src / f"fila{led[0]}_col{led[1]}_color{letter}" / ms_dir(ms))
            img[led, ms] = _crop(mean, crop) - darks[ms]
            sat[led, ms] = bool((_crop(peak, crop) >= saturation).any())

    # measured gain between consecutive exposures, chained to reference_ms
    ratios = {}
    for short, long in zip(exposures[:-1], exposures[1:]):
        r = [img[led, long].mean() / img[led, short].mean() for led in leds
             if not sat[led, long] and img[led, short].mean() > min_counts]
        if len(r) < 3:
            raise ValueError(f"only {len(r)} LEDs to measure the {short}->{long} ms ratio")
        ratios[(short, long)] = (float(np.median(r)), float(np.std(r)), len(r))
    if reference_ms not in exposures:
        raise ValueError(f"--reference-ms {reference_ms} is not one of the exposures {exposures}")
    to_ref = {reference_ms: 1.0}
    i_ref = exposures.index(reference_ms)
    for i in range(i_ref + 1, len(exposures)):
        to_ref[exposures[i]] = to_ref[exposures[i - 1]] / ratios[(exposures[i - 1], exposures[i])][0]
    for i in range(i_ref - 1, -1, -1):
        to_ref[exposures[i]] = to_ref[exposures[i + 1]] * ratios[(exposures[i], exposures[i + 1])][0]

    dest = out / channel
    grid_rows = sorted({r for r, _ in leds})
    grid_cols = sorted({c for _, c in leds})
    if len(grid_rows) != len(grid_cols):
        raise ValueError(f"LED grid is not square: rows {grid_rows}, cols {grid_cols}")
    folder = dest / f"{len(grid_rows)}x{len(grid_rows)}_recortada_{crop}"
    folder.mkdir(parents=True, exist_ok=True)
    chosen = {}
    for led in leds:
        usable = [ms for ms in exposures if not sat[led, ms]]
        if not usable:
            raise ValueError(f"LED {led} is saturated at every exposure")
        ms = max(usable)
        chosen[led] = ms
        tifffile.imwrite(folder / f"fila{led[0]}_col{led[1]}.tiff",
                         (img[led, ms] * to_ref[ms]).astype(np.float32))

    info = {
        "source": str(src), "dark": str(dark_dirs[0]), "channel": channel, "focus": focus,
        "crop": crop, "reference_ms": reference_ms, "saturation_counts": saturation,
        "exposures_ms": exposures,
        "measured_ratio": {f"{s:g}->{l:g}ms": {"median": v[0], "std": v[1], "n_leds": v[2]}
                           for (s, l), v in ratios.items()},
        "scale_to_reference": {f"{ms:g}": v for ms, v in to_ref.items()},
        "chosen_exposure_ms": {f"{r},{c}": ms for (r, c), ms in chosen.items()},
        "n_leds_by_exposure": {f"{ms:g}": sum(1 for v in chosen.values() if v == ms) for ms in exposures},
        "row_index_base": grid_rows[0], "col_index_base": grid_cols[0], "grid_size": len(grid_rows),
    }
    (dest / "hdr_provenance.json").write_text(json.dumps(info, indent=2))
    return info


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--capture", required=True, type=Path,
                   help="capture prefix, e.g. .../2026-09-24 (reads <prefix>_<focus>_enfocado and <prefix>_dark)")
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--channels", nargs="+", default=["red", "green", "blue"], choices=sorted(LETTER))
    p.add_argument("--focus", default=None, choices=sorted(LETTER),
                   help="focus setting to read (default: each channel's own, e.g. red from _red_enfocado)")
    p.add_argument("--crop", type=int, default=400)
    p.add_argument("--saturation", type=int, default=4095, help="Mono12 full scale")
    p.add_argument("--reference-ms", type=float, default=10.0)
    p.add_argument("--min-counts", type=float, default=5.0,
                   help="minimum mean counts at the shorter exposure for an LED to enter the ratio")
    args = p.parse_args(argv)
    for ch in args.channels:
        info = prepare_channel(args.capture.expanduser(), args.focus or ch, ch, args.crop,
                               args.out, args.saturation, args.reference_ms, args.min_counts)
        print(f"{ch}: exposures used {info['n_leds_by_exposure']}  ratios "
              f"{ {k: round(v['median'], 3) for k, v in info['measured_ratio'].items()} }")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
