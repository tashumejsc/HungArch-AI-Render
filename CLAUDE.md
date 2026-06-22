# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**HungArch AI Render v1.0.1** — local web app for architects that transforms rough SketchUp massing model screenshots into photorealistic renders. Also converts 2D drawings (floor plans, elevations) into 3D perspectives. Runs entirely on the user's machine; internet required only for AI API calls.

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
                                              ↳ pdf_utils.py    (PDF page split)
                                              ↳ license.py      (trial / activation gate)
```

### Backend modules (`backend/`)

| File | Role |
|---|---|
| `main.py` | FastAPI app; **10 routes**: `GET /api/presets`, `POST /api/config`, `GET /api/license`, `POST /api/license/activate`, `POST /api/pdf-preview`, `POST /api/render-pdf-page`, `POST /api/render`, `POST /api/inpaint`, `POST /api/analyze-mood`, `POST /api/enhance`. Image-generating routes call `_require_license()` first. 2D-render (`drawing_mode == "2d_render"`) returns Gemini's raw "Top-View 3D Floor Plan" output with **no** post-processing (the old `overlay_linework` step was removed). |
| `config.py` | Loads `.env`, exposes API keys and model IDs. `set_keys()` updates runtime state AND rewrites `.env` (called from `/api/config`). Client rebuilds lazily when key changes. Models: `flash` = `gemini-3.1-flash-image`, `pro` = `gemini-3-pro-image`. **Do not add `gemini-2.5-*-preview` — those are chat models and return 404 for IMAGE modality.** |
| `prompts.py` | **Single source of truth for all presets and prompt logic.** Key functions: `build_interior_prompt()`, `build_exterior_prompt()`, `build_drawing_prompt()` (dispatches to interior/exterior 3D or 2D render path), `build_inpaint_prompt()` (mask-based), `build_text_edit_prompt()` (text-only, no mask), `build_mood_analysis_prompt()` (colour-grading suggestion). `presets_payload()` drives all frontend dropdowns incl. `mood_presets`. `REFERENCE_INSTRUCTION` enforces strict separation between the two render images (see Reference-image style sync below). |
| `store.py` | Saves `outputs/<token>.png` + `outputs/<token>.json` (metadata). `seed = token = filename` — no separate display_seed. |
| `gemini_client.py` | Wraps `google-genai` SDK. Four operations: `render()` (SketchUp → photorealistic, optional reference image), `enhance()` (quality upscale), `inpaint()` (local edit — mask OR text-only), `analyze_mood()` (text-only JSON response — no image modality). `_build_config()` constructs `GenerateContentConfig` defensively (tries full → partial → empty to survive SDK changes). **`render()` with a reference image interleaves a labelling text part BEFORE each image** (`"IMAGE 1 … PRIMARY INPUT"` / `"IMAGE 2 … STYLE REFERENCE ONLY"`) so Gemini does not copy the reference's geometry. |
| `image_utils.py` | **Dead code** — `overlay_linework()` from the abandoned 2D-colourise approach. No longer imported by `main.py`. Kept on disk for reference; safe to delete. |
| `pdf_utils.py` | Splits an uploaded PDF into per-page PNGs + thumbnails for the multi-page 2D render flow. |
| `license.py` | 30-day trial + offline ECDSA key activation. `get_status()` / `activate()`. |

### Frontend (`frontend/`)

- **No build step.** Plain HTML + JS + Tailwind CDN. Cache-busted via `?v=X.X.X` on all script/CSS tags.
- `api.js` — thin fetch wrapper: `API.getPresets()`, `API.setConfig()`, `API.render()`, `API.inpaint()`, `API.analyzeMood()`, `API.enhance()`.
- `app.js` — all UI logic. Key functions:

| Function | Role |
|---|---|
| `loadPresets()` | Fetches `/api/presets`, fills all dropdowns, calls `updateTechSummary()` |
| `doRender()` | Submits render form; saves `originalSourceFile` / `originalRenderParams`; resets `appliedEdits = []`. Routes to `doRenderPdfPages()` (PDF mode) or `doRenderMulti()` (interior/exterior with extra angles) before the single-render path. |
| `doRenderMulti(primaryFile, extraAngles)` | **Đa góc nhìn (multi-angle).** Renders the primary angle, then uses its output as the `reference_image` for each extra angle → style-consistent set. Pure frontend orchestration over `/api/render` (no backend route). Calls `showMultiAngleResults()`. |
| `doInpaint()` | Mask-mode: exports canvas → POST to `/api/inpaint` with mask; pushes to `appliedEdits[]` on success |
| `doTextEdit()` | Text-mode: POST to `/api/inpaint` without mask; shows compare view + `#editPreviewActions` |
| `doEnhance()` | POST to `/api/enhance`; calls `showResult()` |
| `doRebaseRender()` | Concatenates `appliedEdits[]` into combined prompt; calls `/api/render` with `originalSourceFile`; resets `appliedEdits = []` |
| `doAnalyzeMood()` | POST to `/api/analyze-mood`; applies returned JSON to 4 colour sliders via `updateAdj()` |
| `showResult(data)` | Sets `currentResult`; loads image into canvas + compare + adjust panels; calls `updatePostProcessLock()` |
| `updateTabDots()` | Shows/hides `.tab-dot` green indicator on each tab button based on `files[TAB_FILE_MAP[tab]]` |
| `updateTechSummary()` | Updates `#techSummary` text (lighting · model · res) and `#techCostPill` (flash = green ~$0.04, pro = amber ~$0.15) |
| `updatePostProcessLock()` | Toggles `.section-disabled` on `#postProcessCard` / `#historyCard`; toggles `#postProcessLockNote` visibility — based on `currentResult === null` |
| `initEditPreviewActions()` | Wires `#applyEditBtn` (updates `currentResult`, calls `updatePostProcessLock()`, pushes to `appliedEdits[]`) and `#discardEditBtn` |
| `updateAdj()` | Rebuilds CSS filter string; syncs main ↔ mini colour sliders (`#ppBr/Co/Sa/Wa`) |

