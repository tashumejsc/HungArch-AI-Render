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
    "Apply photorealistic materials and lighting ONTO this exact SketchUp clay model — you are "
    "texturing the existing geometry, NOT designing a new room. "
    "ABSOLUTE RULE — preserve with zero tolerance: "
    "the exact camera viewpoint, field of view, perspective projection, and framing; "
    "every wall, floor, ceiling position and dimension, and the room's exact proportions; "
    "the precise location, size and shape of all windows, doors and openings; "
    "all built-in architectural elements (columns, beams, niches, steps, soffits); "
    "the exact position, size, footprint and ORIENTATION of every furniture piece and fixture. "
    "FURNITURE IDENTITY LOCK — this is critical: every furniture piece must stay the SAME object at "
    "the SAME size — keep its shape, proportion and count exactly. DO NOT replace, restyle, enlarge, "
    "shrink, add, remove or rearrange any piece: a plain table must stay that same table at the same "
    "size (do NOT turn it into a larger island or a different counter); keep cabinets at the same "
    "length and height. "
    "COUNT REPEATED SEATS EXACTLY — bar stools and dining chairs are the most common mistake: COUNT "
    "every bar stool at the counter and every chair at each table in the model, and reproduce the "
    "EXACT same number, the SAME stool/chair style, and the SAME arrangement. If the model has 3 bar "
    "stools, render exactly 3 bar stools of that same shape — never add, drop, duplicate or restyle "
    "even one stool or chair, and never swap a stool for a different design. "
    "OPENINGS LOCK — equally critical: keep EXACTLY the same windows, doors and wall openings as the "
    "model: same number, same positions, same sizes. DO NOT add a new window, door or opening, do "
    "NOT remove or enlarge an existing one, and do NOT turn a solid wall into a glazed wall or add "
    "glazing to brighten or balance the room. A wall that is solid (closed) in the model MUST stay a "
    "solid wall in the render — never invent extra windows on it. "
    "NO SYMMETRY COMPLETION — critical: do NOT mirror, duplicate or echo an existing window/door onto "
    "the opposite or an adjacent wall to make the room look balanced or symmetric. The room's "
    "asymmetry is intentional; if only ONE wall has a window, the facing wall stays blank/solid. "
    "Reproduce ONLY the openings actually drawn in the input, even if that leaves a wall empty. "
    "GLAZING LOCK — preserve every GLASS element exactly as in the model (both directions): glass "
    "partition walls, glass doors, glazed curtain walls / facades, glass railings and internal glass "
    "dividers must STAY glass (transparent) at the SAME position, size, framing, mullion/division "
    "pattern and panel count. DO NOT turn an existing glass wall, partition or glass door into a "
    "solid opaque wall, and DO NOT change its frame or split pattern; conversely DO NOT add any new "
    "glass partition, glass wall or glass door that is not in the model. Glass stays glass where it "
    "is; solid stays solid where it is. "
    "DAYLIGHT DIRECTION — natural sunlight and the cast shadows it produces may ONLY enter through "
    "the ACTUAL existing windows, glass walls or glass doors in the model. A SOLID (closed) wall "
    "admits NO light: DO NOT cast sun beams, bright sunlight patches, or window-shaped light/shadow "
    "onto the floor, walls, table or chairs coming from the direction of a solid wall, and do NOT "
    "imply an invisible off-frame window on a solid side. The presence, direction and angle of "
    "daylight must be physically consistent with where the real openings actually are. "
    "LIGHTING / LIGHT FIXTURES — CONDITIONAL RULE: first inspect the input model. "
    "IF the model ALREADY shows light fixtures (pendants, ceiling lights, LED cove strips, "
    "downlights, wall lamps, spotlights), then LOCK them: keep exactly those fixtures at their "
    "positions and types, and DO NOT add any new light fixture or extra cove/LED strip. "
    "IF the model has NO light fixtures at all, you MAY place appropriate light fixtures following "
    "professional architectural lighting-design standards (e.g. ceiling downlights, a cove LED line, "
    "a pendant over a table) — tastefully and realistically, WITHOUT changing any wall or ceiling "
    "geometry. Either way, the room must end up realistically and pleasantly lit. "
    "You may also add: realistic surface materials and finishes, textures, shadows, reflections, "
    "natural daylight through the EXISTING windows, and fine surface detail that does NOT alter any "
    "geometry, size or position. "
    "The room layout, every object's size and position, the camera angle, and the overall composition "
    "must be absolutely identical to the input image — only materials, finishes and (per the rule "
    "above) lighting are new."
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
    "the exact position, size, footprint and orientation of every furniture piece and fixture; "
    "FURNITURE IDENTITY LOCK — every furniture piece must stay the SAME object at the SAME size: "
    "do NOT replace, restyle, enlarge, shrink, add, remove or rearrange any piece (a table stays "
    "that same table at the same size); COUNT every bar stool and every chair and keep the EXACT same "
    "number, style and arrangement — never add, drop or restyle a single stool or chair; "
    "OPENINGS LOCK — keep the SAME windows, doors and wall openings (same number, position, size); "
    "do NOT add a new window/door/opening or turn a solid wall into a glazed one; a solid wall stays solid; "
    "do NOT mirror/duplicate a window onto the opposite wall to make the room symmetric — a blank wall "
    "stays blank; "
    "GLAZING LOCK — keep every existing glass element (glass partition, glass door, curtain wall, "
    "glass railing) as glass at the same position/framing/panel count; do NOT turn existing glass into "
    "a solid wall and do NOT add new glazing; glass stays glass, solid stays solid; "
    "DAYLIGHT DIRECTION — sunlight and its cast shadows may ONLY come through the actual existing "
    "windows/glass; a solid wall admits no light, so do NOT cast sun beams or window-shaped "
    "light/shadow onto floor/furniture from the direction of a solid wall; "
    "LIGHTING FIXTURES LOCK — this model already has its lighting; keep exactly the existing light "
    "fixtures at their positions and do NOT add any new fixture or cove/LED strip (only improve how "
    "realistically the existing lighting renders); "
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
# KẸP PHONG CÁCH (interior) — style chỉ là BẢNG MÀU/VẬT LIỆU, KHÔNG phải danh sách
# đồ nội thất để thêm vào. Ngăn Gemini "mua sắm" thêm đèn/đảo bếp/ghế/cây theo style.
# ---------------------------------------------------------------------------
_INTERIOR_STYLE_CLAMP = (
    "STYLE = MATERIAL PALETTE ONLY: the style description above lists materials, colours, finishes "
    "and a mood. Apply them ONLY as surface materials, finishes and lighting onto the objects and "
    "surfaces ALREADY present in the input model. The style is NOT a shopping list of furniture to "
    "add. DO NOT add, remove, move, resize, duplicate or replace any furniture, cabinet, island, "
    "lighting fixture, appliance, rug, plant or decorative object. If the style names an item "
    "(e.g. a pendant, an island, a vase, a painting) that is NOT already physically present in the "
    "input model, IGNORE that item entirely. "
    "EXACT FURNITURE COUNT — this is critical and the most common mistake to avoid: the output must "
    "contain the EXACT SAME set and NUMBER of furniture pieces as the clay model — no more, no fewer. "
    "DO NOT add any extra seating (sofa, sofa set, armchair, bench, lounge chairs, extra dining "
    "chairs, extra BAR STOOLS), table, console, shelving or decor to 'furnish', 'complete' or 'fill' "
    "the room — even if an area looks empty or the style name implies a fuller 'living' space; "
    "and equally DO NOT drop or remove any existing seat. Count the bar stools and the chairs in the "
    "model and keep that EXACT number and style. Any empty floor area — "
    "especially near a window or along a wall — MUST stay empty unless a real object is clearly "
    "visible there in the input model. The render must contain EXACTLY the same objects, in the same "
    "count, at the same sizes, shapes and positions, as the input clay model — only materials are new."
)

