"""HungArch AI Render — FastAPI app.

Phục vụ frontend tĩnh và 3 endpoint API: /api/presets, /api/render, /api/inpaint.
Chạy: uvicorn backend.main:app  (hoặc dùng run.bat).
"""
from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
import gemini_client
import prompts
import replicate_client


class KeyConfig(BaseModel):
    gemini_api_key: str | None = None
    replicate_api_token: str | None = None

app = FastAPI(title="HungArch AI Render", version="1.1.0")


# ---------- API ----------
@app.get("/api/presets")
def get_presets():
    """Danh sách preset + cấu hình engine/model/độ phân giải cho frontend."""
    return {
        **prompts.presets_payload(),
        "engines": [
            {"key": k, "label": v["label"], "available": v["available"]}
            for k, v in config.ENGINES.items()
        ],
        "default_engine": config.DEFAULT_ENGINE,
        "models": [
            {"key": "pro", "label": "Pro — Chất lượng cao (chậm hơn)"},
            {"key": "flash", "label": "Flash — Nhanh / tiết kiệm"},
        ],
        "resolutions": config.VALID_RESOLUTIONS,
        "default_resolution": config.DEFAULT_RESOLUTION,
        "api_key_configured": bool(config.GEMINI_API_KEY),
        "replicate_configured": bool(config.REPLICATE_API_TOKEN),
    }


@app.post("/api/config")
def set_config(body: KeyConfig):
    """Nhập/cập nhật khóa API ngay trong app (lưu xuống .env). Không trả lại khóa."""
    config.set_keys(gemini=body.gemini_api_key, replicate=body.replicate_api_token)
    return {
        "api_key_configured": bool(config.GEMINI_API_KEY),
        "replicate_configured": bool(config.REPLICATE_API_TOKEN),
    }


@app.post("/api/render")
async def api_render(
    mode: str = Form(...),
    image: UploadFile = File(...),
    style: str = Form(""),
    context: str = Form(""),
    weather: str = Form(""),
    prompt: str = Form(""),
    engine: str = Form(config.DEFAULT_ENGINE),
    model: str = Form("pro"),
    resolution: str = Form(config.DEFAULT_RESOLUTION),
    seed: str = Form(""),
    reference_image: UploadFile | None = File(None),
):
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Thiếu ảnh SketchUp đầu vào.")

    if mode == "interior":
        prompt_text = prompts.build_interior_prompt(style, prompt)
    elif mode == "exterior":
        prompt_text = prompts.build_exterior_prompt(context, weather, prompt)
    else:
        raise HTTPException(status_code=400, detail="mode phải là 'interior' hoặc 'exterior'.")

    ref_bytes = None
    ref_mime = "image/png"
    if reference_image is not None:
        ref_bytes = await reference_image.read()
        ref_mime = reference_image.content_type or "image/png"
        if not ref_bytes:
            ref_bytes = None

    try:
        if engine == "replicate":
            result = replicate_client.render(
                mode=mode,
                image_bytes=image_bytes,
                prompt_text=prompt_text,
                seed=seed.strip() or None,
            )
        else:
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
    except (gemini_client.GeminiError, replicate_client.ReplicateError) as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return JSONResponse({
        "seed": result.seed,
        "image_url": result.image_url,
        "image_filename": result.image_filename,
        "prompt_used": result.prompt_used,
    })


@app.post("/api/inpaint")
async def api_inpaint(
    image: UploadFile = File(...),
    mask: UploadFile = File(...),
    instruction: str = Form(...),
    engine: str = Form(config.DEFAULT_ENGINE),
    model: str = Form("pro"),
    resolution: str = Form(config.DEFAULT_RESOLUTION),
    seed: str = Form(""),
):
    image_bytes = await image.read()
    mask_bytes = await mask.read()
    if not image_bytes or not mask_bytes:
        raise HTTPException(status_code=400, detail="Thiếu ảnh hoặc mask.")
    if not instruction.strip():
        raise HTTPException(status_code=400, detail="Hãy nhập chỉ thị sửa vùng đã chọn.")

    try:
        if engine == "replicate":
            result = replicate_client.inpaint(
                image_bytes=image_bytes,
                mask_bytes=mask_bytes,
                instruction=instruction,
                seed=seed.strip() or None,
            )
        else:
            result = gemini_client.inpaint(
                image_bytes=image_bytes,
                image_mime=image.content_type or "image/png",
                mask_bytes=mask_bytes,
                instruction=instruction,
                model_key=model,
                resolution=resolution,
            )
    except (gemini_client.GeminiError, replicate_client.ReplicateError) as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return JSONResponse({
        "seed": result.seed,
        "image_url": result.image_url,
        "image_filename": result.image_filename,
    })


# ---------- Static (đặt SAU các route API) ----------
@app.get("/")
def index():
    return FileResponse(config.FRONTEND_DIR / "index.html")


app.mount("/outputs", StaticFiles(directory=str(config.OUTPUTS_DIR)), name="outputs")
app.mount("/", StaticFiles(directory=str(config.FRONTEND_DIR), html=True), name="frontend")