- `mask.js` — `MaskTool` class: HTML5 Canvas brush draws **magenta** on transparent overlay. `mousemove`/`mouseup` are attached to `document` (not canvas) to prevent stroke interruption when mouse leaves canvas. Opacity 0.68. `exportMaskBlob()` exports magenta-on-black PNG at native resolution.

### Left Column Layout (5 Groups)

```
#keyPanel         <details> — compact strip when closed (padding 0.42rem)
Tabs row          3 tab-btn with .tab-dot green indicator when image uploaded
#tab-interior     Upload + "📸 Góc nhìn bổ sung" (2 mini-dropzones) + style dropdown + prompt textarea
#tab-exterior     Upload + "📸 Góc nhìn bổ sung" (2 mini-dropzones) + "Bối cảnh & môi trường" card (context + weather + vegetation)
#tab-drawing      Upload + drawing type/mode/output controls with branch-flow hints
.input-type-card  Shared Wireframe / Đã vật liệu toggle (amber border, always visible)
#techConfig       <details> accordion: reference image, lighting, seed, resolution, model
                  summary shows: "▶ ⚙️ Cấu hình kỹ thuật [lighting · model · res] [cost pill]"
#renderBtn        Primary CTA
```

`#vegetationWrap` lives inside `#tab-exterior` (not the old tech accordion). `updateVegetationVisibility()` still uses `currentTab !== 'exterior'` check — redundant but harmless.

The input-type toggle (`#itWireframe`/`#itTextured`) must be a **single DOM node** due to unique-ID constraint. It sits between the tab panels and `#techConfig` as a shared card.

### Hậu kỳ / Inpaint — Three Tiers

Card `#postProcessCard` (locked with `.section-disabled` until `currentResult` is set).

**Tier 1 — Chế độ sửa:**
- `#imMask` → `data-imode="mask"` — activates `#maskModeWrap`
- `#imText` → `data-imode="text"` — activates `#textModeWrap`

**Tier 2A — Mask mode (`#maskModeWrap`):**  
`div.pp-mask-tools-block` (dark inner block) contains:
- `#drawMaskBtn` "➕ Thêm vùng chọn" — adds to selection (draw mode)
- `#eraseMaskBtn` "➖ Bớt vùng chọn" — subtracts from selection (erase mode)
- `#undoMaskBtn` (↩ icon, 38×38 `.pp-icon-btn`) — undo last stroke
- `#clearMaskBtn` (🗑 icon, 38×38 `.pp-icon-btn`) — clear entire mask
- `#brushSize` range slider

Then: `#inpaintInstruction` textarea + `#inpaintBtn` with `<span class="pp-api-note">~1 lần gọi API</span>`.

**Tier 2B — Text mode (`#textModeWrap`):**  
Hint line + italic note "Không cần vẽ vùng — AI tự xác định vị trí dựa theo mô tả của bạn." + `#textEditInstruction` textarea + `#textEditBtn`.

**`#editPreviewActions`** (hidden by default, shown after `doTextEdit()` succeeds):  
JS adds `flex` + removes `hidden`. Static class includes `flex-col gap-2` so when flex is added it becomes column layout. Contains: note line → inner `div.flex.gap-2` → `#applyEditBtn` / `#discardEditBtn`.

