"""Image post-processing utilities for HungArch AI Render.

overlay_linework() — core fix for 2D floor plan geometry preservation.

Root cause problem solved here:
  Gemini image generation encodes the input into a semantic latent space, which
  LOSES exact pixel positions. The generated output is a NEW image that looks
  like the floor plan but with drifted geometry, AND it redraws its own walls /
  poché / cast shadows / lines, all slightly shifted. ANY attempt to composite
  the original lines over Gemini's raster leaves Gemini's shifted structure
  visible → a DOUBLED / GHOSTED drawing. Erasing that structure (median, max
  filter, brightness lift) only makes the ghost fainter, never gone.

Solution — MULTIPLY blend. Take ALL structure from the original drawing and use
  Gemini purely as a flat colour tint, so doubling is impossible by construction:

    result = original_drawing  ×  (flat_colour_wash / 255)

  - Where the original is a black line (0): 0 × anything = 0  → crisp line kept.
  - Where the original is white (a room):  255 × colour     → room tinted.
  The wash is flattened first (HSV brightness-floor to drop Gemini's dark walls /
  shadows, then a heavy blur to erase every Gemini line into a smooth colour
  field). Because the wash carries NO structure, the multiply can only tint the
  original — Gemini's geometry never appears, so there is nothing to double.

  Final image:
    - Geometry + linework: 100% from the original file (single crisp set).
    - Colour tint:         from Gemini, as a smooth pale wash per area.

  NOTE: the 2D prompt path still asks Gemini for FLAT, LIGHT, SHADOWLESS fills so
  the wash is as clean and bright as possible before multiplying.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageFilter


def overlay_linework(
    colorized_bytes: bytes,
    original_bytes: bytes,
    value_floor: int = 190,
) -> bytes:
    """Tint the original CAD drawing with Gemini's colour via multiply blend.

    Args:
        colorized_bytes: PNG from Gemini (colour OK, geometry/structure drifted).
        original_bytes:  PNG of original CAD drawing (authoritative geometry).
        value_floor:     Minimum HSV Value (0-255) applied to the wash before
                         blurring, so Gemini's dark walls/shadows cannot darken
                         the tint. Higher = lighter rooms, fainter colour.

    Returns:
        PNG bytes — original drawing tinted by a smooth Gemini colour wash.
    """
    colorized = Image.open(io.BytesIO(colorized_bytes)).convert("RGB")
    original  = Image.open(io.BytesIO(original_bytes)).convert("RGB")

    # Canvas = ORIGINAL dimensions → original linework is never resized.
    W, H = original.size
    color_layer = colorized if colorized.size == (W, H) else colorized.resize((W, H), Image.LANCZOS)

    short_side = min(W, H)

    # --- Build a FLAT colour wash (no structure) from Gemini -------------------
    # 1. Brightness-floor in HSV: lift every dark pixel (walls/shadows/lines) to
    #    a pale level, keeping hue, so nothing dark survives to darken the tint.
    hsv = np.array(color_layer.convert("HSV"), dtype=np.uint8)
    hsv[:, :, 2] = np.maximum(hsv[:, :, 2], np.uint8(value_floor))
    wash = Image.fromarray(hsv, "HSV").convert("RGB")
    # 2. Heavy blur: dissolve every Gemini line into a smooth colour field so the
    #    wash carries colour only, no geometry.
    wash = wash.filter(ImageFilter.GaussianBlur(radius=max(6, short_side // 90)))

    wash_arr = np.array(wash,     dtype=np.float32) / 255.0   # (H, W, 3) tint 0..1
    orig_arr = np.array(original, dtype=np.float32)            # (H, W, 3) structure

    # --- MULTIPLY blend: structure from original, colour from wash -------------
    result_arr = orig_arr * wash_arr

    result_img = Image.fromarray(np.clip(result_arr, 0, 255).astype(np.uint8))
    buf = io.BytesIO()
    result_img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()
