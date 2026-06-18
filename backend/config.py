"""Cấu hình chung cho HungArch AI Render.

Đọc biến môi trường từ file .env (đặt ở thư mục gốc dự án) và cung cấp
các hằng số dùng chung: API key, danh sách model, độ phân giải, thư mục output.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Thư mục gốc dự án = cha của thư mục backend/
ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
OUTPUTS_DIR = ROOT_DIR / "outputs"

# Nạp .env (nếu có). Không ghi đè biến môi trường đã tồn tại trong hệ thống.
load_dotenv(ROOT_DIR / ".env")

# Chấp nhận cả GEMINI_API_KEY lẫn GOOGLE_API_KEY cho tiện.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""

# Các model ảnh của Gemini. "pro" = chất lượng cao (mặc định), "flash" = nhanh/rẻ.
# Có thể chỉnh qua biến môi trường nếu Google đổi tên model.
MODELS = {
    "pro": os.getenv("GEMINI_MODEL_PRO", "gemini-3-pro-image"),
    "flash": os.getenv("GEMINI_MODEL_FLASH", "gemini-3.1-flash-image"),
}
DEFAULT_MODEL_KEY = "pro"

# --- Replicate (engine thay thế: SD/FLUX + ControlNet, có SEED thật) ---
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN") or ""
# Model render giữ hình học bằng ControlNet depth (giữ khối/không gian SketchUp).
REPLICATE_MODEL = os.getenv("REPLICATE_MODEL", "black-forest-labs/flux-depth-dev")
# Model inpaint (sửa cục bộ bằng mask thật).
REPLICATE_INPAINT_MODEL = os.getenv("REPLICATE_INPAINT_MODEL", "black-forest-labs/flux-fill-dev")

ENGINES = {
    "gemini": {"label": "Gemini — Nhanh, dễ dùng", "available": bool(GEMINI_API_KEY)},
    "replicate": {"label": "Replicate — Seed thật + ControlNet (giữ hình học chính xác)", "available": bool(REPLICATE_API_TOKEN)},
}
DEFAULT_ENGINE = "gemini"

# Độ phân giải đầu ra hợp lệ (theo tài liệu Gemini Image: dùng chữ K viết hoa).
VALID_RESOLUTIONS = ["1K", "2K", "4K"]
DEFAULT_RESOLUTION = "2K"

# Tỉ lệ khung hình Gemini hỗ trợ — dùng để "ép" về giá trị gần nhất với ảnh gốc.
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

# Đảm bảo thư mục output tồn tại ngay khi import.
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def model_id(model_key: str | None) -> str:
    """Trả về model id thật từ khóa 'pro'/'flash'. Mặc định = pro."""
    return MODELS.get((model_key or DEFAULT_MODEL_KEY).lower(), MODELS[DEFAULT_MODEL_KEY])


def closest_aspect_ratio(width: int, height: int) -> str:
    """Tìm tỉ lệ khung hình Gemini hỗ trợ gần nhất với ảnh đầu vào.

    Giúp ảnh render giữ đúng bố cục/khung của ảnh SketchUp gốc.
    """
    if not width or not height:
        return "1:1"
    ratio = width / height
    return min(
        SUPPORTED_ASPECT_RATIOS,
        key=lambda label: abs(SUPPORTED_ASPECT_RATIOS[label] - ratio),
    )
