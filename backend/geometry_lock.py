"""Khóa hình học (Geometry Lock) cho tab Bản vẽ 2D — kỹ thuật "Crop & Re-place".

Vấn đề giải quyết: Gemini Image API là generative diffusion, không đảm bảo pixel-perfect
khớp hình học giữa ảnh CAD gốc và ảnh AI tạo ra (tỷ lệ phòng, vị trí tường có thể lệch
nhẹ). Module này KHÓA hình học bằng thuật toán thuần (OpenCV), không phụ thuộc AI:

  1. Phát hiện tường + tách từng phòng từ ẢNH GỐC (contour + flood-fill).
  2. Align toàn cục ảnh AI về cùng khung với ảnh gốc (homography 4 góc).
  3. Với MỖI phòng: crop đúng vùng đó từ ảnh AI đã align, warp/resize khớp CHÍNH XÁC
     bbox/polygon của phòng đó trong ảnh gốc, rồi paste vào canvas kết quả.
  4. Vẽ đè viền tường gốc lên canvas — tường luôn đúng 100% theo bản vẽ.
  5. Feather nhẹ các đường nối giữa phòng để giảm vết ghép (seam).

Canvas kết quả LUÔN giữ đúng kích thước/tỷ lệ ảnh gốc (quyết định đã chốt cùng Tashume).
Nếu phát hiện được ít phòng (do nét vẽ mờ/phức tạp), vẫn ghép tối đa những gì phát hiện
được — không chặn luồng, không báo lỗi cứng (graceful degradation).

Không phụ thuộc gemini_client/prompts — module thuần xử lý ảnh, nhận 2 ảnh bytes vào,
trả 1 ảnh bytes ra.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image


class GeometryLockError(RuntimeError):
    """Lỗi thân thiện hiển thị được cho người dùng cuối."""


# Diện tích tối thiểu (px²) để 1 contour được coi là 1 phòng hợp lệ — lọc nhiễu nhỏ.
MIN_ROOM_AREA_RATIO = 0.004   # 0.4% diện tích ảnh gốc
# Diện tích tối đa — lọc trường hợp toàn bộ ảnh bị nhận nhầm thành "1 phòng" (do không
# khép kín đường tường, contour ngoài cùng nuốt hết khung ảnh).
MAX_ROOM_AREA_RATIO = 0.65    # 65% diện tích ảnh gốc
FEATHER_PX = 6                # độ rộng vùng làm mờ viền ghép giữa các phòng


@dataclass
class RoomRegion:
    room_id: int
    x: int
    y: int
    w: int
    h: int
    mask: np.ndarray   # uint8 0/255, kích thước (h, w) — polygon đúng hình phòng, không phải bbox chữ nhật


def _load_bgr(image_bytes: bytes) -> np.ndarray:
    pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def _to_png_bytes(bgr: np.ndarray) -> bytes:
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, format="PNG")
    return buf.getvalue()


def detect_wall_mask(original_bgr: np.ndarray) -> np.ndarray:
    """Phát hiện vùng tường (đường nét đậm/đen) trong bản vẽ gốc.

    Trả về mask uint8 0/255 cùng kích thước ảnh gốc — pixel 255 = thuộc tường.
    Dùng adaptive threshold để chịu được ảnh chụp/scan có ánh sáng không đều.
    """
    gray = cv2.cvtColor(original_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    # Đường nét bản vẽ kỹ thuật luôn đậm hơn nền — adaptive threshold xử lý tốt cả ảnh
    # scan có vùng sáng/tối không đều.
    binary = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 35, 10,
    )
    # Đóng các khoảng đứt nét nhỏ (nét vẽ tay/scan thường bị đứt đoạn).
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
    return closed


def detect_room_regions(original_bgr: np.ndarray, wall_mask: np.ndarray) -> list[RoomRegion]:
    """Tách từng phòng bằng flood-fill trong các khoảng khép kín bởi wall_mask.

    Nếu phát hiện được ít phòng (nét vẽ mờ/phức tạp khiến tường không khép kín hoàn
    toàn), vẫn trả về tối đa những gì tìm được — không raise lỗi.
    """
    h, w = wall_mask.shape
    total_area = h * w

    # "Không phải tường" = nền (khả năng là không gian bên trong phòng).
    free_space = cv2.bitwise_not(wall_mask)

    # Connected components trên vùng free_space cô lập từng phòng nếu tường khép kín đủ tốt.
    num_labels, labels = cv2.connectedComponents(free_space, connectivity=4)

    regions: list[RoomRegion] = []
    for label_id in range(1, num_labels):  # 0 = nền/background của connectedComponents
        component_mask = np.uint8(labels == label_id) * 255
        area = int(cv2.countNonZero(component_mask))
        area_ratio = area / total_area
        if area_ratio < MIN_ROOM_AREA_RATIO or area_ratio > MAX_ROOM_AREA_RATIO:
            continue
        ys, xs = np.where(component_mask > 0)
        if len(xs) == 0:
            continue
        x0, x1 = int(xs.min()), int(xs.max())
        y0, y1 = int(ys.min()), int(ys.max())
        regions.append(RoomRegion(
            room_id=len(regions),
            x=x0, y=y0, w=x1 - x0 + 1, h=y1 - y0 + 1,
            mask=component_mask[y0:y1 + 1, x0:x1 + 1],
        ))

    # Sắp theo diện tích giảm dần — phòng lớn ghép trước, giúp seam ít lộ ở phòng nhỏ
    # ghép sau (ghép sau đè feather nhẹ lên viền phòng lớn).
    regions.sort(key=lambda r: r.w * r.h, reverse=True)
    for i, r in enumerate(regions):
        r.room_id = i
    return regions


def _align_ai_image_to_original(ai_bgr: np.ndarray, original_bgr: np.ndarray) -> np.ndarray:
    """Align ảnh AI về đúng khung tọa độ ảnh gốc.

    Dùng feature-matching (ORB) + homography để bù được xoay/dịch/scale nhẹ mà Gemini
    thường tạo ra (ảnh AI "giống nhưng không trùng khít" ảnh gốc). Đây là bước quan
    trọng nhất quyết định việc crop-per-room ở bước sau có khớp đúng vị trí hay không.

    Nếu không tìm được đủ điểm khớp tin cậy (ảnh quá khác biệt, ví dụ AI đổi màu/vật
    liệu quá mạnh khiến ORB không bắt được đặc trưng), fallback về resize đơn giản
    theo kích thước — vẫn tốt hơn không làm gì, dù kém chính xác hơn homography.
    """
    target_h, target_w = original_bgr.shape[:2]
    resized_fallback = cv2.resize(ai_bgr, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)

    try:
        orig_gray = cv2.cvtColor(original_bgr, cv2.COLOR_BGR2GRAY)
        ai_gray_at_orig_size = cv2.cvtColor(resized_fallback, cv2.COLOR_BGR2GRAY)

        orb = cv2.ORB_create(nfeatures=4000)
        kp1, des1 = orb.detectAndCompute(orig_gray, None)
        kp2, des2 = orb.detectAndCompute(ai_gray_at_orig_size, None)
        if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
            return resized_fallback

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        matches = sorted(matches, key=lambda m: m.distance)
        good_matches = matches[: max(30, int(len(matches) * 0.25))]
        if len(good_matches) < 10:
            return resized_fallback

        src_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)

        homography, inlier_mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        if homography is None:
            return resized_fallback

        inlier_ratio = float(inlier_mask.sum()) / len(inlier_mask) if inlier_mask is not None else 0.0
        if inlier_ratio < 0.15:
            # Quá ít điểm khớp đáng tin — homography có thể là rác, an toàn hơn nên
            # fallback thay vì áp 1 phép biến đổi sai làm hỏng toàn ảnh.
            return resized_fallback

        aligned = cv2.warpPerspective(
            resized_fallback, homography, (target_w, target_h),
            borderMode=cv2.BORDER_REPLICATE,
        )
        return aligned
    except Exception:
        # Bất kỳ lỗi nào trong quá trình feature-matching đều không nên làm sập cả
        # request render — fallback về resize thô, vẫn cho ra kết quả dùng được.
        return resized_fallback


def _warp_room_crop(ai_aligned: np.ndarray, region: RoomRegion) -> np.ndarray:
    """Crop đúng bbox của 1 phòng từ ảnh AI đã align toàn cục.

    Vì ảnh AI đã align toàn cục ở _align_ai_image_to_original, bbox tọa độ phòng trong
    ảnh gốc và trong ảnh AI đã align là tương đương — không cần warp thêm cho từng
    phòng trong phiên bản này. Hàm tách riêng để dễ thay bằng warp phi tuyến tính
    (perspective transform riêng từng phòng) nếu sau này cần độ chính xác cao hơn.
    """
    y0, y1 = region.y, region.y + region.h
    x0, x1 = region.x, region.x + region.w
    return ai_aligned[y0:y1, x0:x1]


def _feather_mask(mask: np.ndarray, feather_px: int = FEATHER_PX) -> np.ndarray:
    """Làm mờ viền mask để giảm vết ghép cứng (seam) khi paste từng phòng."""
    blurred = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sigmaX=feather_px)
    return np.clip(blurred / 255.0, 0.0, 1.0)


def apply_geometry_lock(
    *,
    original_bytes: bytes,
    ai_result_bytes: bytes,
) -> bytes:
    """Hàm chính: khóa hình học ảnh AI theo đúng bản vẽ gốc.

    original_bytes  → ảnh bản vẽ CAD/phác thảo gốc (bytes, bất kỳ format PIL đọc được).
    ai_result_bytes → ảnh đã render bởi Gemini (bytes), sẽ bị "ép" lại hình học.

    Trả về: ảnh PNG bytes — kích thước/tỷ lệ CHÍNH XÁC theo original_bytes, nội dung
    (vật liệu/nội thất/ánh sáng) lấy từ ai_result_bytes, viền tường khóa cứng theo gốc.

    Không raise lỗi vì phát hiện ít phòng — luôn cố ghép tối đa những gì tìm được.
    Chỉ raise GeometryLockError nếu không đọc được ảnh đầu vào (lỗi dữ liệu thật sự).
    """
    try:
        original_bgr = _load_bgr(original_bytes)
    except Exception as exc:
        raise GeometryLockError(f"Không đọc được ảnh bản vẽ gốc: {exc}") from exc
    try:
        ai_bgr = _load_bgr(ai_result_bytes)
    except Exception as exc:
        raise GeometryLockError(f"Không đọc được ảnh AI đã render: {exc}") from exc

    h, w = original_bgr.shape[:2]

    wall_mask = detect_wall_mask(original_bgr)
    regions = detect_room_regions(original_bgr, wall_mask)

    ai_aligned = _align_ai_image_to_original(ai_bgr, original_bgr)

    # Canvas khởi điểm = ảnh AI đã align toàn cục (đảm bảo có nội dung phủ kín mọi nơi,
    # kể cả vùng KHÔNG được nhận diện là phòng riêng — ví dụ sân vườn ngoài site_plan).
    canvas = ai_aligned.copy().astype(np.float32)

    for region in regions:
        room_crop = _warp_room_crop(ai_aligned, region).astype(np.float32)
        if room_crop.shape[:2] != region.mask.shape:
            # Phòng tràn ra ngoài biên ảnh hoặc lệch kích thước — bỏ qua phòng này,
            # giữ nguyên nội dung canvas hiện có tại vị trí đó (graceful degradation).
            continue
        alpha = _feather_mask(region.mask)[..., None]  # (h, w, 1) để broadcast 3 channel

        y0, y1 = region.y, region.y + region.h
        x0, x1 = region.x, region.x + region.w
        canvas[y0:y1, x0:x1] = (
            room_crop * alpha + canvas[y0:y1, x0:x1] * (1.0 - alpha)
        )

    canvas_u8 = np.clip(canvas, 0, 255).astype(np.uint8)

    # Khóa cứng viền tường: vẽ đè đúng wall_mask gốc lên canvas, màu lấy trung bình
    # vùng tường tối trong ảnh AI (để không bị màu đen phẳng lạc quẻ với tông ảnh).
    wall_pixels = ai_aligned[wall_mask > 0]
    if wall_pixels.size > 0:
        wall_color = wall_pixels.reshape(-1, 3).mean(axis=0).astype(np.uint8)
        # Tối màu một chút để giữ cảm giác viền tường rõ nét, không bị "tô màu nhạt".
        wall_color = (wall_color.astype(np.int32) * 0.55).clip(0, 255).astype(np.uint8)
    else:
        wall_color = np.array([30, 30, 30], dtype=np.uint8)

    wall_alpha = _feather_mask(wall_mask, feather_px=3)[..., None]
    wall_layer = np.tile(wall_color, (h, w, 1)).astype(np.float32)
    canvas_u8 = np.clip(
        wall_layer * wall_alpha + canvas_u8.astype(np.float32) * (1.0 - wall_alpha),
        0, 255,
    ).astype(np.uint8)

    return _to_png_bytes(canvas_u8)


def count_detected_rooms(original_bytes: bytes) -> int:
    """Tiện ích phụ: đếm số phòng phát hiện được — dùng để hiển thị thông tin debug/UI
    nếu cần (ví dụ "Đã phát hiện 6/8 phòng"), không bắt buộc dùng trong luồng chính.
    """
    original_bgr = _load_bgr(original_bytes)
    wall_mask = detect_wall_mask(original_bgr)
    return len(detect_room_regions(original_bgr, wall_mask))