**Tier 3 — Hành động khác:**  
3-column grid: `#ppAdjBtn` (toggle `#ppAdjPanel`), `#ppEnhanceBtn` (→`doEnhance`), `#ppRebaseBtn` (→`doRebaseRender`, disabled when `appliedEdits.length === 0`).  
`#ppAdjPanel` (hidden by default): 4 mini sliders (`#ppBr/Co/Sa/Wa`) that bidirectionally sync with main `#adjBrightness/Contrast/Saturate/Warmth` via `updateAdj()`.

**Section locking:** `#postProcessCard` and `#historyCard` have `.section-disabled` at page load. `updatePostProcessLock()` removes it (and hides `#postProcessLockNote`) as soon as `currentResult` is set by `showResult()` or `applyEditBtn` handler.

### Render lại từ gốc (C2)

After each inpaint (mask or text-edit applied), the edit instruction is pushed to `appliedEdits[]`. When `appliedEdits.length > 0`, both `#rebaseRenderBtn` (result area) and `#ppRebaseBtn` (Tier 3) become enabled. `doRebaseRender()`:
1. Concatenates all `appliedEdits[].instruction` into `combinedPrompt` appended to `originalRenderParams.prompt`.
2. Calls `/api/render` with `originalSourceFile` (the original SketchUp file, not the inpainted image).
3. Resets `appliedEdits = []` and disables both rebase buttons on success.

This prevents cumulative geometry drift from repeated inpaints on already-inpainted images.

### Gợi ý màu AI — analyze-mood (C3)

`POST /api/analyze-mood` accepts `image` + `mood` (key from `MOOD_PRESETS`) + `model`. It calls `gemini_client.analyze_mood()` which uses **text-only Gemini** (no image output, cheaper than render) and returns JSON `{brightness, contrast, saturate, warmth}`. Frontend `doAnalyzeMood()` applies these to the 4 colour sliders via `updateAdj()`. `MOOD_PRESETS` in `prompts.py` has 5 entries: `warm_luxe`, `cool_minimal`, `natural_daylight`, `cinematic_moody`, `warm_residential`.

### 2D drawing — "Top-View 3D Floor Plan" (current approach)

**Design pivot (important history):** the 2D path originally tried to *colourise* the CAD line drawing while preserving exact geometry, using `image_utils.overlay_linework()` as a post-step. Every variant (stamp / erase / multiply / saturation-gated multiply / region-fill) hit the same wall — colours read flat/pale/bleeding and there was no real 3D depth, because it was fundamentally a 2D tint over line art. **That whole approach was abandoned.**

The current 2D mode is a **generative "Top-View 3D Floor Plan"**: Gemini builds a complete, fully-furnished 3D scene from the 2D plan (real materials, real furniture, walls trimmed to a low parapet so the camera sees in) and photographs it from a **high camera at ~75–85°** (not a flat 90° orthographic) so furniture sides and **real soft 3D shadows** are visible — the real-estate "3D floor plan" presentation style.

- Driven entirely by `prompts.py`: `DRAWING_TO_2D_FLOOR_PLAN` / `DRAWING_TO_2D_SITE_PLAN` (build a furnished 3D scene), `_TOPVIEW_3D_CAMERA` (the ~75–85° high camera, residual perspective is *intentional*), `QUALITY_SUFFIX_2D` (genuine CGI photo, NOT flat/orthographic/vector). Order: `[base, dtype_hint, _TOPVIEW_3D_CAMERA, user, QUALITY_SUFFIX_2D]`.
- **No post-processing.** `main.py` does NOT call `overlay_linework()` for 2D anymore — the raw Gemini 3D render is the output. Stamping CAD lines on top would destroy the 3D look.
- **`image_utils.py` is now dead code** (kept on disk, no longer imported). `numpy`/`scipy` are no longer needed by the 2D path.
- **Trade-off accepted:** geometry is no longer pixel-exact (it's a generative 3D scene that follows the plan's layout/proportions), in exchange for a genuinely 3D, furnished, shadowed presentation render.

### Reference-image style sync (Đồng bộ Style)

Bug class: when a polished render is passed as `reference_image`, Gemini gravitates to the **more photorealistic** image and copies its geometry/objects, ignoring the (greyscale, less detailed) SketchUp input. Fix has two parts and **must stay together**:
- `gemini_client.render()` interleaves a **text label before each image** in `contents` (`IMAGE 1 = PRIMARY INPUT` / `IMAGE 2 = STYLE REFERENCE ONLY`).
- `REFERENCE_INSTRUCTION` takes ALL geometry/camera/layout from image 1, ONLY colour/material/mood from image 2, with an explicit prohibition on copying the reference's objects, screens, text, composition.

