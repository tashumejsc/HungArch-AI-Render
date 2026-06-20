# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**HungArch AI Render v2.1** — local web app for architects that transforms rough SketchUp massing model screenshots into photorealistic renders. Also converts 2D drawings (floor plans, elevations) into 3D perspectives. Runs entirely on the user's machine; internet required only for AI API calls.

## Running the App

```bat
run.bat          # Windows one-click: creates venv, installs deps, starts server, opens browser
```

Manual start (after first run):
```powershell
.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
```

`run.bat` auto-kills any existing process on port 8000 before starting.

## Architecture

### Request Flow
```
Browser (frontend/) → FastAPI (backend/main.py) → gemini_client.py → store.py → outputs/
```

### Backend modules (`backend/`)

| File | Role |
|---|---|
| `main.py` | FastAPI app; **6 routes**: `GET /api/presets`, `POST /api/config`, `POST /api/render`, `POST /api/inpaint`, `POST /api/analyze-mood`, `POST /api/enhance`. |
| `config.py` | Loads `.env`, exposes API keys and model IDs. `set_keys()` updates runtime state AND rewrites `.env` (called from `/api/config`). Client rebuilds lazily when key changes. Models: `flash` = `gemini-3.1-flash-image`, `pro` = `gemini-3-pro-image`. **Do not add `gemini-2.5-*-preview` — those are chat models and return 404 for IMAGE modality.** |
| `prompts.py` | **Single source of truth for all presets and prompt logic.** Key functions: `build_interior_prompt()`, `build_exterior_prompt()`, `build_drawing_prompt()` (dispatches to interior/exterior 3D or 2D render path), `build_inpaint_prompt()` (mask-based), `build_text_edit_prompt()` (text-only, no mask), `build_mood_analysis_prompt()` (colour-grading suggestion). `presets_payload()` drives all frontend dropdowns incl. `mood_presets`. |
| `store.py` | Saves `outputs/<token>.png` + `outputs/<token>.json` (metadata). `seed = token = filename` — no separate display_seed. |
| `gemini_client.py` | Wraps `google-genai` SDK. Four operations: `render()` (SketchUp → photorealistic, optional reference image), `enhance()` (quality upscale), `inpaint()` (local edit — mask OR text-only), `analyze_mood()` (text-only JSON response — no image modality). `_build_config()` constructs `GenerateContentConfig` defensively (tries full → partial → empty to survive SDK changes). |

### Frontend (`frontend/`)

- **No build step.** Plain HTML + JS + Tailwind CDN.
- `api.js` — thin fetch wrapper: `API.getPresets()`, `API.setConfig()`, `API.render()`, `API.inpaint()`, `API.analyzeMood()`, `API.enhance()`.
- `app.js` — all UI logic. Key functions: `loadPresets()`, `doRender()`, `doInpaint()`, `doTextEdit()`, `doEnhance()`, `doRebaseRender()`, `doAnalyzeMood()`, `showResult()`, `initInpaintModeToggle()`, `initEditPreviewActions()`. State: `originalSourceFile`, `originalRenderParams`, `appliedEdits[]`, `MAX_HISTORY = 30`.
- `mask.js` — `MaskTool` class: HTML5 Canvas brush draws **magenta** on transparent overlay. `mousemove`/`mouseup` are attached to `document` (not canvas) to prevent stroke interruption when mouse leaves canvas. Opacity 0.68. `exportMaskBlob()` exports magenta-on-black PNG at native resolution.

### Render Tabs

**Tab NỘI THẤT (`mode=interior`):** style preset + freetext → `build_interior_prompt()`.

**Tab NGOẠI THẤT (`mode=exterior`):** context + weather + vegetation + freetext → `build_exterior_prompt()`.

**Tab BẢN VẼ 2D (`mode=drawing`):** Three sub-controls:
- `drawing_type`: `autocad` | `sketch`
- `drawing_mode`: `3d_perspective` | `2d_render`
- `drawing_output`: `interior` | `exterior` (only for `3d_perspective`)

`build_drawing_prompt()` dispatches: floor-plan → interior 3D (`DRAWING_TO_3D` prompt), elevation → exterior 3D (`DRAWING_ELEVATION_TO_3D` prompt), or 2D prettification (`DRAWING_TO_2D` prompt).

### Hậu kỳ / Inpaint — Two Modes

**Chế độ Vẽ mask:** User draws on canvas → exports magenta-on-black PNG → sent to `/api/inpaint` with `mask` field → `gemini_client.inpaint(mask_bytes=<bytes>)` → `build_inpaint_prompt()`.

**Chế độ Mô tả văn bản:** No drawing needed. Only instruction text sent → `/api/inpaint` without `mask` field → `gemini_client.inpaint(mask_bytes=None)` → `build_text_edit_prompt()`. AI reads room labels/layout from the image to understand spatial context.

