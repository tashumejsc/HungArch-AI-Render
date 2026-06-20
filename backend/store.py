"""Lưu trữ kết quả render cho HungArch AI Render (Gemini engine).

Tách riêng để client không trùng lặp logic lưu ảnh + metadata.
"""
from __future__ import annotations

import io
import json
import secrets
import time
from dataclasses import dataclass

from PIL import Image

import config


@dataclass
class RenderResult:
    seed: str          # = tên file thật trên đĩa (HA<timestamp><hex>), dùng copy/truy vết
    image_filename: str
    image_url: str
    prompt_used: str


def new_token() -> str:
    """Mã định danh ngắn, duy nhất — dùng đặt tên file và làm seed hiển thị."""
    return f"HA{int(time.time())}{secrets.token_hex(2)}".upper()


def save_result(image_bytes: bytes, *, prompt_used: str, meta: dict) -> RenderResult:
    """Lưu ảnh + metadata; trả về RenderResult với seed = chính token tên file."""
    token = new_token()
    png_path = config.OUTPUTS_DIR / f"{token}.png"
    try:
        with Image.open(io.BytesIO(image_bytes)) as im:
            im.save(png_path, format="PNG")
    except Exception:
        png_path.write_bytes(image_bytes)

    record = {
        "token": token,
        "prompt": prompt_used,
        "created": time.time(),
        **meta,
    }
    (config.OUTPUTS_DIR / f"{token}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return RenderResult(
        seed=token,                          # seed = token = tên file, không tách biệt
        image_filename=png_path.name,
        image_url=f"/outputs/{png_path.name}",
        prompt_used=prompt_used,
    )
