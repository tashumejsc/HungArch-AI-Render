"""Thư viện prompt cho HungArch AI Render.

Mỗi lựa chọn trên giao diện (phong cách / bối cảnh / thời tiết) được map sang
một đoạn mô tả tiếng Anh chi tiết. Đoạn mô tả người dùng tự nhập (tiếng Việt)
được nối vào sau — Gemini hiểu tốt cả hai ngôn ngữ.

Nguồn sự thật duy nhất: thêm preset mới vào đây, frontend tự cập nhật.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# KHÓA HÌNH HỌC — bắt Gemini giữ TUYỆT ĐỐI bố cục SketchUp
# ---------------------------------------------------------------------------
GEOMETRY_LOCK = (
    "Transform this SketchUp architectural model screenshot into a photorealistic render. "
    "ABSOLUTE RULE — preserve with zero tolerance: "
    "the exact camera viewpoint, field of view, perspective projection, and framing; "
    "every wall, floor, ceiling position and dimension; "
    "the precise location, size and shape of all windows, doors and openings; "
    "all built-in architectural elements (columns, beams, niches, steps, soffits); "
    "the exact position and footprint of every furniture piece and fixture. "
    "You may ONLY add: realistic surface materials and finishes, textures, "
    "lighting (artificial lamps and natural sunlight), shadows, reflections, "
    "decorative objects, plants, and fine surface detail that does NOT alter geometry. "
    "The room layout, camera angle, and composition must be absolutely identical to the input image."
)

# ---------------------------------------------------------------------------
# GEOMETRY_LOCK cho ảnh ĐÃ CÓ VẬT LIỆU + ÁNH SÁNG từ SketchUp
# (loại 2: ảnh đã áp map vật liệu, ánh sáng trong SU — chỉ nâng lên photorealistic)
# ---------------------------------------------------------------------------
GEOMETRY_LOCK_TEXTURED = (
    "This SketchUp model screenshot already has materials and lighting applied. "
    "TASK: Render it to photorealistic quality by ENHANCING what is already there — do NOT replace it. "
    "ABSOLUTE RULES — preserve with zero tolerance: "
    "the exact camera viewpoint, field of view, perspective projection, and framing; "
    "every wall, floor, ceiling position and dimension; "
    "the precise location, size and shape of all windows, doors and openings; "
    "all built-in architectural elements (columns, beams, niches, steps, soffits); "
    "the exact position and footprint of every furniture piece and fixture; "
    "the EXISTING material palette and colour scheme already applied in the SketchUp model — "
    "do NOT replace, recolour, or change the type of any existing material. "
    "You may ONLY improve: photorealistic texture resolution and micro-detail (wood grain, stone veining, "
    "fabric weave, glass clarity), physically-based surface response (reflectance, roughness, specularity), "
    "realistic lighting quality (shadows, caustics, global illumination, ambient occlusion), "
    "and atmospheric depth and realism. "
    "The room layout, camera angle, material palette, furniture placement, and overall composition "
    "must remain absolutely identical to the input image."
)

# ---------------------------------------------------------------------------
# PROMPT NÂNG CAO CHẤT LƯỢNG ẢNH RENDER (AI Enhance — gọi từ /api/enhance)
# ---------------------------------------------------------------------------
ENHANCE_PROMPT = (
    "This is a photorealistic architectural render. "
    "Enhance its visual quality to the highest possible level without changing any content: "
    "ultra-sharpen every surface texture (stone veining, wood grain, fabric weave, polished floor), "
    "improve global illumination with ray-traced shadows, soft ambient occlusion, and contact shadows, "
    "enhance material PBR response (metallic sheen, glass clarity, polished floor mirror reflections), "
    "refine colour grading to match professional V-Ray/Corona Renderer publication standard, "
    "add subtle depth-of-field where appropriate for architectural photography. "
    "PRESERVE ABSOLUTELY: all existing composition, camera angle, geometry, furniture, "
    "material types, colours, and spatial layout. "
    "Output the same image at significantly higher photorealistic quality and texture detail. "
    "No style change, no added elements, no text, no watermark."
)

# ---------------------------------------------------------------------------
# CHẤT LƯỢNG ĐẦU RA — nối vào cuối mọi render Gemini
# ---------------------------------------------------------------------------
QUALITY_SUFFIX = (
    "Photorealistic quality matching professional V-Ray and Corona Renderer studio output. "
    "Physically based rendering: ray-traced global illumination, area light sources, "
    "accurate PBR surface reflectance (metallic, glass, polished stone, fabric, oiled wood). "
    "Soft contact shadows, ambient occlusion, subtle lens flare on light sources. "
    "Professional medium-format architectural photography: "
    "shallow depth of field, perfect balanced exposure, high dynamic range, "
    "ultra-crisp micro-texture detail on every surface — stone veining, wood grain, fabric weave. "
    "Publication quality matching Dezeen, Architectural Digest, ArchDaily editorial standard. "
    "No sketch lines, no 3D-model look, no flat matte artifacting, "
    "no people unless explicitly stated, no text, no watermark, no borders."
)

# ---------------------------------------------------------------------------
# TAB 1: NỘI THẤT
# placeholder = gợi ý tự động trong textarea khi user chọn phong cách này
# ---------------------------------------------------------------------------
INTERIOR_STYLES: dict[str, dict[str, str]] = {
    "modern": {
        "label": "Hiện đại",
        "placeholder": (
            "VD: Tủ bếp cao sàn gỗ walnut tối, mặt đảo marble Calacatta trắng gân xám, "
            "đèn LED hắt 3000K dưới tủ trên và cove trần, sàn gạch xám lớn 1200×600mm, "
            "ghế bar inox chân cao, không có người"
        ),
        "prompt": (
            "Modern luxury kitchen-living interior: full-height dark walnut wood veneer cabinetry "
            "with integrated touch-to-open panels, warm brushed brass and matte black mixed hardware, "
            "recessed LED strip lighting 3000K warm gold under upper cabinets and inside cove ceiling surround, "
            "book-matched white Calacatta marble island with waterfall edge and dark grey veining, "
            "professional matte black built-in appliances (refrigerator, oven, range hood), "
            "oversized globe pendants in brushed brass above the island, "
            "large format 1200×600mm cool light grey polished porcelain floor tiles, "
            "open plan layout, curated dried sculptural branches in tall vase, "
            "low credenza in walnut with ceramic vases, "
            "cove-lit ceiling with hidden LED, rich warm sophisticated atmosphere."
        ),
    },
    "minimalist": {
        "label": "Tối giản",
        "placeholder": (
            "VD: Sofa linen be nhạt, không đồ decor trên mặt bàn, ánh sáng tự nhiên ban ngày mát, "
            "sàn microcement xám trắng phẳng mịn, không có người"
        ),
        "prompt": (
            "Minimalist luxury interior: absolute purity of form and material, "
            "pure white and warm greige palette throughout, "
            "seamless floor-to-ceiling integrated joinery with push-to-open hairline-gap panels, "
            "polished microcement walls and floor with no skirting boards, "
            "single recessed slot light running the full ceiling perimeter, "
            "one hero furniture piece per zone — oversized linen sofa, solid travertine coffee table, "
            "clear empty surfaces, no visible clutter or decoration, "
            "natural linen and undyed wool textiles only, "
            "air of meditative expensive quietness and restraint."
        ),
    },
    "japandi": {
        "label": "Japandi",
        "placeholder": (
            "VD: Đèn giấy washi pendant thấp phía trên bàn, gỗ ash sáng hạt gỗ mịn, "
            "lọ gốm thủ công nhỏ trên kệ, thảm jute tự nhiên, không có người"
        ),
        "prompt": (
            "Japandi luxury interior — Japanese wabi-sabi meets Scandinavian hygge: "
            "light ash and pale smoked oak wood with natural visible grain on all millwork, "
            "handmade washi paper lantern pendants hanging low over the dining table, "
            "low-profile platform furniture in sanded ash with linen cushion covers, "
            "undyed linen and chunky-knit wool textiles in warm sand and charcoal, "
            "muted earthy palette: warm sand, deep charcoal, dusty sage green, "
            "handcrafted ceramic vessels with drip glazes on open shelving, "
            "a single bonsai and dried pampas grass arrangement, "
            "narrow slatted wood sliding screens as room dividers, "
            "indirect warm 2700K ambient lighting from concealed niches, "
            "deep meditative calm, imperfectly perfect Japanese simplicity."
        ),
    },
    "neoclassic": {
        "label": "Tân cổ điển",
        "placeholder": (
            "VD: Phù điêu thạch cao trắng tường, đèn chùm pha lê lớn trung tâm, "
            "rèm velvet xanh navy dày, sofa bọc lụa kem ngà, không có người"
        ),
        "prompt": (
            "Neoclassical luxury interior — grand European opulence: "
            "deep sculpted white plaster wall panelling with raised moulding and shadow reveals, "
            "ornate coffered ceiling with gilded cornice and centre rose, "
            "monumental crystal chandelier with warm candlelight filament bulbs, "
            "book-matched Carrara marble floor with dark Nero Marquina border inlay and Greek-key pattern, "
            "gilded bronze and champagne satin-gold accents on all hardware and picture frames, "
            "deep-buttoned velvet upholstered sofas and armchairs in dusty rose, ivory and eau-de-nil, "
            "fluted pilasters framing doorways, "
            "heavy lined velvet drapes pooling on the floor, "
            "large oil-painting in ornate frame above fireplace, "
            "overwhelming sense of aristocratic grandeur and timeless luxury."
        ),
    },
    "zen": {
        "label": "Thiền / Á Đông",
        "placeholder": (
            "VD: Tường đá granite thô nhám xám tối, cửa shoji khung tre đen, "
            "đèn hắt thấp vào tường đá từ dưới lên, hòn non bộ nhỏ góc phòng, không có người"
        ),
        "prompt": (
            "Zen luxury Asian interior — serene sanctuary for the spirit: "
            "monumental raw split-face granite stone feature wall with invisible uplighting washing it from below, "
            "dark ebony-stained bamboo and oiled natural teak millwork, "
            "rice-paper shoji sliding screens in lacquered black bamboo frame, "
            "indoor koi pond or floor-to-ceiling water wall feature with stainless steel tray, "
            "curated indoor bonsai forest arrangement and flat raked gravel garden section, "
            "ultra-low floor-level seating cushions in charcoal and terracotta linen, "
            "pinpoint spotlights in dark recesses only, concealed in niches, "
            "incense smoke-diffuser and ceramic ritual objects, "
            "profound spiritual tranquility and five-element harmony."
        ),
    },
    "tropical": {
        "label": "Nhiệt đới",
        "placeholder": (
            "VD: Cây monstera khổng lồ góc phòng, quạt trần gỗ tự nhiên, "
            "ghế mây trắng đệm vải lanh, sàn terrazzo san hô nhạt, không có người"
        ),
        "prompt": (
            "Tropical luxury resort interior — lush indoor paradise: "
            "enormous specimen indoor plants: oversized monstera deliciosa, bird of paradise, "
            "giant banana palm, pothos cascading from high shelves, "
            "natural rattan and hand-woven wicker furniture with thick white linen cushions, "
            "open breezeway connecting inside to outside through full-width bifold glass, "
            "warm tropical sunlight filtering through bamboo woven pendant shades, "
            "terrazzo floor in soft coral and dusty pink with white matrix, "
            "natural teak sideboard and dining table with raw edge, "
            "large white slow-turning ceiling fans in natural wood blade finish, "
            "fresh resort lifestyle, vibrant organic tropical paradise atmosphere."
        ),
    },
    "commercial_office": {
        "label": "Văn phòng thương mại",
        "placeholder": (
            "VD: Sàn vinyl planks màu gỗ sáng, tường kính meeting room film frost, "
            "LED panel 4000K + đèn cove âm trần, cây fiddle-leaf fig góc sảnh, "
            "quầy reception marble trắng + inox mờ, không có người"
        ),
        "prompt": (
            "Premium modern commercial office interior — Grade-A workplace: "
            "height-adjustable sit-stand desks in white oak laminate finish, "
            "high-back ergonomic mesh task chairs in deep charcoal, "
            "suspended rectangular acoustic felt ceiling baffles in warm medium grey, "
            "recessed LED panel lighting 4000K neutral white with indirect warm cove supplement, "
            "glass-partitioned meeting rooms with frosted film cut-pattern manifestation, "
            "monolithic reception counter in white Calacatta marble top and brushed 316L stainless steel base, "
            "large-format 600×1200mm polished light grey porcelain tile floor with dark charcoal grout, "
            "floor-to-ceiling glazing on perimeter flooding space with daylight, "
            "curated statement indoor plants in oversized concrete planters, "
            "subtle branded signage, professional high-energy contemporary corporate atmosphere."
        ),
    },
    "hotel_lobby": {
        "label": "Lobby khách sạn",
        "placeholder": (
            "VD: Marble book-matched tường sau quầy lễ tân, đèn cầu thủy tinh nghệ thuật "
            "thả từ trần cao, ghế lounge velvet xanh lá đậm, hoa tươi cắm cao 1.5m, không có người"
        ),
        "prompt": (
            "Luxury 5-star hotel lobby and reception — architectural statement arrival: "
            "grand triple-height atrium with exposed concrete and warm stone cladding, "
            "monumental hand-blown glass bubble chandelier installation cascading from ceiling, "
            "full-height book-matched Calacatta Gold marble feature wall behind the reception counter, "
            "reception counter in dark smoked oak base with brass inlay top, "
            "plush deep-seated lounge chairs and sofas in forest green velvet and cognac leather, "
            "oversize fresh floral arrangement (white orchids, tropical leaves) as centrepiece, "
            "herringbone inlay polished marble floor with central geometric medallion border, "
            "precise pinspot accent lighting on marble and art, "
            "tall potted indoor olive trees flanking the entrance, "
            "overwhelming sense of sophisticated luxury hospitality."
        ),
    },
    "fb_restaurant": {
        "label": "Nhà hàng / Cafe F&B",
        "placeholder": (
            "VD: Đèn Edison warmwhite mỗi bàn, booth gỗ mahogany tối, quầy bar marble đen, "
            "tường gạch phơi đỏ nâu, nến votives kính nhỏ mỗi bàn, không có người"
        ),
        "prompt": (
            "Upscale restaurant and cocktail bar interior — intimate fine dining atmosphere: "
            "Edison filament pendant lights hanging at varying heights above each table casting warm 2400K pools, "
            "rich deep mahogany wood booth seating with nailhead trim and caramel leather banquette, "
            "monolithic bar counter in Nero Marquina black marble with dramatic backlit bottle wall, "
            "aged exposed brick or raw hand-trowelled plaster feature wall in amber and sienna tones, "
            "custom encaustic patterned floor tiles in terracotta and off-white, "
            "antique brass bar stools with green leather seats, "
            "curated gallery wall of framed botanical prints in brass frames, "
            "small glass votives with flickering candlelight on each table, "
            "warm cinematic 2700K atmosphere, intimate welcoming fine-dining mood."
        ),
    },
    "resort_villa": {
        "label": "Resort / Pool Villa",
        "placeholder": (
            "VD: Cửa kính lùa mở hoàn toàn ra hồ bơi vô biên, sàn đá travertine liền mạch trong-ngoài, "
            "teak daybed trắng nệm dày, quạt trần cánh gỗ lớn, không có người"
        ),
        "prompt": (
            "Luxury resort pool villa interior — ultimate indoor-outdoor tropical living: "
            "fully retractable multi-panel glass wall system opening completely to a private infinity pool, "
            "honed travertine stone floor flowing seamlessly inside-out without threshold, "
            "oversized low-slung teak daybed with thick white mattress and linen bolster cushions, "
            "rattan and teak lounge chairs with white UV-resistant outdoor cushions, "
            "large slow-turning teak ceiling fan with broad carved wood blades, "
            "outdoor rain shower visible through louvred teak privacy screen, "
            "lush mature tropical garden of palms, heliconias and frangipani framing the pool, "
            "turquoise ocean or forest hill backdrop beyond, "
            "pure relaxed luxury resort lifestyle, serene paradise retreat."
        ),
    },
    "apartment_compact": {
        "label": "Căn hộ compact",
        "placeholder": (
            "VD: Tủ âm tường cao 2.8m màu trắng bóng, bàn bếp kiêm bàn ăn kéo dài được, "
            "sàn vinyl gỗ birch nhạt, đèn track đen matte linh hoạt, không có người"
        ),
        "prompt": (
            "Modern compact urban apartment interior — intelligent space maximisation: "
            "floor-to-ceiling integrated white gloss lacquer storage wall concealing all clutter, "
            "multifunctional island counter that extends to seat four for dining, "
            "modular sofa with hidden storage underneath in light sand bouclé, "
            "Murphy wall bed concealed behind mirror-fronted panel, "
            "warm birch veneer kitchen cabinetry keeping the space light and airy, "
            "flexible track lighting rail in matte black with adjustable spot heads, "
            "large floor-to-ceiling sliding glass door to balcony maximising light, "
            "full-height mirror on one wall doubling perceived space, "
            "smart urban lifestyle — efficient, uncluttered, yet stylish and comfortable."
        ),
    },
}

# ---------------------------------------------------------------------------
# TAB 2: NGOẠI THẤT
# ---------------------------------------------------------------------------
EXTERIOR_CONTEXTS: dict[str, dict[str, str]] = {
    "hanoi_old_quarter": {
        "label": "Phố cổ / Ngõ hẻm Hà Nội",
        "placeholder": (
            "VD: Tường rêu phong cổ vàng ochre, mái ngói âm dương xám xanh, "
            "dây bougainvillea đỏ leo tường, xe máy đỗ dưới, đường nhỏ hẹp"
        ),
        "prompt": (
            "Set in a narrow Hanoi Old Quarter (Phố Cổ) alley: dense weathered French-colonial tube houses "
            "with mossy aged terracotta tile roofs, tangled overhead power lines strung between buildings, "
            "peeling stucco walls in faded ochre, cream and dusty rose, "
            "potted bougainvillea in crimson and magenta cascading from iron balconies, "
            "parked motorbikes and bicycles below, damp worn stone paving, "
            "street vendor with bamboo baskets and conical hat, "
            "authentic chaotic lived-in Vietnamese street texture, warm atmospheric aged patina."
        ),
    },
    "urban_shophouse": {
        "label": "Shophouse hiện đại đô thị",
        "placeholder": (
            "VD: Mặt kính curtain wall phản chiếu, louvres nhôm nâu, "
            "vỉa hè granite xám bóng, cây xanh đô thị hàng, tòa nhà cao tầng phía sau"
        ),
        "prompt": (
            "Modern Vietnamese urban shophouse: sleek contemporary commercial frontage "
            "with glass curtain wall and anodised aluminium solar louvres, "
            "clean grey honed granite sidewalk with city street trees, "
            "adjacent modern commercial neighbours, polished high-rise tower backdrop, "
            "tidy prosperous Hanoi or Ho Chi Minh City central business district context, "
            "subtle landscape planters at ground level, evening street activity."
        ),
    },
    "tube_house_facade": {
        "label": "Mặt tiền nhà ống tiêu chuẩn",
        "placeholder": (
            "VD: Sơn tường trắng sáng sạch, lan can kính trong suốt, "
            "nhà ống lân cận 2 bên, đèn ngoài trời mặt tiền, đường nhựa phía trước"
        ),
        "prompt": (
            "Vietnamese tube-house (nhà ống) facade on a typical residential street: "
            "tall narrow contemporary 4–5m wide plot, clean white or light grey render-painted frontage, "
            "decorative powder-coated aluminium privacy screen on balconies, "
            "glass balustrades on upper levels, gate and car parking at ground level, "
            "attached neighbouring tube houses either side continuing the streetscape, "
            "a few motorcycles parked below, mature street tree casting dappled shadow, "
            "typical Hanoi or HCM City mid-range residential street, afternoon light."
        ),
    },
    "northern_village": {
        "label": "Làng quê Bắc Bộ",
        "placeholder": (
            "VD: Cây đa cổ thụ rễ phụ lớn, ao làng có sen, lúa xanh xa, "
            "hàng rào tre vàng, đường làng đất đỏ"
        ),
        "prompt": (
            "Northern Vietnamese countryside (đồng bằng Bắc Bộ): tranquil rural village setting, "
            "massive ancient banyan tree with cascading aerial roots as centrepiece, "
            "still lotus pond with pink and white flowers reflecting sky and building, "
            "vivid green paddy fields stretching to distant tree lines, "
            "woven bamboo hedgerows and rustic terracotta brick walls, "
            "traditional terracotta tile roofs in warm earthy red, "
            "peaceful pastoral Vietnamese countryside, soft overcast diffuse light."
        ),
    },
    "misty_hills": {
        "label": "Cảnh quan đồi núi sương mù",
        "placeholder": (
            "VD: Sương mù buổi sáng cuộn qua rừng thông, ruộng bậc thang xanh mướt, "
            "mây thấp che chân núi, không khí trong vắt"
        ),
        "prompt": (
            "Misty highland landscape of northern Vietnam (Sa Pa, Đà Lạt, Mộc Châu): "
            "rolling verdant hills covered in pine forest and tea plantations, "
            "dramatic layered terraced rice fields cascading down the slopes in vibrant green and gold, "
            "drifting morning mist and low cloud banks weaving between pine trees, "
            "fresh cool highland air, cobalt-blue mountain ridges receding to horizon, "
            "ethereal serene highland atmosphere, magical misty paradise."
        ),
    },
    "commercial_tower": {
        "label": "Tòa nhà văn phòng / thương mại",
        "placeholder": (
            "VD: Kính curtain wall phản chiếu bầu trời, retail podium tầng 1 cao cấp, "
            "plaza công cộng có cây xanh và bồn nước, đường phố đô thị phía trước"
        ),
        "prompt": (
            "Modern commercial office tower exterior — Grade-A urban landmark: "
            "high-rise glass curtain wall facade with structural aluminium grid, "
            "high-performance low-E reflective glazing mirroring clouds and sky, "
            "premium retail podium at street level with deep canopy overhang, "
            "landscaped public plaza with mature specimen trees, stone paving and water feature at base, "
            "adjacent commercial high-rises continuing the city skyline, "
            "precise exterior LED lighting on architectural reveals, "
            "clean authoritative Grade-A commercial presence."
        ),
    },
    "resort_beach": {
        "label": "Resort biển / bungalow",
        "placeholder": (
            "VD: Bãi cát trắng mịn sát mép nước, biển xanh ngọc bích rõ đáy, "
            "dừa xanh nghiêng ra biển, bungalow trên cọc gỗ teak"
        ),
        "prompt": (
            "Luxury beachfront tropical resort architecture — Southeast Asian paradise: "
            "elevated tropical bungalow or overwater villa on dark teak stilts above pristine white sand beach, "
            "traditional hand-tied alang-alang thatched roof or dark copper standing-seam metal, "
            "reclaimed teak and natural bamboo structure, "
            "private plunge pool or deck with infinity edge towards crystal-clear turquoise sea, "
            "lush coconut palms leaning over the water, bougainvillea and frangipani in bloom, "
            "turquoise-to-deep-blue ocean gradient backdrop, "
            "afternoon golden light raking across the water, ultimate tropical beach paradise."
        ),
    },
    "garden_eco": {
        "label": "Biệt thự vườn sang trọng",
        "placeholder": (
            "VD: Lối đi đá đen ướt phản chiếu ánh đèn, cọ vương miện cao, "
            "hàng rào kính trong suốt, đèn LED viền mái vàng ấm, sân thượng có pergola"
        ),
        "prompt": (
            "Luxury modern tropical garden villa exterior — dramatic landscaped arrival: "
            "dark black absolute granite stone paving with perfectly wet mirror-reflective surface, "
            "layered tropical landscaping: tall royal palms, sculptural Japanese maple, "
            "tree ferns, dwarf mondo grass lawn panels, ornamental grasses in foreground, "
            "architectural LED strip lighting on eaves and step edges glowing warm amber gold, "
            "glass balustrades on all terraces and roof deck, "
            "roof terrace pergola in weathered teak with climbing Thunbergia, "
            "modern white concrete and dark Corten steel building volumes, "
            "dramatic atmosphere of lush opulence and privacy."
        ),
    },
}

# ---------------------------------------------------------------------------
# NGOẠI THẤT — thời tiết & ánh sáng
# ---------------------------------------------------------------------------
EXTERIOR_WEATHER: dict[str, dict[str, str]] = {
    "harsh_sun": {
        "label": "Nắng gắt nhiệt đới",
        "prompt": (
            "Blazing tropical midday sun: intense direct sunlight casting deep crisp hard-edged shadows, "
            "brilliant deep cobalt blue sky with white cumulus clouds, "
            "high contrast with blown-out white highlights on light surfaces, "
            "vivid saturated tropical green foliage, sparkling water reflections, "
            "shimmering heat haze over paved surfaces."
        ),
    },
    "overcast_after_rain": {
        "label": "Bầu trời u ám sau mưa",
        "prompt": (
            "Moody overcast sky immediately after tropical downpour: "
            "soft diffuse shadowless pearl-grey light from an overcast sky, "
            "dark wet black granite stone paving perfectly mirror-reflecting the building facade "
            "and all warm golden LED lighting in razor-sharp reflections, "
            "standing puddles with still mirror surface, "
            "architectural LED strip lighting on eaves and step risers glowing warm amber, "
            "warm interior light spilling through large windows onto the wet paving, "
            "glistening water droplets on every tropical leaf, "
            "fallen yellow leaves on wet stone, dramatic moody cinematic atmosphere."
        ),
    },
    "blue_hour": {
        "label": "Giờ xanh (Blue Hour) lên đèn",
        "prompt": (
            "Magic blue hour twilight with full architectural lighting: "
            "deep royal blue gradient sky transitioning from rich cobalt at zenith to dark indigo at horizon, "
            "every interior window glowing warm gold against the cool blue sky, "
            "architectural LED strip accents on eaves, steps and water features all illuminated, "
            "landscape uplights illuminating palm fronds and feature trees from below in warm white, "
            "underwater pool lighting glowing blue-aqua if present, "
            "perfect balanced ambient-to-artificial light exposure ratio, "
            "cinematic luxury evening architecture shot."
        ),
    },
}

# ---------------------------------------------------------------------------
# THỜI ĐIỂM ÁNH SÁNG
# ---------------------------------------------------------------------------
LIGHTING_PRESETS: dict[str, dict[str, str]] = {
    "morning": {
        "label": "Sáng sớm (7–9h)",
        "interior": (
            "soft cool morning light streaming through east-facing windows, "
            "blue-white 5500K daylight, long gentle diagonal shadows across floor, "
            "fresh peaceful morning mood, dew light quality."
        ),
        "exterior": (
            "soft golden morning light from low eastern sun, "
            "long gentle diagonal shadows, fresh dewy atmosphere, light mist on vegetation, "
            "peaceful serene morning mood."
        ),
    },
    "midday": {
        "label": "Ban ngày (11–14h)",
        "interior": (
            "bright neutral daylight from overhead skylights and large windows, "
            "balanced even illumination 5000K, clear crisp visibility with soft diffuse shadows, "
            "professional bright daytime look."
        ),
        "exterior": (
            "bright neutral overhead sunlight, short shadows directly below elements, "
            "clear deep blue sky with white clouds, vivid saturated colours, strong contrast."
        ),
    },
    "golden_hour": {
        "label": "Chiều tà / Golden Hour (16–18h)",
        "interior": (
            "warm low-angle golden hour sunlight raking across all surfaces from one side, "
            "warm amber 2700K tones, long dramatic raking shadows across walls and floor, "
            "luxurious warm golden glow on every surface."
        ),
        "exterior": (
            "warm low-angle late afternoon golden sunlight at 15-degree elevation, "
            "long dramatic amber-orange shadows stretching across paving, "
            "golden light on facade and foliage, cinematic warm atmosphere."
        ),
    },
    "blue_hour": {
        "label": "Blue Hour / Hoàng hôn (18–19h)",
        "interior": (
            "warm 3000K artificial interior lighting dominant over cool blue ambient from windows, "
            "balanced artificial vs twilight ratio, sophisticated intimate evening mood."
        ),
        "exterior": (
            "blue hour twilight, deep royal blue gradient sky, "
            "warm golden architectural lighting on facade and garden, "
            "glowing windows, cinematic luxury evening atmosphere."
        ),
    },
    "night": {
        "label": "Ban đêm",
        "interior": (
            "full dramatic artificial lighting scheme: directional halogen spotlights on key features, "
            "warm LED accent strips in niches and coves, deep atmospheric shadows in corners, "
            "luxurious sophisticated full night atmosphere."
        ),
        "exterior": (
            "full dark night sky, dramatic architectural floodlighting washing the facade, "
            "landscape uplights illuminating trees from below in warm white, "
            "glowing warm interior light through all windows, "
            "LED strip accents on eaves and steps, dark indigo sky."
        ),
    },
}

# ---------------------------------------------------------------------------
# ĐỘ DÀY CÂY XANH NGOẠI THẤT
# ---------------------------------------------------------------------------
VEGETATION_DENSITY: dict[str, dict[str, str]] = {
    "sparse": {
        "label": "Tối thiểu",
        "prompt": (
            "Minimal curated architectural landscaping: "
            "a few precisely placed sculptural specimen plants in concrete planters, "
            "clean architectural focus, architecture as the dominant composition element."
        ),
    },
    "moderate": {
        "label": "Vừa phải",
        "prompt": (
            "Moderate well-maintained tropical landscaping: "
            "balanced greenery framing the architecture without overwhelming it, "
            "neatly trimmed hedge lines, a few specimen trees at key corners."
        ),
    },
    "lush": {
        "label": "Rậm rạp",
        "prompt": (
            "Abundant lush layered tropical vegetation: "
            "dense rich greenery cascading from terraces and planters, "
            "tall mature palms and ferns framing every elevation, "
            "overgrown paradise garden enveloping the architecture."
        ),
    },
}

# ---------------------------------------------------------------------------
# MOOD PRESETS — dùng cho tính năng "Gợi ý màu bằng AI" (analyze_mood)
# Khác với LIGHTING_PRESETS (thời điểm ánh sáng khi render):
# MOOD_PRESETS là tông màu cảm xúc để hậu kỳ colour-grading ảnh đã render.
# ---------------------------------------------------------------------------
MOOD_PRESETS: dict[str, dict[str, str]] = {
    "warm_luxe": {
        "label": "Ấm áp sang trọng",
        "prompt": (
            "Rich warm luxury: amber-gold tones, deep warm shadows, intimate and opulent feel, "
            "high contrast with glowing highlights, reminiscent of high-end interior photography."
        ),
    },
    "cool_minimal": {
        "label": "Lạnh tối giản",
        "prompt": (
            "Cool desaturated minimalism: clean white and cool grey tones, low contrast, "
            "flat soft lighting, contemporary editorial architecture photography style."
        ),
    },
    "natural_daylight": {
        "label": "Tự nhiên ban ngày",
        "prompt": (
            "Neutral balanced daylight: true-to-life colours, bright and airy, "
            "clean whites, balanced exposure, natural and fresh daytime feel."
        ),
    },
    "cinematic_moody": {
        "label": "Điện ảnh u trầm",
        "prompt": (
            "Cinematic dark moodiness: elevated contrast, deep dramatic shadows, "
            "slightly desaturated film look, sophisticated and brooding atmosphere."
        ),
    },
    "warm_residential": {
        "label": "Ấm cúng gia đình",
        "prompt": (
            "Warm cosy residential: soft warm creams and honey tones, comfortable and inviting, "
            "gentle brightness, lived-in homely warmth."
        ),
    },
}


def _join(parts: list[str]) -> str:
    return " ".join(p.strip() for p in parts if p and p.strip())


# ---------------------------------------------------------------------------
# GEMINI PROMPT BUILDERS
# Gemini = instruction-following model → cần GEOMETRY_LOCK + mô tả chi tiết
# ---------------------------------------------------------------------------
def build_interior_prompt(
    style_key: str,
    user_text: str = "",
    lighting_key: str = "golden_hour",
    input_type: str = "wireframe",
) -> str:
    """Xây prompt nội thất.

    input_type='wireframe'  → ảnh đen trắng chưa có vật liệu: AI thêm hoàn toàn theo preset.
    input_type='textured'   → ảnh đã áp vật liệu trong SU: AI giữ vật liệu, chỉ nâng photorealistic.
    """
    if input_type == "textured":
        lock = GEOMETRY_LOCK_TEXTURED
        style_prompt = INTERIOR_STYLES.get(style_key, {}).get("prompt", "")
        style = (
            f"Aesthetic enhancement direction (do not replace existing materials, only refine "
            f"towards this quality level): {style_prompt}"
            if style_prompt else ""
        )
    else:
        lock = GEOMETRY_LOCK
        style = INTERIOR_STYLES.get(style_key, {}).get("prompt", "")

    light = LIGHTING_PRESETS.get(lighting_key, {}).get("interior", "")
    user = f"Additional user requirements: {user_text.strip()}" if user_text.strip() else ""
    return _join([lock, style, light, user, QUALITY_SUFFIX])


def build_exterior_prompt(
    context_key: str,
    weather_key: str,
    user_text: str = "",
    lighting_key: str = "golden_hour",
    vegetation_key: str = "moderate",
    input_type: str = "wireframe",
) -> str:
    """Xây prompt ngoại thất.

    input_type='wireframe'  → ảnh đen trắng: AI thêm vật liệu + bối cảnh hoàn toàn theo preset.
    input_type='textured'   → ảnh đã có vật liệu: AI giữ vật liệu, chỉ nâng photorealistic.
    """
    if input_type == "textured":
        lock = GEOMETRY_LOCK_TEXTURED
        ctx_prompt = EXTERIOR_CONTEXTS.get(context_key, {}).get("prompt", "")
        context = (
            f"Contextual enhancement (enhance existing environment towards this setting without replacing "
            f"existing materials on the building): {ctx_prompt}"
            if ctx_prompt else ""
        )
    else:
        lock = GEOMETRY_LOCK
        context = EXTERIOR_CONTEXTS.get(context_key, {}).get("prompt", "")

    weather = EXTERIOR_WEATHER.get(weather_key, {}).get("prompt", "")
    light = LIGHTING_PRESETS.get(lighting_key, {}).get("exterior", "")
    veg = VEGETATION_DENSITY.get(vegetation_key, {}).get("prompt", "")
    user = f"Additional user requirements: {user_text.strip()}" if user_text.strip() else ""
    return _join([lock, context, weather, light, veg, user, QUALITY_SUFFIX])


# ---------------------------------------------------------------------------
# TAB 3: BẢN VẼ 2D
# Sub-mode 'drawing_mode':
#   '3d_perspective'  → AI tạo phối cảnh 3D từ mặt bằng / phác thảo 2D
#   '2d_render'       → AI làm đẹp bản vẽ 2D gốc, GIỮ NGUYÊN góc nhìn top-down/elevation
#                        (mặt bằng/mặt đứng phối màu kiểu xuất LayOut SketchUp)
# 'drawing_type': 'autocad' | 'sketch'
# 'drawing_output' khi drawing_mode='2d_render': 'floor_plan' | 'site_plan'
#   (vẫn nhận 'interior'/'exterior' cũ làm alias để tương thích ngược với main.py)
# ---------------------------------------------------------------------------

# --- Gợi ý theo CHẤT LƯỢNG ẢNH ĐẦU VÀO (autocad/sketch) -----------------------
# Tách riêng: file CAD vector xuất sạch khác hẳn ảnh chụp màn hình / scan giấy.
_AUTOCAD_HINT_CLEAN = (
    "The input is a clean, crisp AutoCAD/vector technical drawing exported directly from CAD software: "
    "lines are precise and high-contrast. Treat all lines as architecturally accurate, "
    "dimension lines and annotation text are for reference only (do not render them literally), "
    "standard architectural symbols apply (arc = door swing, double-line notch = window, "
    "hatched regions = walls/columns, rectangles = furniture)."
)

# 2D mode only: KEEP all existing linework including dimension lines — do NOT say "for reference only"
# which causes Gemini to discard the geometry and regenerate a new plan from scratch.
_AUTOCAD_HINT_CLEAN_2D = (
    "The input is a clean AutoCAD vector drawing exported from CAD software. "
    "FOR THIS COLORIZATION TASK: ALL existing linework must be preserved and remain fully visible "
    "in the output — this includes wall lines (thick), furniture outlines (thin), "
    "dimension lines with tick marks and numbers, grid bubble circles with letters/numbers, "
    "section cut marks, hatch patterns inside walls/columns, door swing arcs, window openings, "
    "stair tread lines, area labels, and all annotation text. "
    "Do NOT remove, redraw, simplify, or reposition ANY of these lines. "
    "Apply flat color fills BETWEEN existing boundary lines — "
    "the existing linework stays fully visible ON TOP of color fills."
)

_AUTOCAD_HINT_SCAN = (
    "The input is a low-quality photo or scan of an AutoCAD/technical drawing — "
    "expect screen glare, slight skew/perspective distortion, blur, uneven lighting, "
    "compression artefacts, paper texture, or visible watermark/logo overlays. "
    "FIRST mentally rectify and deskew the drawing to a true orthographic top-down view "
    "before interpreting it. Ignore glare spots, scanner noise, paper creases, and any "
    "non-drawing artefacts (phone UI, watermark, ruler edge) — these are NOT architectural elements. "
    "Reconstruct faint or partially-obscured lines using architectural logic (walls form closed "
    "rooms, doors align with wall openings, symmetry where evident) rather than copying noise. "
    "Once rectified, treat lines as architecturally accurate: "
    "dimension lines and annotation text are for reference only (do not render them literally), "
    "standard architectural symbols apply (arc = door swing, double-line notch = window, "
    "hatched regions = walls/columns, rectangles = furniture)."
)

_SKETCH_HINT = (
    "The input is a freehand concept sketch or hand-drawn design: "
    "interpret rough lines as architectural intent — "
    "straighten implied straight edges, regularize proportions, "
    "respect the designer's spatial arrangement while improving geometric precision."
)

DRAWING_TO_3D = (
    "This is a 2D architectural floor plan or layout drawing. "
    "TASK: Generate a photorealistic 3D INTERIOR perspective render based on this 2D floor plan. "
    "READ the floor plan carefully: "
    "solid thick lines = walls; arc symbols = doors and their swing direction; "
    "double-line gaps in walls = windows (preserve their exact wall positions); "
    "rectangles and symbols = furniture/fixtures (preserve relative positions and scale). "
    "Generate a natural 3D interior perspective photographed from INSIDE the main living space, "
    "camera at standing eye level (1.5m high), wide-angle architectural photography, "
    "looking into the room with good depth and spatial feel. "
    "PRESERVE: all room proportions, relative space sizes, and furniture arrangement as indicated. "
    "GENERATE: full photorealistic 3D interior geometry, realistic materials, architectural lighting, "
    "shadows, and high-quality interior atmosphere."
)

DRAWING_ELEVATION_TO_3D = (
    "This is a 2D architectural elevation drawing (mặt đứng) showing the EXTERIOR facade of a building. "
    "TASK: Generate a photorealistic 3D EXTERIOR perspective render based on this elevation. "
    "READ the elevation carefully: "
    "the drawing shows the building exterior — walls, openings (windows/doors), balconies, roof line, "
    "facade articulation, setbacks, and floor levels as indicated by horizontal lines. "
    "Generate a natural 3D exterior perspective as if photographed from OUTSIDE at street level, "
    "camera at eye level (1.6m above ground), slightly angled off-centre (3/4 view) for architectural drama. "
    "PRESERVE: all facade proportions, floor heights, window/door positions, balcony geometry, and roof profile. "
    "GENERATE: full photorealistic 3D building exterior with realistic facade materials, "
    "sky backdrop, ground pavement, architectural lighting and shadows. "
    "DO NOT generate an interior — this is an exterior view of the building facade."
)

# ---------------------------------------------------------------------------
# KHÓA HÌNH HỌC CHO BẢN VẼ 2D — đặt ĐẦU TIÊN trong prompt để Gemini ưu tiên tuyệt đối
# Gemini tuân thủ instruction đầu tiên cao nhất → geometry lock PHẢI là câu đầu tiên.
# ---------------------------------------------------------------------------
_2D_GEOMETRY_LOCK = (
    "TASK TYPE: IMAGE COLORIZATION — THIS IS AN IMAGE EDITING TASK, NOT AN IMAGE GENERATION TASK. "
    "You are NOT creating a new floor plan. You are COLORIZING an existing architectural drawing. "
    "CRITICAL CONSTRAINT — TREAT THE INPUT AS AN IMMOVABLE LOCKED TEMPLATE: "
    "Every single pixel of linework in the input — wall lines, room boundaries, door arcs, "
    "window gaps, column outlines, stair symbols, furniture shapes, dimension lines, "
    "grid bubble circles, annotation text — must appear in the output at the EXACT SAME PIXEL POSITION. "
    "Nothing moves. Nothing is redrawn. Nothing is removed. Nothing is added or rearranged. "
    "The ONLY permitted change: paint flat color fills INSIDE existing closed boundaries. "
    "Think of it as a digital colouring-book: the line art is fixed, your only job is to colour inside the lines. "
    "SCALE AND PROPORTION ARE LOCKED: if a room is 30% of the plan width in the input, "
    "it must be exactly 30% of the plan width in the output. "
    "If there are two or more separate plan sections with gaps between them, those gaps must remain exactly as in the input. "
    "If the plan is in landscape orientation, the output must also be landscape. "
    "Any output where the geometry, proportions, or layout differs from the input — even slightly — is a complete failure."
)

# ---------------------------------------------------------------------------
# BÓNG ĐỔ KIỂU SKETCHUP LAYOUT (Parallel Projection) — KHÔNG phải bóng ảnh chụp
# Tham chiếu quy trình chuẩn: Camera > Parallel Projection (giáo trình SketchUp 2025)
# và Sun Light / Vertical-Horizontal Angle (giáo trình V-Ray 7).
# ---------------------------------------------------------------------------
_HARD_SHADOW_PLAN = (
    "SHADOW STYLE — this is critical, follow exactly like a SketchUp LayOut export, "
    "NOT a soft photographic render: "
    "render shadows as if cast by a single distant directional sun light under an orthographic "
    "PARALLEL PROJECTION camera (no perspective convergence, no camera depth-of-field blur). "
    "Shadows must be HARD-EDGED silhouette shapes with crisp, clean, non-blurred outlines — "
    "a flat, uniformly-toned grey/dark shadow shape (NOT a soft gradient falloff, NOT ambient "
    "occlusion fuzziness), projected consistently in ONE single direction from every wall, "
    "column, furniture piece, and tree symbol, as if the sun were fixed at one azimuth and "
    "altitude across the entire plan. Shadow length should be modest and proportionate "
    "(roughly 0.3–0.6× the casting object's plan footprint), pointing the same way for every "
    "object — never radiating, never randomized, never softly diffused. "
    "This hard, consistent, single-direction cast shadow is what gives the plan its crisp "
    "architectural presentation look, exactly like a SketchUp/LayOut walls-and-roof shadow study."
)

# ---------------------------------------------------------------------------
# PHÙ ĐIÊU 3D TOP-DOWN — nổi khối mà KHÔNG nghiêng trục, KHÔNG phối cảnh.
# Camera vẫn 90° thẳng đứng (footprint không lệch → overlay_linework vẫn khớp).
# Cảm giác 3D đến TỪ shading/AO/chất liệu, KHÔNG từ phép chiếu hình học.
# ---------------------------------------------------------------------------
_RELIEF_3D_PLAN = (
    "RELIEF / VOLUMETRIC DEPTH — make the plan read as a richly three-dimensional "
    "'rendered floor plan' that visually pops, WITHOUT changing the camera: "
    "the camera stays STRICTLY 90° orthographic straight-down top view — "
    "NO perspective convergence, NO axonometric/isometric tilt, NO visible vertical side faces. "
    "The sense of depth must come ONLY from shading and lighting cues, never from geometric projection: "
    "(1) add soft AMBIENT OCCLUSION — a subtle dark contact-shading gradient where walls meet the floor, "
    "inside corners, and around the base of every furniture piece, so objects feel seated and raised; "
    "(2) render furniture, beds, sofas, rugs and fixtures with realistic TOP-SURFACE material shading — "
    "cushions look plump, tabletops have a soft sheen, bedding has gentle folds and self-shadow — "
    "so each object reads as a solid object with real thickness seen from directly above; "
    "(3) give walls a subtle raised-edge highlight and a thin self-shadow along one side so the poché "
    "reads as a wall standing up off the floor plane; "
    "(4) add gentle material highlights and faint reflections on glossy floors / water / glass. "
    "CRITICAL: every object's outline must stay exactly on its plan footprint — depth is faked with "
    "tone and shadow only, the footprint geometry never moves or enlarges."
)

DRAWING_TO_2D_FLOOR_PLAN = (
    "COLORIZATION TARGET: A 2D architectural floor plan (mặt bằng) in strict orthographic "
    "top-down view — do NOT tilt, do NOT add perspective, do NOT convert to isometric or 3D. "
    "GOAL: Apply professional flat color fills to each room/space in this floor plan to produce "
    "a presentation-quality colored floor plan ('mặt bằng phối màu'). "
    "COLOR GUIDE — apply these flat, even tint fills INSIDE existing room boundaries: "
    "office/working/living areas → warm honey-tan (wood floor tone); "
    "meeting rooms → slightly cooler warm beige; "
    "wet areas (WC, bathroom, pantry, kitchen) → pale blue-grey tile tone; "
    "reception/lobby/corridor/circulation → light neutral warm grey; "
    "storage/service/utility rooms → cool light grey; "
    "outdoor terraces/balconies → light terracotta or stone grey paving tone. "
    "Wall/poché areas: add a dark grey fill inside thick wall regions if clearly identifiable — "
    "do NOT redraw or move any wall line. "
    "Furniture symbols: leave their shape and position exactly as in the input; "
    "optionally add a very subtle flat fill tint to distinguish them from the floor. "
    "KEEP visible in the output: all dimension lines, grid bubble circles, section cut marks, "
    "hatch patterns, and annotation text exactly as they appear in the input. "
    "OUTPUT: The exact same drawing as the input, with flat color fills added inside rooms. "
    "Same layout. Same proportions. Same orientation. Geometry 100% identical to input."
)

DRAWING_TO_2D_SITE_PLAN = (
    "COLORIZATION TARGET: A 2D architectural site plan or landscape plan "
    "(mặt bằng tổng thể / quy hoạch / cảnh quan) in strict orthographic top-down view — "
    "do NOT tilt, do NOT add perspective, do NOT convert to isometric or 3D. "
    "GOAL: Apply professional flat color fills to each zone in this site plan. "
    "COLOR GUIDE — apply flat tint fills INSIDE existing zone boundaries: "
    "building footprints → light warm grey or terracotta roof-plan tone; "
    "tree/shrub circle symbols → layered green (medium to dark green per canopy size); "
    "lawn/grass zones → flat mid-green; "
    "roads, driveways, footpaths → flat light grey; "
    "water features (pools, ponds, fountains) → flat turquoise-blue; "
    "parking areas → flat pale grey with existing parking bay lines kept visible; "
    "open plazas/terraces → flat warm stone-grey paving tone. "
    "KEEP visible in the output: all boundary lines, setback lines, dimension lines, "
    "contour lines, grid markers, and annotation text exactly as they appear in the input. "
    "Do NOT redraw, simplify, or remove any existing line. "
    "OUTPUT: The exact same drawing as the input, with flat color fills added. "
    "Same layout. Same proportions. Same orientation. Geometry 100% identical to input."
)

# ---------------------------------------------------------------------------
# CHẤT LƯỢNG ĐẦU RA RIÊNG CHO BẢN VẼ 2D — KHÔNG dùng QUALITY_SUFFIX (3D photography)
# QUALITY_SUFFIX nói về DOF, lens flare, camera photography → sai hoàn toàn cho ảnh
# orthographic top-down. Bản vẽ 2D cần: phẳng, sắc nét, không méo, không có ống kính.
# ---------------------------------------------------------------------------
# Tô PHẲNG, nhạt, KHÔNG bóng — để overlay_linework() dán nét gốc lại mà không bị
# nội dung tối (tường đen/bóng đổ do Gemini vẽ) gây nhân đôi (doubling/ghosting).
_FLAT_COLOR_2D = (
    "COLOUR STYLE — FLAT, LIGHT and SHADOWLESS (this is critical): "
    "fill each room with ONE flat, even, PALE colour wash — like a single paint-bucket fill, "
    "low saturation and high brightness, no gradient across the room. "
    "Do NOT add ANY shadow of any kind: no drop shadow, no cast shadow, no ambient occlusion, "
    "no contact shading, no 3D relief, no volume, no glossy highlight. The plan stays perfectly flat. "
    "Do NOT paint thick black walls or heavy dark poché, and do NOT redraw or thicken any line — "
    "keep all linework as thin and light as in the input (the precise lines are restored afterwards). "
    "Minimise dark pixels everywhere: only pale colour on a white background, nothing dark, nothing shaded."
)

QUALITY_SUFFIX_2D = (
    "Output is a FLAT orthographic top-down coloured floor plan — camera strictly 90° straight down, "
    "NOT a tilted 3D photograph: zero perspective, zero axonometric tilt, zero visible vertical faces, "
    "zero lens flare, zero sky, zero horizon, and zero shadows or relief. "
    "Even, flat, pale colour fills only — no shading gradients, no dark areas. "
    "Keep linework thin and light exactly as in the input; do NOT redraw, thicken, or move any line. "
    "Professional architectural presentation quality. "
    "Do NOT add new text, new dimension numbers, watermarks, borders, or people."
)


def build_drawing_prompt(
    drawing_mode: str,
    drawing_type: str,
    drawing_output: str = "interior",   # xem ánh xạ alias bên dưới
    style_key: str = "",
    context_key: str = "",
    weather_key: str = "",
    user_text: str = "",
    lighting_key: str = "golden_hour",
    is_scan: bool = False,
) -> str:
    """Xây prompt cho bản vẽ 2D AutoCAD / phác thảo tay.

    drawing_mode='3d_perspective' + drawing_output='interior' → phối cảnh nội thất 3D từ mặt bằng.
    drawing_mode='3d_perspective' + drawing_output='exterior' → phối cảnh ngoại thất 3D từ mặt đứng.
    drawing_mode='2d_render' → làm đẹp bản vẽ 2D gốc, GIỮ NGUYÊN góc nhìn top-down:
        drawing_output='floor_plan' (alias cũ: 'interior') → mặt bằng nội thất/tầng, phối màu vật liệu sàn.
        drawing_output='site_plan'  (alias cũ: 'exterior') → mặt bằng tổng thể/cảnh quan, phối màu cây xanh/đường/hồ nước.
    drawing_type='autocad'|'sketch' → gợi ý thêm cho AI về chất lượng đường nét.
    is_scan=True → ảnh AutoCAD là ảnh chụp/scan chất lượng thấp (mờ, nghiêng, nhiễu, watermark),
        khác với file CAD vector xuất sạch. Chỉ có ý nghĩa khi drawing_type='autocad'.
    """
    if drawing_type == "autocad":
        dtype_hint = _AUTOCAD_HINT_SCAN if is_scan else _AUTOCAD_HINT_CLEAN
    else:
        dtype_hint = _SKETCH_HINT
    user = f"Additional requirements: {user_text.strip()}" if user_text.strip() else ""

    if drawing_mode == "3d_perspective":
        if drawing_output == "exterior":
            context = EXTERIOR_CONTEXTS.get(context_key, {}).get("prompt", "")
            weather = EXTERIOR_WEATHER.get(weather_key, {}).get("prompt", "")
            light   = LIGHTING_PRESETS.get(lighting_key, {}).get("exterior", "")
            return _join([DRAWING_ELEVATION_TO_3D, dtype_hint, context, weather, light, user, QUALITY_SUFFIX])
        else:
            style = INTERIOR_STYLES.get(style_key, {}).get("prompt", "") if style_key else ""
            light = LIGHTING_PRESETS.get(lighting_key, {}).get("interior", "")
            return _join([DRAWING_TO_3D, dtype_hint, style, light, user, QUALITY_SUFFIX])
    else:
        # Alias tương thích ngược: UI cũ gửi 'interior'/'exterior'; UI mới có thể gửi
        # trực tiếp 'floor_plan'/'site_plan'.
        is_site_plan = drawing_output in ("exterior", "site_plan")
        base = DRAWING_TO_2D_SITE_PLAN if is_site_plan else DRAWING_TO_2D_FLOOR_PLAN
        # 2D mode dùng hint KHÁC: _AUTOCAD_HINT_CLEAN_2D GIỮ dimension lines,
        # thay vì _AUTOCAD_HINT_CLEAN nói "for reference only" → Gemini xoá hết và vẽ lại.
        if drawing_type == "autocad":
            dtype_hint_2d = _AUTOCAD_HINT_SCAN if is_scan else _AUTOCAD_HINT_CLEAN_2D
        else:
            dtype_hint_2d = _SKETCH_HINT
        # _2D_GEOMETRY_LOCK đứng ĐẦU TIÊN — Gemini ưu tiên instruction đầu cao nhất.
        # _FLAT_COLOR_2D: ép tô PHẲNG, KHÔNG bóng/relief → tránh nội dung tối gây doubling
        # khi overlay_linework() dán nét gốc lại. (Shadow/relief đã bỏ — xem image_utils.py.)
        return _join([
            _2D_GEOMETRY_LOCK, base, dtype_hint_2d,
            _FLAT_COLOR_2D, user, QUALITY_SUFFIX_2D,
        ])


def build_text_edit_prompt(instruction: str) -> str:
    """Prompt cho chỉnh sửa bằng mô tả văn bản — không có mask."""
    return _join([
        "This is a photorealistic architectural render or drawing. "
        "TASK: Apply ONLY the changes described in the instruction below. "
        "ABSOLUTE PRESERVATION RULE — keep pixel-identical everything NOT mentioned in the instruction: "
        "all geometry, room structure, furniture layout, existing colors, materials, "
        "labels, dimensions, annotations, and any element not explicitly described. "
        "Apply the described changes seamlessly with consistent lighting, "
        "matching photorealistic quality, and natural integration with the unchanged surroundings.",
        f"Edit instruction: {instruction.strip()}",
        "Photorealistic quality, seamless integration. No text added, no watermark, "
        "no new elements added unless explicitly instructed.",
    ])


def build_mood_analysis_prompt(mood_key: str) -> str:
    """Prompt cho analyze_mood() — yêu cầu Gemini trả về JSON thông số colour-grading."""
    mood = MOOD_PRESETS.get(mood_key, {}).get("prompt", "balanced natural look")
    return (
        "Analyze this architectural render image carefully. "
        f"Suggest CSS/canvas filter values to colour-grade it towards this mood: '{mood}'. "
        "Consider the image's current brightness, contrast, saturation, and colour temperature "
        "when making suggestions — propose adjustments relative to the image as-is. "
        "Return ONLY a valid JSON object with these exact 4 integer fields within the stated ranges:\n"
        "- 'brightness': 70–130 (100 = unchanged, >100 = brighter, <100 = darker)\n"
        "- 'contrast': 70–140 (100 = unchanged)\n"
        "- 'saturate': 0–150 (100 = unchanged, 0 = greyscale, >100 = more vivid)\n"
        "- 'warmth': 0–50 (0 = unchanged/cool, higher = warmer/more sepia)\n"
        "Return ONLY the JSON object, no explanation, no markdown fences:\n"
        '{"brightness": <int>, "contrast": <int>, "saturate": <int>, "warmth": <int>}'
    )


def build_inpaint_prompt(instruction: str) -> str:
    return _join([
        "You are given a photorealistic architectural render and a second image showing a mask: "
        "the bright magenta region marks the area to edit. "
        "Modify ONLY the masked region according to the instruction below. "
        "Keep absolutely everything outside the mask pixel-identical: "
        "same geometry, materials, colour, lighting and composition. "
        "Blend the edited region seamlessly with its surroundings.",
        f"Edit instruction: {instruction.strip()}",
        "Photorealistic, seamless integration, consistent lighting, no text, no watermark.",
    ])


REFERENCE_INSTRUCTION = (
    "STYLE-REFERENCE RULES — strict separation of concerns between the two images:\n"
    "FROM IMAGE 1 (the PRIMARY SketchUp input) take EVERYTHING structural and spatial: "
    "the exact camera angle and viewpoint, the room geometry, every wall / window / door position, "
    "the spatial layout, and which furniture and objects exist and exactly where they sit. "
    "Your render's composition must match IMAGE 1 — NOT the reference.\n"
    "FROM IMAGE 2 (the style reference) take ONLY the look-and-feel: colour grading, "
    "material tones and finish quality, and lighting mood — so both renders feel like the same project.\n"
    "ABSOLUTE PROHIBITION — DO NOT copy any of the following FROM the reference image: "
    "its camera angle, its room shape or geometry, its furniture layout, any specific object or model, "
    "any screen / TV / monitor content, any signage, logo, text or people, or its overall composition. "
    "If the reference shows a different room, a different angle, or different furniture, IGNORE its "
    "structure completely — treat it purely as a colour-and-material swatch, never as a scene to reproduce."
)


# ---------------------------------------------------------------------------
# PRESETS PAYLOAD — dữ liệu cho frontend dropdowns + placeholder hints
# ---------------------------------------------------------------------------
def presets_payload() -> dict:
    def to_list(d: dict, include_placeholder: bool = False):
        out = []
        for k, v in d.items():
            item = {"key": k, "label": v["label"]}
            if include_placeholder and "placeholder" in v:
                item["placeholder"] = v["placeholder"]
            out.append(item)
        return out

    return {
        "interior_styles":   to_list(INTERIOR_STYLES, include_placeholder=True),
        "exterior_contexts": to_list(EXTERIOR_CONTEXTS, include_placeholder=True),
        "exterior_weather":  to_list(EXTERIOR_WEATHER),
        "lighting_presets":  to_list(LIGHTING_PRESETS),
        "vegetation_density": to_list(VEGETATION_DENSITY),
        "mood_presets":      to_list(MOOD_PRESETS),
        "default_lighting":  "golden_hour",
        "default_vegetation": "moderate",
    }
