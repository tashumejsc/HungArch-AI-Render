"""HungArch AI Render — FastAPI app (Gemini-only, v1.0.0).

10 endpoint API:
  GET  /api/presets           — danh sách preset + model cho frontend
  POST /api/config            — lưu API key
  GET  /api/license           — trạng thái license (trial / licensed / expired)
  POST /api/license/activate  — kích hoạt bằng license key
  POST /api/pdf-preview       — tách PDF → danh sách trang + thumbnail (không render)
  POST /api/render-pdf-page   — render 1 trang PDF theo page_token
  POST /api/render            — render ảnh SketchUp → photorealistic
  POST /api/inpaint           — sửa cục bộ (mask hoặc mô tả văn bản)
  POST /api/analyze-mood      — đề xuất thông số colour-grading (text-only)
  POST /api/enhance           — nâng cao chất lượng ảnh render đã có (AI upscale)
"""
from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
import gemini_client
import image_utils
import license as lic
import pdf_utils
import prompts
import store


class KeyConfig(BaseModel):
    gemini_api_key: str | None = None


app = FastAPI(title="HungArch AI Render", version="1.0.0")


def _require_license() -> None:
    """Ném 403 nếu hết hạn — gọi ở đầu mỗi endpoint sinh ảnh."""
    status = lic.get_status()
    if status["mode"] == "expired":
        raise HTTPException(
            status_code=403,
            detail="Hết hạn dùng thử. Nhập license key trong mục 🔑 để tiếp tục.",
        )


# ── License ───────────────────────────────────────────────────────────────────
@app.get("/api/license")
def get_license():
    return JSONResponse(lic.get_status())


class ActivateBody(BaseModel):
    key: str


@app.post("/api/license/activate")
def activate_license(body: ActivateBody):
    result = lic.activate(body.key.strip())
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return JSONResponse(result)


# ── PDF: preview các trang (KHÔNG render, chỉ tách trang + thumbnail) ────────
@app.post("/api/pdf-preview")
async def api_pdf_preview(pdf: UploadFile = File(...)):
    pdf_bytes = await pdf.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Thiếu file PDF.")
    try:
        pages = pdf_utils.split_pdf_pages(pdf_bytes)
    except pdf_utils.PdfError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    import base64
    session_pages = []
    for p in pages:
        token = store.new_token()
        full_path = config.OUTPUTS_DIR / f"_pdfpage_{token}.png"
        full_path.write_bytes(p.full_png)
        session_pages.append({
            "page_token":        token,
            "page_index":        p.page_index,
            "thumbnail_base64":  base64.b64encode(p.thumbnail_png).decode("ascii"),
            "width_px":          p.width_px,
            "height_px":         p.height_px,
            "paper_label":       p.paper_label,
            "is_blurry":         p.is_blurry,
        })
    return JSONResponse({"page_count": len(pages), "pages": session_pages})


# ── PDF: render 1 trang đã preview, theo page_token ──────────────────────────
@app.post("/api/render-pdf-page")
async def api_render_pdf_page(
    page_token: str = Form(...),
    drawing_mode: str = Form("2d_render"),
    drawing_type: str = Form("autocad"),
    drawing_output: str = Form("floor_plan"),
    is_scan: bool = Form(False),
    style: str = Form(""),
    context: str = Form(""),
    weather: str = Form(""),
    prompt: str = Form(""),
    lighting: str = Form("golden_hour"),
    model: str = Form(config.DEFAULT_MODEL_KEY),
    resolution: str = Form(config.DEFAULT_RESOLUTION),
):
    _require_license()
    full_path = config.OUTPUTS_DIR / f"_pdfpage_{page_token}.png"
    if not full_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Trang PDF không tồn tại hoặc đã hết hạn. Hãy tải lại PDF.",
        )
    image_bytes = full_path.read_bytes()

    prompt_text = prompts.build_drawing_prompt(
        drawing_mode, drawing_type,
        drawing_output=drawing_output,
        style_key=style,
        context_key=context,
        weather_key=weather,
        user_text=prompt,
        lighting_key=lighting,
        is_scan=is_scan,
    )

    try:
        result = gemini_client.render(
            mode="drawing",
            image_bytes=image_bytes,
            image_mime="image/png",
            prompt_text=prompt_text,
            model_key=model,
            resolution=resolution,
        )
    except gemini_client.GeminiError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    # 2D render: overlay original CAD linework to restore exact geometry.
    # Gemini's generative pipeline loses pixel positions at encoding — this
    # composites the original walls/dimensions/text back on top of AI color fills.
    if drawing_mode == "2d_render":
        result_path = config.OUTPUTS_DIR / result.image_filename
        composited = image_utils.overlay_linework(
            colorized_bytes=result_path.read_bytes(),
            original_bytes=image_bytes,
        )
        result_path.write_bytes(composited)

    return JSONResponse({
        "seed":           result.seed,
        "image_url":      result.image_url,
        "image_filename": result.image_filename,
        "prompt_used":    result.prompt_used,
        "page_token":     page_token,
    })


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
    drawing_output: str = Form("interior"),            # "interior" | "exterior" | "floor_plan" | "site_plan"
    is_scan: bool = Form(False),                       # True = ảnh chụp/scan PDF chất lượng thấp
    model: str = Form(config.DEFAULT_MODEL_KEY),
    resolution: str = Form(config.DEFAULT_RESOLUTION),
    seed: str = Form(""),
    lighting: str = Form("golden_hour"),
    vegetation: str = Form("moderate"),
    reference_image: UploadFile | None = File(None),
):
    _require_license()
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
            is_scan=is_scan,
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

    # 2D drawing mode: overlay original CAD linework to restore exact geometry.
    # Gemini's generative pipeline loses pixel positions at encoding — this
    # composites the original walls/dimensions/text back on top of AI color fills.
    if mode == "drawing" and drawing_mode == "2d_render":
        result_path = config.OUTPUTS_DIR / result.image_filename
        composited = image_utils.overlay_linework(
            colorized_bytes=result_path.read_bytes(),
            original_bytes=image_bytes,
        )
        result_path.write_bytes(composited)

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
    _require_license()
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
    _require_license()
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
    _require_license()
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
