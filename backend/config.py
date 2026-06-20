"""Cấu hình chung cho HungArch AI Render.

Đọc biến môi trường từ file .env và cung cấp hằng số dùng chung:
API key, danh sách model Gemini, độ phân giải, thư mục output.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
OUTPUTS_DIR = ROOT_DIR / "outputs"

load_dotenv(ROOT_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""

# Model Gemini hỗ trợ sinh ảnh (IMAGE response modality).
# Lưu ý: gemini-2.5-*-preview là chat model, KHÔNG hỗ trợ sinh ảnh → đã xóa.
# Có thể ghi đè từng model qua biến môi trường nếu Google đổi tên.
MODELS: dict[str, str] = {
    "flash": os.getenv("GEMINI_MODEL_FLASH", "gemini-3.1-flash-image"),
    "pro":   os.getenv("GEMINI_MODEL_PRO",   "gemini-3-pro-image"),
}

MODEL_LABELS: dict[str, str] = {
    "flash": "Flash 3.1 — Nhanh, tiết kiệm (khuyên dùng)",
    "pro":   "Pro 3.0 — Chất lượng cao nhất (tốn token hơn)",
}
DEFAULT_MODEL_KEY = "flash"

# Chỉ Gemini — Replicate đã bị loại bỏ (output không đạt yêu cầu thực tế).
ENGINES = {
    "gemini": {"label": "Gemini Image API", "available": bool(GEMINI_API_KEY)},
}
DEFAULT_ENGINE = "gemini"

VALID_RESOLUTIONS = ["1K", "2K", "4K"]
DEFAULT_RESOLUTION = "2K"

SUPPORTED_ASPECT_RATIOS = {
    "1:1": 1 / 1,
    "2:3": 2 / 3,
    "3:2": 3 / 2,
    "3:4": 3 / 4,
    "4:3": 4 / 3,
    "4:5": 4 / 5,
    "5:4": 5 / 4,
    "9:16": 9 / 16,
    "16:9": 16 / 9,
    "21:9": 21 / 9,
}

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
ENV_PATH = ROOT_DIR / ".env"


def _update_env_file(updates: dict[str, str]) -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    seen = set()
    out = []
    for line in lines:
        head = line.split("=", 1)[0].strip()
        if head in updates:
            out.append(f"{head}={updates[head]}")
            seen.add(head)
        else:
            out.append(line)
    for k, v in updates.items():
        if k not in seen:
            out.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")


def set_keys(gemini: str | None = None, **_ignored) -> None:
    """Cập nhật Gemini API key lúc đang chạy và lưu xuống .env."""
    global GEMINI_API_KEY
    updates: dict[str, str] = {}
    if gemini is not None:
        GEMINI_API_KEY = gemini.strip()
        ENGINES["gemini"]["available"] = bool(GEMINI_API_KEY)
        if GEMINI_API_KEY:
            updates["GEMINI_API_KEY"] = GEMINI_API_KEY
    if updates:
        try:
            _update_env_file(updates)
        except Exception:
            pass


def model_id(model_key: str | None) -> str:
    """Trả về model ID thật từ khóa (flash/pro/flash_25/pro_25). Mặc định = flash."""
    return MODELS.get((model_key or DEFAULT_MODEL_KEY).lower(), MODELS[DEFAULT_MODEL_KEY])


def closest_aspect_ratio(width: int, height: int) -> str:
    if not width or not height:
        return "1:1"
    ratio = width / height
    return min(
        SUPPORTED_ASPECT_RATIOS,
        key=lambda label: abs(SUPPORTED_ASPECT_RATIOS[label] - ratio),
    )