### Đa góc nhìn — multi-angle render (B)

Lets one room/building render at 2–3 different SketchUp camera angles with **consistent style**. Implemented **entirely in the frontend** (no backend route) by chaining `/api/render`:
1. Render the primary angle (uses the user's `referenceImage` if present).
2. Fetch its output PNG → use as the `reference_image` for each extra angle (leans on the reference-image fix above for style consistency).
3. `showMultiAngleResults()` puts the primary in the main viewer (post-process enabled) and renders a 3-up gallery (`#multiAngleGallery`); clicking a thumbnail swaps the active result.

UI: `#tab-interior` / `#tab-exterior` each have a "📸 Góc nhìn bổ sung" block with 2 `.dropzone-mini` zones → `files.{interior,exterior}Angle2/3`. `_extraAngleFiles()` reads them; `updateRenderBtnLabel()` shows "📸 Render N góc đồng bộ". `doRender()` routes to `doRenderMulti()` when ≥1 extra angle is present. **Each angle is an independent Gemini call**, so exact material micro-detail (e.g. marble veining) won't match pixel-for-pixel across angles — only material type / tone / mood.

### Key Design Decisions

**GEOMETRY_LOCK in prompts:** Gemini needs explicit instruction to preserve SketchUp geometry. Always included in `build_interior_prompt()` and `build_exterior_prompt()`. The drawing prompts have their own equivalent geometry-lock wording.

**Seed = token = filename:** `new_token()` generates `HA<timestamp><hex>` used as both the PNG filename and `RenderResult.seed`. No separate display_seed — user copies seed → finds exact file in `outputs/`.

**Inpaint mask format:** Frontend draws magenta (`#ff00ff`). Backend receives magenta-on-black PNG; the prompt instructs Gemini to edit only the magenta-marked region.

**Error messages:** All errors translated to Vietnamese via `viError()` in `app.js`. Error toasts display for 10 s (vs 3.5 s for success). 429 errors suggest billing/model/console.

**Compare view labels:** `cmpLabelBefore` / `cmpLabelAfter` are dynamic — set to "Trước/Sau chỉnh sửa" during text-edit preview, reset to "Gốc/Render" by `showResult()` on each new render.

**History cap:** `MAX_HISTORY = 30` — `addHistory()` calls `history.splice(MAX_HISTORY)` after push.

**analyze_mood JSON parsing:** defensive — tries `GenerateContentConfig(response_mime_type="application/json")`, fallback regex `\{[^{}]+\}`, validates all 4 required fields, clamps to defined ranges before returning.

**`.section-disabled` lock pattern:** `opacity: 0.4; pointer-events: none` applied to `#postProcessCard` and `#historyCard` at init. Removed by `updatePostProcessLock()` after first successful render. `#postProcessLockNote` (a `<p>`) toggles opposite — visible when locked.

**Tech accordion summary:** `#techConfig` is a `<details>` element. CSS hides default browser disclosure triangle (`::-webkit-details-marker` + `::marker`), replaces with `▶`/`▼` via `::before`. `updateTechSummary()` writes to `#techSummary` span and `#techCostPill` (colour-coded by model).

**`editPreviewActions` flex layout:** The div has static class `flex-col gap-2`. JS adds `flex` (removes `hidden`) to display it — making it `flex flex-col gap-2` so the note line stacks above the button row (which lives in an inner `div.flex.gap-2`).

**`btn-primary:disabled` style:** Uses grey `background: #334155` with `opacity: 0.6` (not the default faded gradient) so disabled state is clearly distinct from active state. Both `#inpaintBtn` and `#textEditBtn` use this automatically.

**Tab file map:** `TAB_FILE_MAP = { interior: 'interiorImage', exterior: 'exteriorImage', drawing: 'drawingImage' }` — used by `updateTabDots()` to check which tabs have uploaded images.

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
- Python 3.14 compatibility: `requirements.txt` uses `>=` (not pinned `==`) intentionally. (`numpy` is listed but now only used by the dead `image_utils.py`.)
- Replicate is fully removed. `replicate_client.py` deleted; no Replicate constants in `prompts.py` or `requirements.txt`.
- **2D mode is now a generative "Top-View 3D Floor Plan"**, not a geometry-exact colourise. Gemini regenerates the plan as a furnished 3D scene; exact pixel geometry is intentionally NOT preserved. Do not re-add CAD-line overlay post-processing — it was removed on purpose (it killed the 3D look).
