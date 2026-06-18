"""Lưu trữ kết quả render dùng chung cho mọi engine (Gemini, Replicate).

Tách riêng để các client không trùng lặp logic lưu ảnh + metadata.
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
    seed: str          # mã hiển thị cho người dùng (Gemini: mã truy vết; Replicate: seed thật)
    image_filename: str
    image_url: str
    prompt_used: str


def new_token() -> str:
    """Mã định danh ngắn, duy nhất — dùng đặt tên file (tránh trùng)."""
    return f"HA{int(time.time())}{secrets.token_hex(2)}".upper()


def random_seed() -> int:
    """Seed số nguyên ngẫu nhiên (cho engine hỗ trợ seed thật như Replicate)."""
    return secrets.randbelow(2_147_483_647)


def save_result(image_bytes: bytes, *, display_seed: str, prompt_used: str, meta: dict) -> RenderResult:
    token = new_token()
    png_path = config.OUTPUTS_DIR / f"{token}.png"
    try:
        with Image.open(io.BytesIO(image_bytes)) as im:
            im.save(png_path, format="PNG")
    except Exception:
        png_path.write_bytes(image_bytes)

    record = {
        "token": token,
        "seed": display_seed,
        "prompt": prompt_used,
        "created": time.time(),
        **meta,
    }
    (config.OUTPUTS_DIR / f"{token}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return RenderResult(
        seed=str(display_seed),
        image_filename=png_path.name,
        image_url=f"/outputs/{png_path.name}",
        prompt_used=prompt_used,
    )
