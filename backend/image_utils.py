"""Image post-processing utilities for HungArch AI Render.

overlay_linework() — core fix for 2D floor plan geometry preservation.

Root cause problem solved here:
  Gemini image generation encodes the input into a semantic latent space, which
  LOSES exact pixel positions. The generated output is a NEW image that looks
  like the floor plan but with drifted geometry, AND it redraws its own dark
  walls / poché / cast shadows / lines, all slightly shifted. Compositing the
  original lines on top of that produces a DOUBLED / GHOSTED drawing.

  A local filter (median / MaxFilter) only erases THIN strokes. Gemini's thick
  wall poché and large cast-shadow blobs survive and keep doubling the plan.

Solution: treat Gemini purely as a COLOUR (hue) source, never as structure.
  1. A median pass removes Gemini's thin redrawn lines.
  2. A BRIGHTNESS-FLOOR lift in HSV space brightens EVERY dark pixel — of any
     size — up to a pale level while keeping its hue. Gemini's dark walls and
     shadow blobs (which are near-greyscale) become light grey; coloured room
     fills keep their colour. Nothing dark remains to double the original.
  3. STAMP the original CAD linework (kept at original resolution, never
     stretched) on top → one single crisp line set.

  Final image:
    - Colour:   from Gemini, flattened to a pale even wash (no Gemini geometry left)
    - Geometry: from the original file, 100% exact, single crisp line set

  NOTE: the 2D prompt path asks Gemini for FLAT, LIGHT, SHADOWLESS fills so there
  is as little dark content as possible for this stage to neutralise.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageFilter


def _odd(n: int, lo: int, hi: int) -> int:
    """Clamp n to [lo, hi] and force an odd value (PIL filters need odd sizes)."""
    n = max(lo, min(hi, int(n)))
    return n if n % 2 == 1 else n + 1


def overlay_linework(
    colorized_bytes: bytes,
    original_bytes: bytes,
    dark_threshold: int = 165,
    value_floor: int = 178,
) -> bytes:
    """Composite Gemini colour with the original CAD linework — no doubling.

    Args:
        colorized_bytes: PNG from Gemini (colours OK, geometry/structure drifted).
        original_bytes:  PNG of original CAD drawing (authoritative geometry).
        dark_threshold:  Avg RGB below this in the ORIGINAL = a line to stamp back.
        value_floor:     Minimum HSV Value (0-255) for the colour wash. Every
                         Gemini pixel darker than this is lifted to it (hue kept),
                         which erases Gemini's dark walls / shadows of any size.

    Returns:
        PNG bytes — pale flat Gemini colour under a single crisp set of original lines.
    """
    colorized = Image.open(io.BytesIO(colorized_bytes)).convert("RGB")
    original  = Image.open(io.BytesIO(original_bytes)).convert("RGB")

    # Canvas = ORIGINAL dimensions → original linework is never resized (stays
    # pixel-perfect). Only the approximate Gemini colour layer is scaled to fit.
    W, H = original.size
    color_layer = colorized if colorized.size == (W, H) else colorized.resize((W, H), Image.LANCZOS)

    short_side = min(W, H)

    # --- Stage 1: remove Gemini's thin redrawn lines --------------------------
    median_size = _odd(short_side // 240, lo=3, hi=9)
    wash = color_layer.filter(ImageFilter.MedianFilter(size=median_size))

    # --- Stage 2: brightness-floor lift in HSV → erase ALL dark Gemini content -
    # Works per-pixel, so it neutralises dark regions of ANY size (thick walls,
    # big shadow blobs) that local filters cannot. Hue (room colour) is kept.
    hsv = np.array(wash.convert("HSV"), dtype=np.uint8)
    hsv[:, :, 2] = np.maximum(hsv[:, :, 2], np.uint8(value_floor))
    wash = Image.fromarray(hsv, "HSV").convert("RGB")
    # Gentle smooth so lifted greys blend into the surrounding wash.
    wash = wash.filter(ImageFilter.GaussianBlur(radius=max(2, short_side // 320)))

    wash_arr = np.array(wash,     dtype=np.float32)   # (H, W, 3) colour only
    orig_arr = np.array(original, dtype=np.float32)   # (H, W, 3) geometry source

    # --- Stage 3: stamp the original linework on top (single crisp set) --------
    line_mask = orig_arr.mean(axis=2) < dark_threshold
    result_arr = wash_arr.copy()
    result_arr[line_mask] = orig_arr[line_mask]

    result_img = Image.fromarray(np.clip(result_arr, 0, 255).astype(np.uint8))
    buf = io.BytesIO()
    result_img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()
