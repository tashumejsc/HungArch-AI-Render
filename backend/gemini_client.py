"""Wrapper gọi Google Gemini Image cho HungArch AI Render.

Cung cấp 2 thao tác chính:
- render():  ảnh SketchUp (+ ảnh tham chiếu tùy chọn) -> ảnh photorealistic.
- inpaint(): ảnh render + mask + chỉ thị -> sửa cục bộ vùng được đánh dấu.

Mỗi kết quả được lưu ra outputs/<seed>.png kèm outputs/<seed>.json (metadata).
"""
from __future__ import annotations

import io

from PIL import Image

from google import genai
from google.genai import types

import config
import prompts
from store import RenderResult, new_token, save_result


class GeminiError(RuntimeError):
    """Lỗi thân thiện hiển thị được cho người dùng cuối."""


# --- Client khởi tạo lười (lazy) để app vẫn boot được khi chưa có API key ---
_client: genai.Client | None = None
_client_key: str | None = None


def _get_client() -> genai.Client:
    global _client, _client_key
    if not config.GEMINI_API_KEY:
        raise GeminiError(
            "Chưa cấu hình GEMINI_API_KEY. Hãy nhập khóa ở mục '🔑 Cấu hình khóa API' "
            "trong app (hoặc điền vào file .env). Lấy khóa miễn phí tại Google AI Studio."
        )
    # Dựng lại client nếu khóa được đổi lúc đang chạy (từ giao diện).
    if _client is None or _client_key != config.GEMINI_API_KEY:
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
        _client_key = config.GEMINI_API_KEY
    return _client


def _to_part(image_bytes: bytes, mime: str = "image/png") -> types.Part:
    return types.Part.from_bytes(data=image_bytes, mime_type=mime)


def _aspect_from_bytes(image_bytes: bytes) -> str:
    try:
        with Image.open(io.BytesIO(image_bytes)) as im:
            return config.closest_aspect_ratio(im.width, im.height)
    except Exception:
        return "1:1"


def _extract_image(response) -> bytes:
    """Lấy bytes ảnh đầu tiên từ response của Gemini."""
    candidates = getattr(response, "candidates", None) or []
    for cand in candidates:
        content = getattr(cand, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            inline = getattr(part, "inline_data", None)
            if inline and getattr(inline, "data", None):
                return inline.data
    # Không có ảnh -> thường do bị chặn nội dung hoặc model trả về text.
    text = getattr(response, "text", None)
    raise GeminiError(
        "Gemini không trả về ảnh. " + (f"Phản hồi: {text}" if text else
        "Có thể nội dung bị từ chối hoặc ảnh đầu vào không hợp lệ. Thử lại với mô tả khác.")
    )


def _build_image_config(aspect_ratio: str, resolution: str):
    """Dựng ImageConfig một cách phòng thủ.

    SDK / model Gemini Image còn thay đổi nhanh: một số field (vd image_size) có
    thể chưa được hỗ trợ. Thử lần lượt từ đầy đủ -> tối giản -> None để app không vỡ.
    """
    size = resolution if resolution in config.VALID_RESOLUTIONS else config.DEFAULT_RESOLUTION
    for kwargs in (
        {"aspect_ratio": aspect_ratio, "image_size": size},
        {"aspect_ratio": aspect_ratio},
        {},
    ):
        try:
            return types.ImageConfig(**kwargs) if kwargs else None
        except Exception:
            continue
    return None


def _build_config(aspect_ratio: str, resolution: str):
    """Dựng GenerateContentConfig, có dự phòng nếu field không được hỗ trợ."""
    image_config = _build_image_config(aspect_ratio, resolution)
    for kwargs in (
        {"response_modalities": ["IMAGE"], "image_config": image_config},
        {"response_modalities": ["IMAGE"]},
        {"image_config": image_config},
        {},
    ):
        # Loại bỏ image_config=None để không truyền field thừa.
        clean = {k: v for k, v in kwargs.items() if v is not None}
        try:
            return types.GenerateContentConfig(**clean) if clean else None
        except Exception:
            continue
    return None


def _generate(model_key: str, parts: list, aspect_ratio: str, resolution: str):
    client = _get_client()
    cfg = _build_config(aspect_ratio, resolution)
    try:
        return client.models.generate_content(
            model=config.model_id(model_key),
            contents=parts,
            config=cfg,
        )
    except GeminiError:
        raise
    except Exception as exc:  # gói lỗi SDK/mạng thành thông báo gọn
        raise GeminiError(f"Lỗi khi gọi Gemini: {exc}") from exc


def render(
    *,
    mode: str,
    image_bytes: bytes,
    image_mime: str,
    prompt_text: str,
    reference_bytes: bytes | None = None,
    reference_mime: str = "image/png",
    model_key: str = config.DEFAULT_MODEL_KEY,
    resolution: str = config.DEFAULT_RESOLUTION,
    seed: str | None = None,
) -> RenderResult:
    """Biến ảnh khối SketchUp thành ảnh render photorealistic."""
    seed = seed or new_token()
    aspect = _aspect_from_bytes(image_bytes)

    parts: list = [_to_part(image_bytes, image_mime)]
    full_prompt = prompt_text
    if reference_bytes:
        parts.append(_to_part(reference_bytes, reference_mime))
        full_prompt = f"{prompt_text}\n\n{prompts.REFERENCE_INSTRUCTION}"
    parts.append(full_prompt)

    response = _generate(model_key, parts, aspect, resolution)
    img = _extract_image(response)
    return save_result(img, display_seed=seed, prompt_used=full_prompt, meta={
        "engine": "gemini",
        "mode": mode,
        "model": config.model_id(model_key),
        "resolution": resolution,
        "aspect_ratio": aspect,
        "has_reference": bool(reference_bytes),
    })


def inpaint(
    *,
    image_bytes: bytes,
    image_mime: str,
    mask_bytes: bytes,
    instruction: str,
    model_key: str = config.DEFAULT_MODEL_KEY,
    resolution: str = config.DEFAULT_RESOLUTION,
    seed: str | None = None,
) -> RenderResult:
    """Sửa cục bộ: chỉ chỉnh vùng được đánh dấu (mask magenta), giữ nguyên phần còn lại."""
    seed = seed or new_token()
    aspect = _aspect_from_bytes(image_bytes)
    prompt_text = prompts.build_inpaint_prompt(instruction)

    parts = [
        _to_part(image_bytes, image_mime),
        _to_part(mask_bytes, "image/png"),
        prompt_text,
    ]
    response = _generate(model_key, parts, aspect, resolution)
    img = _extract_image(response)
    return save_result(img, display_seed=seed, prompt_used=prompt_text, meta={
        "engine": "gemini",
        "mode": "inpaint",
        "model": config.model_id(model_key),
        "resolution": resolution,
        "aspect_ratio": aspect,
        "instruction": instruction,
    })
