"""Engine Replicate cho HungArch AI Render.

Dùng FLUX + ControlNet depth để giữ hình học khối SketchUp chính xác, và có
SEED THẬT (tái lập 100% giữa các góc). Inpaint dùng flux-fill-dev với mask thật.

Tài liệu model: black-forest-labs/flux-depth-dev, black-forest-labs/flux-fill-dev.
"""
from __future__ import annotations

import io
import urllib.request

from PIL import Image

import config
from store import RenderResult, random_seed, save_result


class ReplicateError(RuntimeError):
    """Lỗi thân thiện hiển thị được cho người dùng cuối."""


_client = None
_client_token: str | None = None


def _get_client():
    global _client, _client_token
    if not config.REPLICATE_API_TOKEN:
        raise ReplicateError(
            "Chưa cấu hình REPLICATE_API_TOKEN. Hãy nhập ở mục '🔑 Cấu hình khóa API' "
            "trong app (hoặc file .env). Lấy token ở https://replicate.com/account/api-tokens."
        )
    if _client is None or _client_token != config.REPLICATE_API_TOKEN:
        try:
            import replicate  # import lười để app vẫn boot nếu chưa cài
        except ImportError as exc:
            raise ReplicateError("Chưa cài thư viện 'replicate'. Chạy: pip install replicate") from exc
        _client = replicate.Client(api_token=config.REPLICATE_API_TOKEN)
        _client_token = config.REPLICATE_API_TOKEN
    return _client


def _coerce_seed(seed: str | None) -> int:
    """Chuyển seed người dùng nhập thành số nguyên; rỗng/không hợp lệ -> ngẫu nhiên."""
    if seed:
        s = seed.strip()
        if s.isdigit():
            return int(s)
    return random_seed()


def _read_output(out) -> bytes:
    """Lấy bytes ảnh từ output của replicate (FileOutput / URL / list / bytes)."""
    if isinstance(out, (list, tuple)):
        if not out:
            raise ReplicateError("Replicate không trả về ảnh nào.")
        out = out[0]
    if isinstance(out, bytes):
        return out
    if hasattr(out, "read"):
        return out.read()
    # còn lại coi như URL chuỗi
    url = str(out)
    with urllib.request.urlopen(url, timeout=120) as resp:
        return resp.read()


def _run(model: str, payload: dict):
    client = _get_client()
    try:
        return client.run(model, input=payload)
    except ReplicateError:
        raise
    except Exception as exc:  # gói lỗi SDK/mạng/billing thành thông báo gọn
        raise ReplicateError(f"Lỗi khi gọi Replicate ({model}): {exc}") from exc


def render(
    *,
    mode: str,
    image_bytes: bytes,
    prompt_text: str,
    seed: str | None = None,
    guidance: float = 10.0,
    steps: int = 28,
    **_ignored,
) -> RenderResult:
    """Render giữ hình học bằng ControlNet depth (giữ khối/không gian SketchUp)."""
    seed_int = _coerce_seed(seed)
    payload = {
        "prompt": prompt_text,
        "control_image": io.BytesIO(image_bytes),  # ảnh SketchUp làm điều kiện depth
        "guidance": guidance,
        "num_inference_steps": steps,
        "megapixels": "1",
        "output_format": "png",
        "num_outputs": 1,
        "seed": seed_int,
    }
    out = _run(config.REPLICATE_MODEL, payload)
    img = _read_output(out)
    return save_result(img, display_seed=str(seed_int), prompt_used=prompt_text, meta={
        "engine": "replicate",
        "mode": mode,
        "model": config.REPLICATE_MODEL,
        "seed_int": seed_int,
    })


def _mask_to_white(mask_bytes: bytes) -> bytes:
    """Chuyển mask magenta-trên-nền-đen (của frontend) thành mask trắng/đen cho flux-fill.

    flux-fill-dev: vùng TRẮNG = vùng sẽ sửa. Mọi pixel không phải đen -> trắng.
    """
    with Image.open(io.BytesIO(mask_bytes)).convert("L") as im:
        bw = im.point(lambda p: 255 if p > 10 else 0)
        buf = io.BytesIO()
        bw.save(buf, format="PNG")
        return buf.getvalue()


def inpaint(
    *,
    image_bytes: bytes,
    mask_bytes: bytes,
    instruction: str,
    seed: str | None = None,
    steps: int = 28,
    **_ignored,
) -> RenderResult:
    """Sửa cục bộ bằng mask thật (flux-fill-dev): vùng được bôi sẽ được tô lại theo chỉ thị."""
    seed_int = _coerce_seed(seed)
    payload = {
        "prompt": instruction,
        "image": io.BytesIO(image_bytes),
        "mask": io.BytesIO(_mask_to_white(mask_bytes)),
        "num_inference_steps": steps,
        "output_format": "png",
        "num_outputs": 1,
        "seed": seed_int,
    }
    out = _run(config.REPLICATE_INPAINT_MODEL, payload)
    img = _read_output(out)
    return save_result(img, display_seed=str(seed_int), prompt_used=instruction, meta={
        "engine": "replicate",
        "mode": "inpaint",
        "model": config.REPLICATE_INPAINT_MODEL,
        "seed_int": seed_int,
        "instruction": instruction,
    })