**Text-edit result flow:** API returns → compare view shows "Trước chỉnh sửa" / "Sau chỉnh sửa" slider → user clicks **Áp dụng** (updates `currentResult` + mask canvas, pushes to `appliedEdits[]`, shows `rebaseRenderBtn`) or **Giữ nguyên** (dismisses). On next render `showResult()` resets compare labels to "Gốc (SketchUp)" / "Render (AI)".

### Render lại từ gốc (C2)

After each inpaint (mask or text), the edit instruction is tracked in `appliedEdits[]`. When `appliedEdits.length > 0`, the **🔄 Render lại từ gốc** button appears. Clicking it calls `doRebaseRender()` which:
1. Concatenates all edit instructions into `combinedPrompt` appended to the original render prompt.
2. Calls `/api/render` with the **original SketchUp file** (`originalSourceFile`) and full combined prompt.
3. Resets `appliedEdits = []` and hides the button on success.

This prevents cumulative geometry drift from repeated inpaints on already-inpainted images.

### Gợi ý màu AI — analyze-mood (C3)

`POST /api/analyze-mood` accepts `image` + `mood` (key from `MOOD_PRESETS`) + `model`. It calls `gemini_client.analyze_mood()` which uses **text-only Gemini** (no image output, cheaper than render) and returns JSON `{brightness, contrast, saturate, warmth}`. Frontend `doAnalyzeMood()` applies these to the 4 colour sliders via `updateAdj()`. `MOOD_PRESETS` in `prompts.py` has 5 entries: `warm_luxe`, `cool_minimal`, `natural_daylight`, `cinematic_moody`, `warm_residential`.

### Key Design Decisions

**GEOMETRY_LOCK in prompts:** Gemini needs explicit instruction to preserve SketchUp geometry. Always included in `build_interior_prompt()` and `build_exterior_prompt()`. The drawing prompts have their own equivalent geometry-lock wording.

**Seed = token = filename:** `new_token()` generates `HA<timestamp><hex>` used as both the PNG filename and `RenderResult.seed`. No separate display_seed — user copies seed → finds exact file in `outputs/`.

**Inpaint mask format:** Frontend draws magenta (`#ff00ff`). Backend receives magenta-on-black PNG; the prompt instructs Gemini to edit only the magenta-marked region.

**Error messages:** All errors translated to Vietnamese via `viError()` in `app.js`. Error toasts display for 10 s (vs 3.5 s for success) to give time to read. 429 errors suggest billing/model/console — no longer mentions Replicate (removed).

**Compare view labels:** `cmpLabelBefore` / `cmpLabelAfter` are dynamic — set to "Trước/Sau chỉnh sửa" during text-edit preview, reset to "Gốc/Render" by `showResult()` on each new render.

**History cap:** `MAX_HISTORY = 30` — `addHistory()` calls `history.splice(MAX_HISTORY)` after push.

**analyze_mood JSON parsing:** defensive — tries `GenerateContentConfig(response_mime_type="application/json")`, fallback regex `\{[^{}]+\}`, validates all 4 required fields, clamps to defined ranges before returning.

## Adding New Presets

All preset data lives in `backend/prompts.py`. To add a new interior style:
1. Add an entry to `INTERIOR_STYLES` dict with `label` (Vietnamese) and `prompt` (detailed English visual description).
2. No other backend changes needed — `presets_payload()` auto-includes it.
3. Frontend dropdown rebuilds from `/api/presets` on load.

Same pattern for `EXTERIOR_CONTEXTS`, `EXTERIOR_WEATHER`, `LIGHTING_PRESETS`, `VEGETATION_DENSITY`, `MOOD_PRESETS`.

## Environment & Keys

- `.env` at project root — **never committed** (in `.gitignore`). Never hardcode keys anywhere.
- Users enter keys via the app UI ("🔑 Cấu hình khóa API") → `POST /api/config` → `config.set_keys()` writes to `.env`.
- Required: `GEMINI_API_KEY` (Google AI Studio).
- Model names overridable via env: `GEMINI_MODEL_PRO`, `GEMINI_MODEL_FLASH`.

## Known Constraints

- **Gemini image models have free tier = 0.** All Gemini image generation requires billing enabled on the Google Cloud project. `analyze_mood` uses text-only mode and is cheaper (~¼–½ of a render call).
- **`gemini-2.5-*-preview` models do NOT support IMAGE response modality** — they return 404. Only use models explicitly listed in `config.py`. `analyze_mood()` uses text-only so it can use any model, but for consistency uses the same model keys.
- Python 3.14 compatibility: `requirements.txt` uses `>=` (not pinned `==`) intentionally.
- Replicate is fully removed (v2.1). `replicate_client.py` deleted; no Replicate constants in `prompts.py` or `requirements.txt`.
