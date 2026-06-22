"""Xử lý PDF cho tab Bản vẽ 2D: tách trang, tạo thumbnail, ước lượng khổ giấy
và phát hiện trang nghi mờ/kém chất lượng.

Không phụ thuộc gemini_client hay prompts — module thuần xử lý ảnh/PDF.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import fitz  # pymupdf
from PIL import Image, ImageFilter


MAX_PDF_PAGES = 30  # giới hạn an toàn, tránh người dùng lỡ tay tải hồ sơ quá dài


class PdfError(RuntimeError):
    """Lỗi thân thiện hiển thị được cho người dùng cuối."""


@dataclass
class PdfPageInfo:
    page_index: int          # 0-based
    thumbnail_png: bytes     # ảnh thumbnail nhỏ, dùng hiển thị UI
    full_png: bytes          # ảnh độ phân giải cao, dùng để render thật
    width_px: int
    height_px: int
    paper_label: str         # ví dụ "A3 ngang", "A4 đứng", "Không xác định"
    is_blurry: bool          # cảnh báo nghi mờ/kém chất lượng


def _paper_label(width_px: int, height_px: int) -> str:
    """Ước lượng khổ giấy từ tỷ lệ khung hình. Chỉ là gợi ý hiển thị UI,
    không ảnh hưởng logic render."""
    ratio = max(width_px, height_px) / max(1, min(width_px, height_px))
    orientation = "ngang" if width_px > height_px else "đứng"
    # Tỷ lệ chuẩn ISO 216 (A-series) ~ 1.414
    if 1.30 <= ratio <= 1.50:
        return f"A-series {orientation}"
    if ratio > 1.50:
        return f"Khổ dài {orientation}"
    return "Gần vuông"


def _is_blurry(pil_image: Image.Image) -> bool:
    """Ước lượng độ sắc nét bằng biến thiên Laplacian xấp xỉ qua PIL
    (không dùng OpenCV để tránh thêm dependency nặng).
    Ngưỡng được chọn thực nghiệm — đây là GỢI Ý cho người dùng, không phải
    kết luận tuyệt đối; false positive/negative đều có thể xảy ra.
    """
    gray = pil_image.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    # Lấy độ lệch chuẩn cường độ biên: ảnh sắc nét có biên rõ -> std cao.
    histogram = edges.histogram()
    total = sum(histogram)
    if total == 0:
        return False
    mean = sum(i * c for i, c in enumerate(histogram)) / total
    variance = sum(((i - mean) ** 2) * c for i, c in enumerate(histogram)) / total
    std_dev = variance ** 0.5
    return std_dev < 18.0  # ngưỡng thực nghiệm, có thể cần tinh chỉnh sau khi test thật


def split_pdf_pages(pdf_bytes: bytes, *, dpi: int = 200, thumb_max_side: int = 300) -> list[PdfPageInfo]:
    """Tách PDF thành danh sách trang, mỗi trang có ảnh full-res + thumbnail.

    dpi=200 cho full_png: đủ chi tiết để Gemini đọc đường nét bản vẽ kỹ thuật,
    không quá nặng cho upload.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise PdfError(f"Không đọc được file PDF: {exc}") from exc

    if doc.page_count == 0:
        raise PdfError("File PDF không có trang nào.")
    if doc.page_count > MAX_PDF_PAGES:
        raise PdfError(
            f"PDF có {doc.page_count} trang, vượt giới hạn {MAX_PDF_PAGES} trang/lần. "
            "Hãy tách file PDF nhỏ hơn trước khi tải lên."
        )

    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    results: list[PdfPageInfo] = []

    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        full_bytes = pix.tobytes("png")

        with Image.open(io.BytesIO(full_bytes)) as im:
            width_px, height_px = im.size
            paper_label = _paper_label(width_px, height_px)
            is_blurry = _is_blurry(im)

            thumb = im.copy()
            thumb.thumbnail((thumb_max_side, thumb_max_side))
            thumb_buf = io.BytesIO()
            thumb.save(thumb_buf, format="PNG")
            thumb_bytes = thumb_buf.getvalue()

        results.append(PdfPageInfo(
            page_index=i,
            thumbnail_png=thumb_bytes,
            full_png=full_bytes,
            width_px=width_px,
            height_px=height_px,
            paper_label=paper_label,
            is_blurry=is_blurry,
        ))

    doc.close()
    return results
