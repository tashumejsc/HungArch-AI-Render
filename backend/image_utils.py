"""Image post-processing utilities for HungArch AI Render.

overlay_linework() — core fix for 2D floor plan geometry preservation.

Problem chain (each prior approach and why it failed):
  - Stamp original lines over Gemini's raster → Gemini's shifted walls/lines
    remain → DOUBLED drawing.
  - Erase Gemini structure (median / max / brightness lift) → only fades the
    ghost; grey 178 lines still visible on white.
  - Plain multiply (heavy blur) → no doubling, but washed-out PALE colour, not
    the solid material colours of a SketchUp LayOut plan.
  - Region fill (segment + flat colour per room) → doorways merge neighbouring
    rooms into one region → muddy averaged colour.

Solution — SATURATION-GATED MULTIPLY:
  Build a colour wash from Gemini where
    * saturated pixels (real room colour) keep a rich, brightened tone, but
    * desaturated pixels (Gemini's grey walls / cast shadows / redrawn lines)
      are pushed to WHITE.
  Then multiply the wash onto the ORIGINAL drawing:

    result = original_drawing  ×  (wash / 255)

  - Original black line × anything = 0 → crisp original geometry kept.
  - White room × rich colour      = vivid room colour.
  - Gemini's grey ghosts → white in the wash → multiply tints nothing → they
    vanish. No segmentation, so no door-merge muddiness; structure is 100% from
    the original, so doubling is impossible.

  NOTE: the 2D prompt asks Gemini for FLAT, LIGHT, SHADOWLESS fills, so almost
  all of its output is saturated room colour and the wash stays clean.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageFilter


def overlay_linework(
    colorized_bytes: bytes,
    original_bytes: bytes,
    value_floor: int = 165,
    sat_boost: float = 1.4,
    sat_lo: int = 18,
    sat_hi: int = 55,
) -> bytes:
    """Tint the original CAD drawing with Gemini's rich colour, ghost-free.

    Args:
        colorized_bytes: PNG from Gemini (colour OK, geometry/structure drifted).
        original_bytes:  PNG of original CAD drawing (authoritative geometry).
        value_floor:     HSV Value floor for coloured pixels (keeps colour bright).
        sat_boost:       Saturation multiplier for richer presentation colour.
        sat_lo, sat_hi:  HSV Saturation band (0-255). Below sat_lo a pixel is
                         treated as Gemini greyscale → pushed to white; above
                         sat_hi it is full room colour; linear in between.

    Returns:
        PNG bytes — original drawing tinted with solid Gemini room colour.
    """
    colorized = Image.open(io.BytesIO(colorized_bytes)).convert("RGB")
    original  = Image.open(io.BytesIO(original_bytes)).convert("RGB")

    # Canvas = ORIGINAL dimensions → original linework is never resized.
    W, H = original.size
    color_layer = colorized if colorized.size == (W, H) else colorized.resize((W, H), Image.LANCZOS)
    short_side = min(W, H)

    # --- Rich colour version of Gemini (brighten + boost saturation) -----------
    hsv = np.array(color_layer.convert("HSV"), dtype=np.float32)
    sat = hsv[:, :, 1].copy()                       # original saturation (for the gate)
    hsv[:, :, 2] = np.maximum(hsv[:, :, 2], value_floor)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * sat_boost, 0, 255)
    rich = np.array(Image.fromarray(hsv.astype(np.uint8), "HSV").convert("RGB"), dtype=np.float32)

    # --- Saturation gate: keep colour where saturated, go WHITE where grey -----
    # gate = 0 for Gemini greyscale (walls/shadows/lines) → white → no tint/ghost
    # gate = 1 for real room colour → rich tint.
    gate = np.clip((sat - sat_lo) / float(max(1, sat_hi - sat_lo)), 0.0, 1.0)[:, :, None]
    wash = rich * gate + 255.0 * (1.0 - gate)

    # Light blur so the wash reads as smooth flat colour fields.
    wash_img = Image.fromarray(np.clip(wash, 0, 255).astype(np.uint8))
    wash_img = wash_img.filter(ImageFilter.GaussianBlur(radius=max(2, short_side // 300)))
    wash_arr = np.array(wash_img, dtype=np.float32) / 255.0

    # --- MULTIPLY: structure from original, colour from wash -------------------
    orig_arr = np.array(original, dtype=np.float32)
    result_arr = orig_arr * wash_arr

    out = Image.fromarray(np.clip(result_arr, 0, 255).astype(np.uint8))
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()