# ---------------------------------------------------------------------------
# KẸP CÔNG TRÌNH (exterior) — bối cảnh/thời tiết/cây xanh chỉ áp cho MÔI TRƯỜNG quanh
# nhà; bản thân công trình bị khóa cứng (không restyle/đổi tỷ lệ/thêm tầng).
# ---------------------------------------------------------------------------
_EXTERIOR_BUILDING_LOCK = (
    "BUILDING IS LOCKED, ONLY THE ENVIRONMENT IS ADDED: the context, weather, lighting and "
    "vegetation described below apply ONLY to the surroundings AROUND the building (sky, ground, "
    "street, neighbouring structures, plants, people, vehicles, atmosphere). The BUILDING ITSELF — "
    "its massing, facade, every wall / window / door / balcony / railing / roof line, and its exact "
    "proportions and dimensions — must stay EXACTLY as in the input model. DO NOT restyle, "
    "re-proportion, extend, simplify, add storeys to, or remove any part of the building; only apply "
    "realistic materials and lighting onto its existing geometry. Add the described environment "
    "AROUND the locked building — never reshape the building to fit the scene."
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
# ĐỒNG BỘ ĐÈN CHO RENDER ĐA GÓC — mỗi góc là 1 lần gọi Gemini độc lập nên hệ đèn
# hay khác nhau (góc thì đèn thả, góc thì cove). Ép đèn ĐƠN GIẢN & THỐNG NHẤT để 3
# góc nhìn như cùng một công trình.
# ---------------------------------------------------------------------------
_MULTI_ANGLE_LIGHTING = (
    "MULTI-ANGLE CONSISTENCY — this render is one of a set showing the SAME room from different "
    "camera angles, so the lighting scheme MUST be simple and identical across every angle: use ONLY "
    "recessed ceiling downlights plus at most one continuous cove LED line. DO NOT add decorative "
    "pendant lights, chandeliers, hanging lamps or ceiling-mounted AC cassette units. Keep the same "
    "wall, floor and ceiling materials and the same warm lighting tone as the style reference, so all "
    "angles read as one consistent project."
)


# ---------------------------------------------------------------------------
# GEMINI PROMPT BUILDERS
# Gemini = instruction-following model → cần GEOMETRY_LOCK + mô tả chi tiết
# ---------------------------------------------------------------------------
def build_interior_prompt(
    style_key: str,
    user_text: str = "",
    lighting_key: str = "golden_hour",
    input_type: str = "wireframe",
    multi_angle: bool = False,
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
    ma = _MULTI_ANGLE_LIGHTING if multi_angle else ""
    # _INTERIOR_STYLE_CLAMP ngay sau style để kẹp lại: style chỉ là palette, không thêm đồ.
    return _join([lock, style, _INTERIOR_STYLE_CLAMP, light, ma, user, QUALITY_SUFFIX])


def build_exterior_prompt(
    context_key: str,
    weather_key: str,
    user_text: str = "",
    lighting_key: str = "golden_hour",
    vegetation_key: str = "moderate",
    input_type: str = "wireframe",
    multi_angle: bool = False,
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
    ma = _MULTI_ANGLE_LIGHTING if multi_angle else ""
    # _EXTERIOR_BUILDING_LOCK đứng ngay sau lock: bối cảnh chỉ áp môi trường, khóa công trình.
    return _join([lock, _EXTERIOR_BUILDING_LOCK, context, weather, light, veg, ma, user, QUALITY_SUFFIX])


# ---------------------------------------------------------------------------
# TAB 3: BẢN VẼ 2D
# Sub-mode 'drawing_mode':
#   '3d_perspective'  → AI tạo phối cảnh 3D góc người đứng (eye-level) từ mặt bằng/mặt đứng 2D
#   '2d_render'       → AI làm đẹp bản vẽ 2D gốc, GIỮ NGUYÊN góc nhìn 2D (V1.0.0 —
#                        không đổi sang 3D, không overlay, không geometry-lock).
# 'drawing_type': 'autocad' | 'sketch'
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
# LAM DEP BAN VE 2D — giu nguyen goc nhin 2D goc (khong doi sang 3D).
# Khoi phuc cach tiep can don gian cua V1.0.0 — da bo chuoi thu nghiem Top-View
# 3D / overlay / geometry-lock vi ket qua khong on dinh.
# ---------------------------------------------------------------------------
DRAWING_TO_2D = (
    "This is a 2D architectural floor plan, elevation, or technical drawing. "
    "TASK: COLOUR IN this existing drawing to make a professional, beautiful coloured "
    "presentation plan — you are colouring the plan that is already there, NOT redrawing it. "
    "LAYOUT LOCK (most important): keep the SAME overall outline / footprint shape and the SAME "
    "overall aspect ratio as the input; keep the SAME number of rooms, each in its SAME position "
    "with the SAME relative size and proportion; keep every wall, partition, door and window where "
    "it is drawn. DO NOT move, resize, rotate, merge, split, add or remove any room or wall, and "
    "DO NOT re-imagine the layout from scratch — the coloured result must be instantly recognisable "
    "as the very same plan, with rooms in the same places at the same proportions. "
    "VIEW LOCK: keep the same flat 2D top-down plan view (or elevation view) — DO NOT convert to 3D "
    "perspective, DO NOT tilt or change the viewing angle. "
    "ENHANCE to professional presentation standard (this is where you may be rich and beautiful): "
    "fill each room with an appropriate, vivid-but-tasteful coloured material surface "
    "(warm honey wood tone for parquet floors, cool grey-blue for tiles, soft beige for carpet, "
    "dark solid fill for walls in plan, light tone for exterior walls); "
    "render furniture and fixtures as clean flat coloured symbols in their drawn positions; "
    "add soft shadow beneath furniture and walls for subtle depth; "
    "add colour fills for landscape elements "
    "(tree circles → lush green foliage in plan view, pool/water → turquoise blue fill, "
    "lawns → green, roads/paving → grey); "
    "improve overall linework crispness and professional polish; "
    "colour-code different room zones with a tasteful architectural palette. "
    "Output: a beautiful, vivid, colour-rendered architectural presentation plan at the exact same "
    "2D view, with the layout, room positions and proportions matching the input."
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
    drawing_mode='2d_render' → làm đẹp bản vẽ 2D gốc, GIỮ NGUYÊN góc nhìn 2D
        (V1.0.0 — không đổi sang 3D, không overlay, không geometry-lock).
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
        # 2d_render — làm đẹp bản vẽ 2D gốc, giữ nguyên góc nhìn (cách V1.0.0).
        return _join([DRAWING_TO_2D, dtype_hint, user, QUALITY_SUFFIX])


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
    "An additional reference image is provided. Match its overall colour grading, "
    "material palette, mood and lighting style so this render stays visually consistent "
    "with it, while still respecting the geometry of the main SketchUp input."
)


# ---------------------------------------------------------------------------
# ĐỒNG BỘ STYLE BẰNG VĂN BẢN (chống reference dominance triệt để)
# Thay vì gửi ẢNH reference (Gemini hay copy bố cục cam1 -> sai góc), ta trích mô tả
# vật liệu/ánh sáng của cam1 thành TEXT rồi tiêm vào prompt cam2. Text không làm lệch
# hình học -> cam2 đúng góc, chỉ mượn style.
# ---------------------------------------------------------------------------
STYLE_DESCRIPTION_PROMPT = (
    "You are given a finished architectural render. Describe ONLY its MATERIALS, COLOURS, "
    "FINISHES and LIGHTING — as a concise list another artist could use to reproduce the exact "
    "same look on a DIFFERENT camera angle of the same space. "
    "Cover: floor material & colour; wall finishes; ceiling treatment; cabinetry / furniture "
    "materials and colours; metal / accent finishes; and the lighting (colour temperature, key "
    "fixtures, overall mood and time of day). "
    "Do NOT describe the room layout, the camera angle, the composition, or which object sits where "
    "— ONLY the look, materials and lighting. Answer in 2–4 sentences, no preamble."
)

REFERENCE_STYLE_SYNC = (
    "STYLE SYNC — render the scene using EXACTLY the following material, colour and lighting scheme, "
    "taken from a previously-approved render of the SAME project so that every camera angle matches. "
    "Apply these finishes and this lighting onto THIS image's geometry; do NOT alter the geometry, "
    "camera angle or composition to match — only adopt the materials and lighting described here:"
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
