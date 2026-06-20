"""HungArch AI Render — FastAPI app (Gemini-only, v2.1).

6 endpoint API:
  GET  /api/presets       — danh sách preset + model cho frontend
  POST /api/config        — lưu API key
  POST /api/render        — render ảnh SketchUp → photorealistic
  POST /api/inpaint       — sửa cục bộ (mask hoặc mô tả văn bản)
  POST /api/analyze-mood  — đề xuất thông số colour-grading (text-only, không sinh ảnh)
  POST /api/enhance       — nâng cao chất lượng ảnh render đã có (AI upscale)
"""
from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
import gemini_client
import prompts


class KeyConfig(BaseModel):
    gemini_api_key: str | None = None


app = FastAPI(title="HungArch AI Render", version="2.0.0")


# ── Presets ───────────────────────────────────────────────────────────────────
@app.get("/api/presets")
def get_presets():
    """Danh sách preset + model + cấu hình cho frontend."""
    return {
        **prompts.presets_payload(),
        "models": [
            {"key": k, "label": config.MODEL_LABELS[k]}
            for k in config.MODELS
        ],
        "default_model":     config.DEFAULT_MODEL_KEY,
        "resolutions":       config.VALID_RESOLUTIONS,
        "default_resolution": config.DEFAULT_RESOLUTION,
        "api_key_configured": bool(config.GEMINI_API_KEY),
    }


# ── Config (lưu API key) ──────────────────────────────────────────────────────
@app.post("/api/config")
def set_config(body: KeyConfig):
    config.set_keys(gemini=body.gemini_api_key)
    return {"api_key_configured": bool(config.GEMINI_API_KEY)}


# ── Render ────────────────────────────────────────────────────────────────────
@app.post("/api/render")
async def api_render(
    mode: str = Form(...),                              # "interior" | "exterior"
    image: UploadFile = File(...),                      # ảnh SketchUp
    style: str = Form(""),
    context: str = Form(""),
    weather: str = Form(""),
    prompt: str = Form(""),
    input_type: str = Form("wireframe"),               # "wireframe" | "textured"
    drawing_mode: str = Form("3d_perspective"),        # "3d_perspective" | "2d_render"
    drawing_type: str = Form("autocad"),               # "autocad" | "sketch"
    drawing_output: str = Form("interior"),            # "interior" | "exterior" (cho 3d_perspective)
    model: str = Form(config.DEFAULT_MODEL_KEY),
    resolution: str = Form(config.DEFAULT_RESOLUTION),
    seed: str = Form(""),
    lighting: str = Form("golden_hour"),
    vegetation: str = Form("moderate"),
    reference_image: UploadFile | None = File(None),
):
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Thiếu ảnh đầu vào.")

    if mode == "interior":
        prompt_text = prompts.build_interior_prompt(
            style, prompt, lighting, input_type=input_type
        )
    elif mode == "exterior":
        prompt_text = prompts.build_exterior_prompt(
            context, weather, prompt, lighting, vegetation, input_type=input_type
        )
    elif mode == "drawing":
        prompt_text = prompts.build_drawing_prompt(
            drawing_mode, drawing_type,
            drawing_output=drawing_output,
            style_key=style,
            context_key=context,
            weather_key=weather,
            user_text=prompt,
            lighting_key=lighting,
        )
    else:
        raise HTTPException(status_code=400, detail="mode phải là 'interior', 'exterior' hoặc 'drawing'.")

    ref_bytes, ref_mime = None, "image/png"
    if reference_image is not None:
        ref_bytes = await reference_image.read() or None
        ref_mime = reference_image.content_type or "image/png"

    try:
        result = gemini_client.render(
            mode=mode,
            image_bytes=image_bytes,
            image_mime=image.content_type or "image/png",
            prompt_text=prompt_text,
            reference_bytes=ref_bytes,
            reference_mime=ref_mime,
            model_key=model,
            resolution=resolution,
            seed=seed.strip() or None,
        )
    except gemini_client.GeminiError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return JSONResponse({
        "seed":           result.seed,
        "image_url":      result.image_url,
        "image_filename": result.image_filename,
        "prompt_used":    result.prompt_used,
    })


# ── Inpaint ───────────────────────────────────────────────────────────────────
@app.post("/api/inpaint")
async def api_inpaint(
    image: UploadFile = File(...),
    mask: UploadFile | None = File(None),   # None = chỉnh sửa thuần văn bản
    instruction: str = Form(...),
    model: str = Form(config.DEFAULT_MODEL_KEY),
    resolution: str = Form(config.DEFAULT_RESOLUTION),
    seed: str = Form(""),
):
    image_bytes = await image.read()
    mask_bytes = (await mask.read()) if mask else None
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Thiếu ảnh đầu vào.")
    if not instruction.strip():
        raise HTTPException(status_code=400, detail="Hãy nhập chỉ thị chỉnh sửa.")

    try:
        result = gemini_client.inpaint(
            image_bytes=image_bytes,
            image_mime=image.content_type or "image/png",
            mask_bytes=mask_bytes,
            instruction=instruction,
            model_key=model,
            resolution=resolution,
        )
    except gemini_client.GeminiError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return JSONResponse({
        "seed":           result.seed,
        "image_url":      result.image_url,
        "image_filename": result.image_filename,
    })


# ── Analyze Mood (gợi ý thông số colour-grading, text-only) ──────────────────
@app.post("/api/analyze-mood")
async def api_analyze_mood(
    image: UploadFile = File(...),
    mood: str = Form(...),
    model: str = Form(config.DEFAULT_MODEL_KEY),
):
    """Phân tích ảnh và đề xuất 4 thông số màu cho slider hậu kỳ (không sinh ảnh mới).

    Rẻ hơn đáng kể so với render/enhance vì chỉ dùng Gemini text-only mode.
    """
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Thiếu ảnh đầu vào.")
    try:
        result = gemini_client.analyze_mood(
            image_bytes=image_bytes,
            image_mime=image.content_type or "image/png",
            mood_key=mood,
            model_key=model,
        )
    except gemini_client.GeminiError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return JSONResponse(result)


# ── Enhance (AI nâng cao chất lượng) ─────────────────────────────────────────
@app.post("/api/enhance")
async def api_enhance(
    image: UploadFile = File(...),
    model: str = Form(config.DEFAULT_MODEL_KEY),
    resolution: str = Form(config.DEFAULT_RESOLUTION),
    seed: str = Form(""),
):
    """Nâng cao chất lượng ảnh render: texture sắc nét, PBR chuẩn, lighting tốt hơn.
    Tốn 1 Gemini API call (~$0.04–0.15 tùy model).
    """
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Thiếu ảnh đầu vào.")

    try:
        result = gemini_client.enhance(
            image_bytes=image_bytes,
            image_mime=image.content_type or "image/png",
            model_key=model,
            resolution=resolution,
            seed=seed.strip() or None,
        )
    except gemini_client.GeminiError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return JSONResponse({
        "seed":           result.seed,
        "image_url":      result.image_url,
        "image_filename": result.image_filename,
    })


# ── Static (đặt SAU các route API) ───────────────────────────────────────────
@app.get("/")
def index():
    return FileResponse(config.FRONTEND_DIR / "index.html")


app.mount("/outputs", StaticFiles(directory=str(config.OUTPUTS_DIR)), name="outputs")
app.mount("/", StaticFiles(directory=str(config.FRONTEND_DIR), html=True), name="frontend")
