"""Image post-processing utilities for HungArch AI Render.

overlay_linework() — core fix for 2D floor plan geometry preservation.

Root cause problem solved here:
  Gemini image generation encodes the input into a semantic latent space,
  which LOSES exact pixel positions. The generated output is a new image that
  LOOKS LIKE the input floor plan but has different room proportions/positions,
  AND it re-draws its own copy of every line slightly shifted. If we simply
  stamp the original lines on top, BOTH line sets remain visible → the output
  shows a doubled / ghosted drawing.

Solution (two stages):
  1. SUPPRESS Gemini's own linework so it cannot double the original lines:
     - a median filter erases thin re-drawn strokes while keeping room colour;
     - any residual dark stroke that is NOT an original line is replaced with a
       heavily-blurred local colour so it dissolves into the surrounding fill.
  2. STAMP the original CAD linework (kept at the original pixel resolution, so
     it is never stretched) on top of the cleaned colour layer.

  Final image:
    - Colour fills:   from Gemini  (approximate room tones, shadows, polish)
    - Line geometry:  from original (100% exact pixel positions, single crisp set)
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageFilter


def _odd(n: int, lo: int, hi: int) -> int:
    """Clamp n to [lo, hi] and force an odd value (required by MedianFilter)."""
    n = max(lo, min(hi, int(n)))
    return n if n % 2 == 1 else n + 1


def overlay_linework(
    colorized_bytes: bytes,
    original_bytes: bytes,
    dark_threshold: int = 165,
    residual_dark: int = 110,
) -> bytes:
    """Composite Gemini colour fills with the original CAD linework, no doubling.

    Args:
        colorized_bytes: PNG from Gemini (colours OK, geometry/linework drifted).
        original_bytes:  PNG of original CAD drawing (authoritative geometry).
        dark_threshold:  Avg RGB below this in the ORIGINAL = architectural line
                         (wall, dimension, text, hatch). These get stamped back.
        residual_dark:   Avg RGB below this in the CLEANED colour layer, on a
                         non-line pixel, is treated as a leftover Gemini stroke
                         and dissolved into blurred local colour.

    Returns:
        PNG bytes — clean single-set original geometry over Gemini colour.
    """
    colorized = Image.open(io.BytesIO(colorized_bytes)).convert("RGB")
    original  = Image.open(io.BytesIO(original_bytes)).convert("RGB")

    # Canvas = ORIGINAL dimensions → original linework is never resized, so it
    # stays pixel-perfect. Only the (approximate) Gemini colour layer is scaled.
    W, H = original.size
    color_layer = colorized if colorized.size == (W, H) else colorized.resize((W, H), Image.LANCZOS)

    short_side = min(W, H)

    # --- Stage 1a: median filter erases Gemini's thin re-drawn lines ----------
    median_size = _odd(short_side // 220, lo=5, hi=13)
    color_clean = color_layer.filter(ImageFilter.MedianFilter(size=median_size))

    # Heavily-blurred colour used to fill residual dark strokes (Stage 1b).
    blur_radius = max(6, short_side // 120)
    color_blur = color_layer.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    color_arr = np.array(color_clean, dtype=np.float32)   # (H, W, 3)
    blur_arr  = np.array(color_blur,  dtype=np.float32)
    orig_arr  = np.array(original,    dtype=np.float32)

    orig_brightness = orig_arr.mean(axis=2)               # (H, W)
    line_mask = orig_brightness < dark_threshold          # original CAD lines

    # --- Stage 1b: dissolve any dark stroke that is NOT an original line ------
    cleaned_brightness = color_arr.mean(axis=2)
    residual = (cleaned_brightness < residual_dark) & (~line_mask)
    color_arr[residual] = blur_arr[residual]

    # --- Stage 2: stamp the original linework on top (single crisp set) -------
    result_arr = color_arr.copy()
    result_arr[line_mask] = orig_arr[line_mask]

    result_img = Image.fromarray(np.clip(result_arr, 0, 255).astype(np.uint8))
    buf = io.BytesIO()
    result_img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()
