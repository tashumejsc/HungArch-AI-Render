"""Wrapper gọi Google Gemini Image cho HungArch AI Render.

Cung cấp 4 thao tác:
- render():       ảnh SketchUp (+ ảnh tham chiếu tùy chọn) → ảnh photorealistic.
- enhance():      nâng cao chất lượng ảnh render đã có.
- inpaint():      sửa cục bộ — mask hoặc mô tả văn bản.
- analyze_mood(): phân tích ảnh và đề xuất thông số màu (text-only, không sinh ảnh).

Mỗi kết quả ảnh được lưu ra outputs/<token>.png kèm <token>.json (metadata).
"""
from __future__ import annotations

import io
import json
import re

from PIL import Image

from google import genai
from google.genai import types

import config
import prompts
from store import RenderResult, save_result


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
    except Exception as exc:
        msg = str(exc)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
            model_name = config.model_id(model_key)
            if "limit: 0" in msg or "free_tier" in msg.lower():
                raise GeminiError(
                    f"Model '{model_name}' không có hạn mức miễn phí (free tier = 0 request).\n"
                    "Giải pháp:\n"
                    "① Bật thanh toán (billing) tại console.cloud.google.com → chọn đúng dự án Google Cloud.\n"
                    "② Thử chuyển sang model 'Flash 3.1' — rẻ hơn đáng kể so với Pro 3.0.\n"
                    "③ Kiểm tra hạn mức và chi phí tại aistudio.google.com hoặc console.cloud.google.com."
                ) from exc
            raise GeminiError(
                "Vượt hạn mức Gemini API (429). Đợi 1–2 phút rồi thử lại, "
                "hoặc chuyển sang model Flash 3.1 để giảm chi phí."
            ) from exc
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
    seed: str | None = None,   # không dùng cho Gemini, giữ để tương thích API
) -> RenderResult:
    """Biến ảnh khối SketchUp thành ảnh render photorealistic."""
    aspect = _aspect_from_bytes(image_bytes)

    if reference_bytes:
        # Gắn NHÃN TEXT trước MỖI ảnh để Gemini không nhầm vai trò.
        # Nếu chỉ xếp [img_su, img_ref, prompt] thì Gemini bị hút về ảnh render
        # chi tiết hơn (reference) và copy luôn bố cục → sai hình học.
        full_prompt = f"{prompt_text}\n\n{prompts.REFERENCE_INSTRUCTION}"
        parts: list = [
            "IMAGE 1 below is the PRIMARY INPUT — the SketchUp model. You MUST reproduce its "
            "exact camera angle, geometry, spatial layout and composition in your render:",
            _to_part(image_bytes, image_mime),
            "IMAGE 2 below is a STYLE REFERENCE ONLY. Use it solely to match colour grading, "
            "material finish and lighting mood. DO NOT copy its camera angle, layout, geometry, "
            "furniture, objects, screen/signage content, text or composition:",
            _to_part(reference_bytes, reference_mime),
            full_prompt,
        ]
    else:
        full_prompt = prompt_text
        parts = [_to_part(image_bytes, image_mime), full_prompt]

    response = _generate(model_key, parts, aspect, resolution)
    img = _extract_image(response)
    return save_result(img, prompt_used=full_prompt, meta={
        "engine": "gemini",
        "mode": mode,
        "model": config.model_id(model_key),
        "resolution": resolution,
        "aspect_ratio": aspect,
        "has_reference": bool(reference_bytes),
    })


def enhance(
    *,
    image_bytes: bytes,
    image_mime: str,
    model_key: str = config.DEFAULT_MODEL_KEY,
    resolution: str = config.DEFAULT_RESOLUTION,
    seed: str | None = None,   # không dùng cho Gemini, giữ để tương thích API
) -> RenderResult:
    """Nâng cao chất lượng ảnh render: texture sắc nét, PBR chuẩn, lighting tốt hơn.

    Tốn 1 Gemini API call. Chi phí: ~$0.04 (Flash) / ~$0.15 (Pro) mỗi ảnh.
    """
    aspect = _aspect_from_bytes(image_bytes)
    prompt_text = prompts.ENHANCE_PROMPT

    parts = [_to_part(image_bytes, image_mime), prompt_text]
    response = _generate(model_key, parts, aspect, resolution)
    img = _extract_image(response)
    return save_result(img, prompt_used=prompt_text, meta={
        "engine": "gemini",
        "mode": "enhance",
        "model": config.model_id(model_key),
        "resolution": resolution,
    })


