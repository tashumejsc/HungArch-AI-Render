"""Thư viện prompt cho HungArch AI Render.

Mỗi lựa chọn trên giao diện (phong cách / bối cảnh / thời tiết) được map sang
một đoạn mô tả tiếng Anh chi tiết — Gemini cho chất lượng tốt nhất với mô tả
tiếng Anh rõ ràng. Đoạn mô tả người dùng tự nhập (tiếng Việt) được nối vào sau,
Gemini vẫn hiểu tốt.

Tất cả prompt đều bắt đầu bằng GEOMETRY_LOCK để bắt buộc giữ nguyên hình học,
góc camera và bố cục của ảnh khối SketchUp gốc.
"""
from __future__ import annotations

# Chỉ thị KHÓA HÌNH HỌC — dùng chung cho mọi render.
GEOMETRY_LOCK = (
    "Transform this rough SketchUp massing / clay model screenshot into a "
    "photorealistic architectural render. CRITICAL: preserve the EXACT geometry, "
    "proportions, scale, camera angle, perspective, framing and composition of the "
    "input image. Do NOT add, remove, move or resize any structural elements, walls, "
    "floors, ceilings, columns, windows, doors or openings. Keep every line and edge "
    "exactly where it is. Only add realistic materials, textures, lighting, shadows, "
    "reflections and fine detail."
)

# Yêu cầu chất lượng đầu ra — nối vào cuối mọi render.
QUALITY_SUFFIX = (
    "Ultra photorealistic, physically based rendering, natural global illumination, "
    "high dynamic range, crisp sharp detail, professional architectural photography, "
    "no text, no watermark, no people unless explicitly requested."
)

# --- TAB 1: NỘI THẤT — phong cách ---
INTERIOR_STYLES: dict[str, dict[str, str]] = {
    "modern": {
        "label": "Hiện đại",
        "prompt": (
            "Modern interior design: clean lines, neutral palette with bold accents, "
            "polished surfaces, designer furniture, large glazing, integrated lighting, "
            "open and airy space."
        ),
    },
    "minimalist": {
        "label": "Tối giản",
        "prompt": (
            "Minimalist interior: very restrained palette of whites, greys and warm "
            "neutrals, uncluttered space, few but refined furniture pieces, hidden "
            "storage, soft diffuse lighting, emphasis on negative space and texture."
        ),
    },
    "japandi": {
        "label": "Japandi",
        "prompt": (
            "Japandi interior blending Japanese wabi-sabi and Scandinavian warmth: "
            "light oak and walnut wood, paper lanterns, low furniture, linen and "
            "natural textiles, muted earthy tones, handcrafted ceramics, calm cozy mood."
        ),
    },
    "neoclassic": {
        "label": "Tân cổ điển",
        "prompt": (
            "Neoclassical interior: elegant symmetry, decorative wall mouldings and "
            "panelling, ornate cornices, crystal chandelier, marble floor, gilded "
            "accents, refined classic furniture, luxurious sophisticated atmosphere."
        ),
    },
    "zen": {
        "label": "Thiền / Á Đông",
        "prompt": (
            "Zen Asian interior: serene meditative space, natural wood and stone, "
            "bamboo, shoji screens, indoor plants and water feature, soft warm indirect "
            "light, harmony with nature, quiet spiritual calm."
        ),
    },
    "tropical": {
        "label": "Nhiệt đới",
        "prompt": (
            "Tropical interior: lush indoor greenery, rattan and teak furniture, natural "
            "fibers, breezy open layout, warm sunlight, vibrant yet relaxed resort mood, "
            "ceiling fans, textured natural materials."
        ),
    },
}

