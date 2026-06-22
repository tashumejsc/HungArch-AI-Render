"""Image post-processing utilities for HungArch AI Render.

overlay_linework() — core fix for 2D floor plan geometry preservation.

Root cause problem solved here:
  Gemini image generation encodes the input into a semantic latent space,
  which LOSES exact pixel positions. The generated output is a new image that
  LOOKS LIKE the input floor plan but has different room proportions/positions.
  No prompt instruction can fix this — the pixel position information is gone
  before the prompt is even considered.

Solution: after Gemini colorizes the plan, re-stamp the original CAD linework
  (walls, dimension lines, annotations, hatch patterns) on top of the result.
  The final image has:
    - Color fills:     from Gemini  (approximate room tones, shadows, polish)
    - Line geometry:   from original (100% exact pixel positions)
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image


def overlay_linework(
    colorized_bytes: bytes,
    original_bytes: bytes,
    dark_threshold: int = 170,
) -> bytes:
    """Stamp original CAD linework on top of Gemini-colorized output.

    Args:
        colorized_bytes: PNG from Gemini (colors OK, geometry may be wrong).
        original_bytes:  PNG of original CAD drawing (exact geometry source).
        dark_threshold:  Average RGB below this = architectural line
                         (wall, dimension, text, hatch). Default 170 captures
                         black walls (0), dark grey dims (~80), medium hatches (~150).

    Returns:
        PNG bytes — Gemini color fills + original linework geometry.
    """
    colorized = Image.open(io.BytesIO(colorized_bytes)).convert("RGB")
    original  = Image.open(io.BytesIO(original_bytes)).convert("RGB")

    target_w, target_h = colorized.size

    # Scale original to match Gemini output canvas exactly.
    # Minor aspect-ratio distortion is acceptable here because Gemini also
    # stretches/squishes content to fill its output canvas.
    if original.size != (target_w, target_h):
        original = original.resize((target_w, target_h), Image.LANCZOS)

    colorized_arr = np.array(colorized, dtype=np.float32)   # (H, W, 3)
    original_arr  = np.array(original,  dtype=np.float32)   # (H, W, 3)

    # Per-pixel average brightness of original
    orig_brightness = original_arr.mean(axis=2)              # (H, W)

    # Line mask: True where original has dark architectural lines
    line_mask = orig_brightness < dark_threshold              # (H, W) bool

    # Stamp: wherever original has lines, replace AI pixels with original dark color
    result_arr = colorized_arr.copy()
    result_arr[line_mask] = original_arr[line_mask]

    result_img = Image.fromarray(np.clip(result_arr, 0, 255).astype(np.uint8))
    buf = io.BytesIO()
    result_img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()