def inpaint(
    *,
    image_bytes: bytes,
    image_mime: str,
    mask_bytes: bytes | None,
    instruction: str,
    model_key: str = config.DEFAULT_MODEL_KEY,
    resolution: str = config.DEFAULT_RESOLUTION,
    seed: str | None = None,
) -> RenderResult:
    """Sửa cục bộ.

    mask_bytes=None  → chỉnh sửa thuần văn bản (AI hiểu từ nhãn phòng / mô tả).
    mask_bytes=bytes → chỉnh vùng đánh dấu magenta, giữ nguyên phần còn lại.
    """
    aspect = _aspect_from_bytes(image_bytes)

    if mask_bytes is not None:
        prompt_text = prompts.build_inpaint_prompt(instruction)
        parts = [
            _to_part(image_bytes, image_mime),
            _to_part(mask_bytes, "image/png"),
            prompt_text,
        ]
        edit_mode = "inpaint"
    else:
        prompt_text = prompts.build_text_edit_prompt(instruction)
        parts = [_to_part(image_bytes, image_mime), prompt_text]
        edit_mode = "text_edit"

    response = _generate(model_key, parts, aspect, resolution)
    img = _extract_image(response)
    return save_result(img, prompt_used=prompt_text, meta={
        "engine": "gemini",
        "mode": edit_mode,
        "model": config.model_id(model_key),
        "resolution": resolution,
        "aspect_ratio": aspect,
        "instruction": instruction,
    })


def analyze_mood(
    *,
    image_bytes: bytes,
    image_mime: str,
    mood_key: str,
    model_key: str = config.DEFAULT_MODEL_KEY,
) -> dict:
    """Phân tích ảnh và đề xuất 4 thông số màu cho giao diện hậu kỳ (text-only, không sinh ảnh).

    Trả về dict: {"brightness": int, "contrast": int, "saturate": int, "warmth": int}
    tương ứng range các slider trong app.js.
    """
    client = _get_client()
    prompt_text = prompts.build_mood_analysis_prompt(mood_key)
    parts = [_to_part(image_bytes, image_mime), prompt_text]

    try:
        # Không yêu cầu IMAGE modality — chỉ cần text JSON
        cfg = types.GenerateContentConfig(response_mime_type="application/json")
        response = client.models.generate_content(
            model=config.model_id(model_key),
            contents=parts,
            config=cfg,
        )
    except Exception:
        # Fallback: gọi không có config đặc biệt
        try:
            response = client.models.generate_content(
                model=config.model_id(model_key),
                contents=parts,
            )
        except Exception as exc:
            raise GeminiError(f"Lỗi phân tích mood màu: {exc}") from exc

    text = (getattr(response, "text", None) or "").strip()
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        m = re.search(r'\{[^{}]+\}', text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group())
            except Exception:
                raise GeminiError("AI không trả về đúng định dạng JSON. Thử lại.")
        else:
            raise GeminiError("AI không trả về dữ liệu màu hợp lệ. Thử lại với mood khác.")

    required = {"brightness", "contrast", "saturate", "warmth"}
    if not required.issubset(set(data.keys())):
        raise GeminiError("Phản hồi AI thiếu trường dữ liệu. Thử lại.")

    # Clamp vào range hợp lệ của từng slider
    ranges = {"brightness": (70, 130), "contrast": (70, 140), "saturate": (0, 150), "warmth": (0, 50)}
    result = {}
    for k, (lo, hi) in ranges.items():
        try:
            v = int(round(float(data[k])))
        except (TypeError, ValueError):
            raise GeminiError(f"Giá trị '{k}' không hợp lệ trong phản hồi AI.")
        result[k] = max(lo, min(hi, v))
    return result