# --- TAB 2: NGOẠI THẤT — bối cảnh Việt Nam ---
EXTERIOR_CONTEXTS: dict[str, dict[str, str]] = {
    "hanoi_old_quarter": {
        "label": "Phố cổ / Ngõ hẻm Hà Nội",
        "prompt": (
            "Set in a narrow Hanoi Old Quarter alley: dense tube houses, tangled "
            "overhead power lines, mossy old walls, street vendors and parked motorbikes, "
            "weathered shutters, vibrant chaotic Vietnamese street life, aged patina."
        ),
    },
    "urban_shophouse": {
        "label": "Shophouse hiện đại đô thị",
        "prompt": (
            "Modern Vietnamese urban shophouse street: contemporary commercial frontage, "
            "glass and aluminium facade, clean sidewalk, neighbouring modern buildings, "
            "tidy busy city context."
        ),
    },
    "tube_house_facade": {
        "label": "Mặt tiền nhà ống tiêu chuẩn",
        "prompt": (
            "Standard Vietnamese tube-house (nha ong) facade on a typical residential "
            "street: tall narrow plot, balconies with railings, tiled or painted "
            "frontage, neighbouring tube houses on both sides, paved road, parked scooters."
        ),
    },
    "northern_village": {
        "label": "Làng quê Bắc Bộ",
        "prompt": (
            "Northern Vietnamese countryside village: traditional rural setting, brick "
            "and tile roofs, banyan tree, lotus pond, green rice paddies, bamboo hedges, "
            "peaceful pastoral atmosphere."
        ),
    },
    "misty_hills": {
        "label": "Cảnh quan đồi núi sương mù",
        "prompt": (
            "Misty mountainous landscape of northern Vietnam: rolling green hills, "
            "terraced fields, drifting fog and low clouds, pine forest, fresh highland "
            "air, serene panoramic nature backdrop."
        ),
    },
    "garden_eco": {
        "label": "Sinh thái miệt vườn",
        "prompt": (
            "Mekong-delta garden (miet vuon) ecological setting: lush fruit orchards, "
            "tropical plants, small canals and water, wooden walkways, abundant greenery, "
            "relaxed riverside countryside mood."
        ),
    },
}

# --- TAB 2: NGOẠI THẤT — thời tiết & ánh sáng ---
EXTERIOR_WEATHER: dict[str, dict[str, str]] = {
    "harsh_sun": {
        "label": "Nắng gắt nhiệt đới",
        "prompt": (
            "Harsh tropical midday sun: bright direct sunlight, hard well-defined "
            "shadows, deep blue sky, high contrast, shimmering heat, vivid saturated "
            "colours."
        ),
    },
    "overcast_after_rain": {
        "label": "Bầu trời u ám sau mưa",
        "prompt": (
            "Overcast sky just after rain: soft diffuse grey light, wet reflective "
            "surfaces and puddles, damp atmosphere, muted cool tones, gentle even shadows."
        ),
    },
    "blue_hour": {
        "label": "Giờ xanh (Blue Hour) lên đèn",
        "prompt": (
            "Blue hour at dusk with lights on: deep blue twilight sky, warm glowing "
            "interior and facade lights, illuminated windows, balanced ambient-to-artificial "
            "light, cinematic evening mood."
        ),
    },
}


def _join(parts: list[str]) -> str:
    return " ".join(p.strip() for p in parts if p and p.strip())


def build_interior_prompt(style_key: str, user_text: str = "") -> str:
    style = INTERIOR_STYLES.get(style_key, {}).get("prompt", "")
    user = f"User requirements (Vietnamese): {user_text.strip()}" if user_text.strip() else ""
    return _join([GEOMETRY_LOCK, style, user, QUALITY_SUFFIX])


def build_exterior_prompt(context_key: str, weather_key: str, user_text: str = "") -> str:
    context = EXTERIOR_CONTEXTS.get(context_key, {}).get("prompt", "")
    weather = EXTERIOR_WEATHER.get(weather_key, {}).get("prompt", "")
    user = f"User requirements (Vietnamese): {user_text.strip()}" if user_text.strip() else ""
    return _join([GEOMETRY_LOCK, context, weather, user, QUALITY_SUFFIX])


def build_inpaint_prompt(instruction: str) -> str:
    """Chỉ thị sửa cục bộ: chỉ đổi vùng được đánh dấu (mask), giữ nguyên phần còn lại."""
    return _join([
        "You are given a photorealistic render and a second image showing a mask: the "
        "bright magenta region marks the area to edit. Modify ONLY the masked region "
        "according to the instruction below. Keep absolutely everything outside the mask "
        "pixel-identical: same geometry, materials, colour, lighting and composition. "
        "Blend the edited region seamlessly with its surroundings.",
        f"Edit instruction (Vietnamese): {instruction.strip()}",
        "Photorealistic, seamless, consistent lighting, no text, no watermark.",
    ])


# Reference image: hướng dẫn Gemini "hút" tone màu & vật liệu từ ảnh tham chiếu.
REFERENCE_INSTRUCTION = (
    "An additional reference image is provided. Match its overall colour grading, "
    "material palette, mood and lighting style so this render stays visually consistent "
    "with it, while still respecting the geometry of the main SketchUp input."
)


def presets_payload() -> dict:
    """Dữ liệu preset cho frontend dựng dropdown (1 nguồn sự thật)."""
    def to_list(d: dict[str, dict[str, str]]):
        return [{"key": k, "label": v["label"]} for k, v in d.items()]

    return {
        "interior_styles": to_list(INTERIOR_STYLES),
        "exterior_contexts": to_list(EXTERIOR_CONTEXTS),
        "exterior_weather": to_list(EXTERIOR_WEATHER),
    }
