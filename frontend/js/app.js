// HungArch AI Render — điều khiển chính (Gemini-only v2.1 + tab BẢN VẼ 2D).
(() => {
  const $ = (id) => document.getElementById(id);
  const files = {
    interiorImage: null,
    exteriorImage: null,
    drawingImage:  null,
    referenceImage: null,
  };
  let currentTab = 'interior';
  let currentResult    = null;
  let maskTool         = null;
  let pendingBeforeUrl = null;

  // Hậu kỳ
  let currentInpaintMode      = 'mask';  // 'mask' | 'text'
  let pendingEditResult       = null;    // kết quả text-edit chờ xác nhận
  let _pendingEditInstruction = null;    // instruction text-edit đang chờ Apply

  // C2 — Render lại từ gốc
  const MAX_HISTORY = 30;
  let originalSourceFile   = null;  // File ảnh SketchUp gốc của lần render cuối
  let originalRenderParams = null;  // Params form của lần render cuối
  let originalRefFile      = null;  // Reference image của lần render cuối
  let appliedEdits         = [];    // [{type, instruction}] kể từ lần render đó

  // Input type: 'wireframe' | 'textured'
  let currentInputType  = 'wireframe';
  // Drawing sub-states
  let currentDrawingMode   = '3d_perspective';  // '3d_perspective' | '2d_render'
  let currentDrawingType   = 'autocad';         // 'autocad' | 'sketch'
  let currentDrawingOutput = 'interior';        // 'interior' | 'exterior' (chỉ cho 3d_perspective)

  // Hậu kỳ
  let _currentHueRotate = 0;
  let _adjFilterStr     = 'none';
  let _exportFormat     = 'png';
  let _exportQuality    = 0.90;

  const history = [];

  // ══════════════════════════════════════════════
  //  Toast
  // ══════════════════════════════════════════════

  // Dịch các lỗi API thường gặp sang tiếng Việt
  function viError(msg) {
    if (!msg) return 'Lỗi không xác định.';
    if (/api.key|api_key|api key/i.test(msg))
      return 'Thiếu hoặc sai Gemini API key. Vào "Cấu hình khóa API" để nhập lại.';
    if (/quota|rate.limit|429/i.test(msg))
      return 'Đã vượt hạn mức API (rate limit). Chờ 1–2 phút rồi thử lại.';
    if (/billing|payment|403/i.test(msg))
      return 'Tài khoản Google Cloud chưa bật thanh toán (billing). Gemini Image không có free tier.';
    if (/not.found|404|not.support/i.test(msg))
      return 'Model không được hỗ trợ trên API này. Hãy chọn model khác (Flash 3.1 hoặc Pro 3.0).';
    if (/safety|content.filter|blocked/i.test(msg))
      return 'Nội dung bị chặn bởi bộ lọc an toàn của Google. Hãy thử lại hoặc điều chỉnh mô tả.';
    if (/timeout|deadline|503|502/i.test(msg))
      return 'API Gemini đang quá tải. Chờ 1 phút rồi thử lại.';
    if (/image.*too.large|payload.too/i.test(msg))
      return 'Ảnh đầu vào quá lớn. Hãy giảm kích thước ảnh xuống dưới 5 MB rồi thử lại.';
    return msg;
  }

  function toast(msg, ok = true) {
    const t = $('toast');
    const text = ok ? msg : viError(msg);
    t.textContent = text;
    t.className = 'fixed bottom-4 left-1/2 -translate-x-1/2 px-5 py-3 rounded-lg text-sm shadow-lg z-50 max-w-sm text-center ' +
      (ok ? 'bg-emerald-600 text-white' : 'bg-red-600 text-white');
    t.classList.remove('hidden');
    // Lỗi hiển thị lâu hơn (10s) để đủ thời gian đọc; thông báo ok hiển thị 3.5s
    setTimeout(() => t.classList.add('hidden'), ok ? 3500 : 10000);
  }

  // ══════════════════════════════════════════════
  //  Tab dots — chấm xanh khi đã upload ảnh
  // ══════════════════════════════════════════════
  const TAB_FILE_MAP = { interior: 'interiorImage', exterior: 'exteriorImage', drawing: 'drawingImage' };

  function updateTabDots() {
    document.querySelectorAll('.tab-btn').forEach((btn) => {
      const dot = btn.querySelector('.tab-dot');
      if (!dot) return;
      dot.classList.toggle('hidden', !files[TAB_FILE_MAP[btn.dataset.tab]]);
    });
  }

  // ══════════════════════════════════════════════
  //  Dropzones
  // ══════════════════════════════════════════════
  function initDropzones() {
    document.querySelectorAll('.dropzone').forEach((dz) => {
      const targetId = dz.dataset.target;
      const input = $(targetId);
      const img   = dz.querySelector('.preview');
      const ph    = dz.querySelector('.ph');

      const show = (file) => {
        files[targetId] = file;
        img.src = URL.createObjectURL(file);
        img.classList.remove('hidden');
        ph.classList.add('hidden');
        updateTabDots();
      };

      dz.addEventListener('click', () => input.click());
      input.addEventListener('change', (e) => { if (e.target.files[0]) show(e.target.files[0]); });
      dz.addEventListener('dragover',  (e) => { e.preventDefault(); dz.classList.add('dragover'); });
      dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
      dz.addEventListener('drop', (e) => {
        e.preventDefault();
        dz.classList.remove('dragover');
        if (e.dataTransfer.files[0]) show(e.dataTransfer.files[0]);
      });
    });
  }

  // ══════════════════════════════════════════════
  //  Tabs chính (NỘI THẤT / NGOẠI THẤT / BẢN VẼ 2D)
  // ══════════════════════════════════════════════
  function initTabs() {
    document.querySelectorAll('.tab-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        currentTab = btn.dataset.tab;
        document.querySelectorAll('.tab-btn').forEach((b) => b.classList.toggle('active', b === btn));
        $('tab-interior').classList.toggle('hidden', currentTab !== 'interior');
        $('tab-exterior').classList.toggle('hidden', currentTab !== 'exterior');
        $('tab-drawing').classList.toggle('hidden',  currentTab !== 'drawing');
        updateVegetationVisibility();
      });
    });
    document.querySelector('.tab-btn[data-tab="interior"]').classList.add('active');
  }

  // ══════════════════════════════════════════════
  //  Tab BẢN VẼ 2D — sub-controls
  // ══════════════════════════════════════════════
  const DRAWING_MODE_HINTS = {
    '3d_perspective_interior': 'AI đọc mặt bằng và tưởng tượng phối cảnh nội thất 3D thực tế.',
    '3d_perspective_exterior': 'AI đọc mặt đứng và tạo phối cảnh ngoại thất 3D với bối cảnh thực tế.',
    '2d_render':               'AI giữ nguyên góc nhìn 2D, chỉ nâng lên chất lượng trình bày đẹp hơn.',
  };

  function _updateDrawingHint() {
    const key = currentDrawingMode === '2d_render'
      ? '2d_render'
      : `3d_perspective_${currentDrawingOutput}`;
    $('drawingModeHint').textContent = DRAWING_MODE_HINTS[key];
  }

  function _syncDrawingControls() {
    const is3d = currentDrawingMode === '3d_perspective';
    const isExt = currentDrawingOutput === 'exterior';
    // Ẩn/hiện khu output toggle (chỉ cho 3D)
    $('drawingOutputWrap').classList.toggle('hidden', !is3d);
    // Ẩn/hiện style nội thất
    $('drawingStyleWrap').classList.toggle('hidden', !is3d || isExt);
    // Ẩn/hiện bối cảnh + thời tiết ngoại thất
    $('drawingExtWrap').classList.toggle('hidden', !is3d || !isExt);
    _updateDrawingHint();
  }

  function initDrawingTab() {
    // Drawing mode toggle (3D / 2D render)
    ['dm3d', 'dm2d'].forEach((id) => {
      $(id).addEventListener('click', () => {
        currentDrawingMode = $(id).dataset.dmode;
        $('dm3d').classList.toggle('active', currentDrawingMode === '3d_perspective');
        $('dm2d').classList.toggle('active', currentDrawingMode === '2d_render');
        _syncDrawingControls();
      });
    });

    // Drawing output toggle (Nội thất / Ngoại thất)
    ['doInterior', 'doExterior'].forEach((id) => {
      $(id).addEventListener('click', () => {
        currentDrawingOutput = $(id).dataset.doutput;
        $('doInterior').classList.toggle('active', currentDrawingOutput === 'interior');
        $('doExterior').classList.toggle('active', currentDrawingOutput === 'exterior');
        _syncDrawingControls();
      });
    });

    // Drawing type toggle (AutoCAD / sketch)
    ['dtAutocad', 'dtSketch'].forEach((id) => {
      $(id).addEventListener('click', () => {
        currentDrawingType = $(id).dataset.dtype;
        $('dtAutocad').classList.toggle('active', currentDrawingType === 'autocad');
        $('dtSketch').classList.toggle('active',  currentDrawingType === 'sketch');
      });
    });
  }

  // ══════════════════════════════════════════════
  //  Input type toggle (Đen trắng / Đã vật liệu)
  // ══════════════════════════════════════════════
  const INPUT_TYPE_HINTS = {
    wireframe: 'AI thêm vật liệu + ánh sáng hoàn toàn mới theo preset đã chọn.',
    textured:  'AI giữ nguyên vật liệu đã có, chỉ nâng lên chất lượng photorealistic.',
  };

  function initInputType() {
    $('itWireframe').dataset.type = 'wireframe';
    $('itTextured').dataset.type  = 'textured';
    ['itWireframe', 'itTextured'].forEach((id) => {
      $(id).addEventListener('click', () => {
        currentInputType = $(id).dataset.type;
        $('itWireframe').classList.toggle('active', currentInputType === 'wireframe');
        $('itTextured').classList.toggle('active',  currentInputType === 'textured');
        $('inputTypeHint').textContent = INPUT_TYPE_HINTS[currentInputType];
      });
    });
  }

  // ══════════════════════════════════════════════
  //  View tabs (Kết quả / So sánh / Điều chỉnh)
  // ══════════════════════════════════════════════
  const VIEW_IDS = ['viewResult', 'viewCompare', 'viewAdjust'];
  const TAB_IDS  = ['vtResult',   'vtCompare',   'vtAdjust'];

  function switchToView(viewId) {
    VIEW_IDS.forEach((id) => $(id).classList.toggle('hidden', id !== viewId));
    TAB_IDS.forEach((id, i) => $(id).classList.toggle('active', VIEW_IDS[i] === viewId));
  }

  function initViewTabs() {
    $('vtResult').addEventListener('click', () => switchToView('viewResult'));
    $('vtCompare').addEventListener('click', () => {
      if (!currentResult) { toast('Hãy render ảnh trước.', false); return; }
      switchToView('viewCompare');
    });
    $('vtAdjust').addEventListener('click', () => {
      if (!currentResult) { toast('Hãy render ảnh trước.', false); return; }
      switchToView('viewAdjust');
    });
  }

  // ══════════════════════════════════════════════
  //  Before / After comparison slider
  // ══════════════════════════════════════════════
  function initCompareSlider() {
    const wrap = $('compareWrap');
    const over = $('cmpAfter');
    const div  = $('cmpDivider');
    let drag = false;

    const setPos = (clientX) => {
      const r   = wrap.getBoundingClientRect();
      const pct = Math.max(5, Math.min(95, (clientX - r.left) / r.width * 100));
      div.style.left     = pct + '%';
      over.style.clipPath = `inset(0 ${(100 - pct).toFixed(1)}% 0 0)`;
    };

    div.addEventListener('mousedown',  (e) => { drag = true; e.preventDefault(); });
    wrap.addEventListener('mousemove', (e) => { if (drag) setPos(e.clientX); });
    document.addEventListener('mouseup',  () => { drag = false; });
    div.addEventListener('touchstart',  (e) => { drag = true; e.preventDefault(); });
    wrap.addEventListener('touchmove',  (e) => { if (drag) { setPos(e.touches[0].clientX); e.preventDefault(); } });
    document.addEventListener('touchend', () => { drag = false; });
  }

  // ══════════════════════════════════════════════
  //  Color presets
  // ══════════════════════════════════════════════
  const COLOR_PRESETS = {
    natural:   { b: 100, c: 100, s: 100, w: 0,  hue: 0   },
    film:      { b: 97,  c: 108, s: 80,  w: 15, hue: 0   },
    cinematic: { b: 88,  c: 118, s: 72,  w: 8,  hue: 0   },
    warm:      { b: 105, c: 103, s: 112, w: 35, hue: 0   },
    cool:      { b: 102, c: 106, s: 108, w: 0,  hue: -18 },
    bw:        { b: 100, c: 118, s: 0,   w: 0,  hue: 0   },
  };

  function applyColorPreset(name) {
    const p = COLOR_PRESETS[name] || COLOR_PRESETS.natural;
    $('adjBrightness').value = p.b;
    $('adjContrast').value   = p.c;
    $('adjSaturate').value   = p.s;
    $('adjWarmth').value     = p.w;
    _currentHueRotate = p.hue;
    updateAdj();
    document.querySelectorAll('.color-preset-btn').forEach((btn) =>
      btn.classList.toggle('active', btn.dataset.preset === name)
    );
  }

  function initColorPresets() {
    document.querySelectorAll('.color-preset-btn').forEach((btn) => {
      btn.addEventListener('click', () => applyColorPreset(btn.dataset.preset));
    });
  }

  // ══════════════════════════════════════════════
  //  Image adjustments
  // ══════════════════════════════════════════════
  function buildAdjFilter() {
    const b = ($('adjBrightness').value / 100).toFixed(2);
    const c = ($('adjContrast').value   / 100).toFixed(2);
    const s = ($('adjSaturate').value   / 100).toFixed(2);
    const w = parseInt($('adjWarmth').value);
    const sepia = (w * 0.5).toFixed(1);
    let f = `brightness(${b}) contrast(${c}) saturate(${s}) sepia(${sepia}%)`;
    if (_currentHueRotate !== 0) f += ` hue-rotate(${_currentHueRotate}deg)`;
    return f;
  }

  function updateAdj() {
    _adjFilterStr = buildAdjFilter();
    $('adjImg').style.filter = _adjFilterStr;
    $('vBr').textContent = $('adjBrightness').value;
    $('vCo').textContent = $('adjContrast').value;
    $('vSa').textContent = $('adjSaturate').value;
    $('vWa').textContent = $('adjWarmth').value;
    // Sync mini panel sliders (Tầng 3)
    [['ppBr','ppBrVal','adjBrightness'],['ppCo','ppCoVal','adjContrast'],
     ['ppSa','ppSaVal','adjSaturate'], ['ppWa','ppWaVal','adjWarmth']].forEach(([pp,pv,main]) => {
      const el = $(pp); if (el) { el.value = $(main).value; $(pv).textContent = $(main).value; }
    });
  }

  function resetAdj() {
    ['adjBrightness', 'adjContrast', 'adjSaturate'].forEach((id) => { $(id).value = 100; });
    $('adjWarmth').value = 0;
    _currentHueRotate = 0;
    _adjFilterStr = 'none';
    if ($('adjImg')) $('adjImg').style.filter = 'none';
    $('vBr').textContent = $('vCo').textContent = $('vSa').textContent = '100';
    $('vWa').textContent = '0';
    document.querySelectorAll('.color-preset-btn').forEach((b) =>
      b.classList.toggle('active', b.dataset.preset === 'natural')
    );
    // Sync mini panel sliders về default
    [['ppBr','ppBrVal','adjBrightness'],['ppCo','ppCoVal','adjContrast'],
     ['ppSa','ppSaVal','adjSaturate'], ['ppWa','ppWaVal','adjWarmth']].forEach(([pp,pv,main]) => {
      const el = $(pp); if (el) { el.value = $(main).value; $(pv).textContent = $(main).value; }
    });
  }

  function initAdjust() {
    ['adjBrightness', 'adjContrast', 'adjSaturate', 'adjWarmth'].forEach((id) => {
      $(id).addEventListener('input', () => {
        document.querySelectorAll('.color-preset-btn').forEach((b) => b.classList.remove('active'));
        updateAdj();
      });
    });
    $('downloadAdjBtn').addEventListener('click', downloadAdjusted);
    $('resetAdjBtn').addEventListener('click', resetAdj);
  }

  // ══════════════════════════════════════════════
  //  Export format
  // ══════════════════════════════════════════════
  function initExportFormat() {
    document.querySelectorAll('.fmt-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        _exportFormat = btn.dataset.fmt;
        document.querySelectorAll('.fmt-btn').forEach((b) =>
          b.classList.toggle('active', b === btn)
        );
        const needQual = _exportFormat !== 'png';
        $('qualWrap').classList.toggle('hidden', !needQual);
        $('qualWrap').classList.toggle('flex', needQual);
      });
    });
    $('exportQual').addEventListener('input', (e) => {
      _exportQuality = e.target.value / 100;
      $('exportQualVal').textContent = e.target.value;
    });
  }

  function downloadAdjusted() {
    if (!currentResult) return;
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width  = img.naturalWidth;
      canvas.height = img.naturalHeight;
      const ctx = canvas.getContext('2d');
      if (_adjFilterStr && _adjFilterStr !== 'none') ctx.filter = _adjFilterStr;
      ctx.drawImage(img, 0, 0);
      const mime = _exportFormat === 'jpeg' ? 'image/jpeg'
                 : _exportFormat === 'webp' ? 'image/webp'
                 : 'image/png';
      const qual = _exportFormat === 'png' ? undefined : _exportQuality;
      canvas.toBlob((blob) => {
        const url  = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href     = url;
        link.download = `hungarch_adj_${currentResult.seed || 'render'}.${_exportFormat}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        setTimeout(() => URL.revokeObjectURL(url), 200);
      }, mime, qual);
    };
    img.src = currentResult.url;
  }

  // ══════════════════════════════════════════════
  //  Inpaint mode toggle (Vẽ mask ↔ Mô tả văn bản)
  // ══════════════════════════════════════════════
  function initInpaintModeToggle() {
    ['imMask', 'imText'].forEach((id) => {
      $(id).addEventListener('click', () => {
        currentInpaintMode = $(id).dataset.imode;
        $('imMask').classList.toggle('active', currentInpaintMode === 'mask');
        $('imText').classList.toggle('active', currentInpaintMode === 'text');
        $('maskModeWrap').classList.toggle('hidden', currentInpaintMode !== 'mask');
        $('textModeWrap').classList.toggle('hidden', currentInpaintMode !== 'text');
      });
    });
  }

  // ══════════════════════════════════════════════
  //  Mask mode
  // ══════════════════════════════════════════════
  function setMaskMode(mode) {
    if (!currentResult) { toast('Hãy render ảnh trước.', false); return; }
    maskTool.enable(true);
    maskTool.setMode(mode);
    $('drawMaskBtn').classList.toggle('m-draw',  mode === 'draw');
    $('drawMaskBtn').classList.toggle('m-erase', false);
    $('eraseMaskBtn').classList.toggle('m-erase', mode === 'erase');
    $('eraseMaskBtn').classList.toggle('m-draw',  false);
    switchToView('viewResult');
    toast(mode === 'draw' ? '🖌️ Chế độ VẼ — bôi lên vùng cần sửa.' : '🧹 Chế độ TẨY — kéo để xóa vùng đã bôi.');
  }

  function stopMaskMode() {
    maskTool.enable(false);
    $('drawMaskBtn').classList.remove('m-draw', 'm-erase');
    $('eraseMaskBtn').classList.remove('m-draw', 'm-erase');
  }

  // ══════════════════════════════════════════════
  //  Presets + status
  // ══════════════════════════════════════════════
  function fillSelect(sel, items) {
    if (!sel) return;
    sel.innerHTML = items.map((i) => `<option value="${i.key}">${i.label}</option>`).join('');
  }

  const stylePlaceholders   = {};
  const contextPlaceholders = {};

  function updateVegetationVisibility() {
    $('vegetationWrap').classList.toggle('hidden', currentTab !== 'exterior');
  }

  // ══════════════════════════════════════════════
  //  Tech accordion summary (lighting · model · resolution + cost)
  // ══════════════════════════════════════════════
  function updateTechSummary() {
    const lSel = $('lightingSelect');
    const mSel = $('modelSelect');
    const rSel = $('resolutionSelect');
    const lighting = lSel?.options[lSel.selectedIndex]?.text || '';
    const model    = mSel?.options[mSel.selectedIndex]?.text || '';
    const res      = rSel?.value || '';
    const techSum  = $('techSummary');
    const costPill = $('techCostPill');
    if (techSum) techSum.textContent = [lighting, model, res].filter(Boolean).join(' · ');
    if (costPill) {
      const isFlash = (mSel?.value || '').includes('flash');
      costPill.textContent  = isFlash ? '~$0.04/ảnh' : '~$0.15/ảnh';
      costPill.className = 'ml-auto text-[10px] px-2 py-0.5 rounded-full whitespace-nowrap shrink-0 ' +
        (isFlash ? 'bg-emerald-900/50 text-emerald-400' : 'bg-amber-900/50 text-amber-400');
    }
  }

  function applyStylePlaceholder() {
    const ph = stylePlaceholders[$('styleSelect').value];
    if (ph) $('interiorPrompt').placeholder = ph;
  }

  function applyContextPlaceholder() {
    const ph = contextPlaceholders[$('contextSelect').value];
    if (ph) $('exteriorPrompt').placeholder = ph;
  }

  async function loadPresets() {
    try {
      const p = await API.getPresets();

      fillSelect($('styleSelect'), p.interior_styles);
      p.interior_styles.forEach((s) => { if (s.placeholder) stylePlaceholders[s.key] = s.placeholder; });
      applyStylePlaceholder();

      // Drawing tab reuses interior styles for 3D perspective mode
      fillSelect($('drawingStyleSelect'), p.interior_styles);

      fillSelect($('contextSelect'), p.exterior_contexts);
      p.exterior_contexts.forEach((c) => { if (c.placeholder) contextPlaceholders[c.key] = c.placeholder; });
      applyContextPlaceholder();

      // Drawing tab — bối cảnh + thời tiết ngoại thất (dùng cùng dữ liệu với tab Ngoại Thất)
      fillSelect($('drawingContextSelect'), p.exterior_contexts);
      fillSelect($('drawingWeatherSelect'), p.exterior_weather);

      fillSelect($('weatherSelect'),    p.exterior_weather);
      fillSelect($('lightingSelect'),   p.lighting_presets);
      if (p.default_lighting)   $('lightingSelect').value = p.default_lighting;
      fillSelect($('vegetationSelect'), p.vegetation_density);
      if (p.default_vegetation) $('vegetationSelect').value = p.default_vegetation;
      fillSelect($('modelSelect'),      p.models);
      if (p.default_model)      $('modelSelect').value = p.default_model;
      fillSelect($('resolutionSelect'), p.resolutions.map((r) => ({ key: r, label: r })));
      if (p.default_resolution) $('resolutionSelect').value = p.default_resolution;

      if (p.mood_presets) fillSelect($('moodSelect'), p.mood_presets);

      updateVegetationVisibility();
      updateTechSummary();
      applyStatus(p);
    } catch (e) {
      toast(e.message, false);
    }
  }

  function applyStatus(s) {
    const st = $('apiStatus');
    if (s.api_key_configured) {
      st.textContent = '● API sẵn sàng';
      st.className = 'ml-auto text-xs px-2 py-1 rounded-full bg-emerald-900 text-emerald-300';
    } else {
      st.textContent = '● Thiếu API key';
      st.className = 'ml-auto text-xs px-2 py-1 rounded-full bg-red-900 text-red-300';
    }
    $('keySummary').textContent = s.api_key_configured ? '— Gemini ✓' : '— Gemini ✗';
    if (!s.api_key_configured) $('keyPanel').open = true;
  }

  async function saveKeys() {
    const gemini = $('geminiKey').value.trim();
    if (!gemini) { toast('Hãy nhập Gemini API key.', false); return; }
    try {
      await API.setConfig({ gemini_api_key: gemini });
      $('geminiKey').value = '';
      await loadPresets();
      toast('Đã lưu Gemini API key.');
    } catch (e) {
      toast(e.message, false);
    }
  }

  // ══════════════════════════════════════════════
  //  Loading
  // ══════════════════════════════════════════════
  function setLoading(on, text) {
    $('loadingOverlay').classList.toggle('hidden', !on);
    if (text) $('loadingText').textContent = text;
  }

  // ══════════════════════════════════════════════
  //  Hiển thị kết quả
  // ══════════════════════════════════════════════
  async function showResult(data) {
    currentResult = {
      url:       data.image_url,
      seed:      data.seed,
      filename:  data.image_filename,
      beforeUrl: pendingBeforeUrl,
    };

    $('resultPlaceholder').classList.add('hidden');
    $('maskCanvas').classList.remove('hidden');
    await maskTool.load(data.image_url);
    stopMaskMode();

    // Đặt lại nhãn so sánh về mặc định cho render mới
    $('cmpLabelBefore').textContent = 'Gốc (SketchUp)';
    $('cmpLabelAfter').textContent  = 'Render (AI)';
    if (pendingBeforeUrl) $('cmpBefore').src = pendingBeforeUrl;
    $('cmpAfter').src = data.image_url;
    $('cmpAfter').style.clipPath = 'inset(0 50% 0 0)';
    $('cmpDivider').style.left = '50%';

    $('adjImg').src = data.image_url;
    resetAdj();

    $('seedBadge').classList.remove('hidden');
    $('seedBadge').classList.add('flex');
    $('seedValue').textContent = data.seed;

    $('resultActions').classList.remove('hidden');
    $('inpaintBtn').disabled = false;
    $('textEditBtn').disabled = false;

    switchToView('viewResult');
    addHistory(data);
    updatePostProcessLock();
  }

  function addHistory(data) {
    history.unshift(data);
    if (history.length > MAX_HISTORY) history.splice(MAX_HISTORY);
    const wrap = $('history');
    wrap.innerHTML = history
      .map((h) => `<img src="${h.image_url}" class="history-thumb" data-url="${h.image_url}" data-seed="${h.seed}" data-file="${h.image_filename}" title="Seed: ${h.seed}" />`)
      .join('');
    wrap.querySelectorAll('.history-thumb').forEach((el) => {
      el.addEventListener('click', () => showResult({
        image_url: el.dataset.url, seed: el.dataset.seed, image_filename: el.dataset.file,
      }));
    });
  }

  // ══════════════════════════════════════════════
  //  Render (xử lý cả 3 tab)
  // ══════════════════════════════════════════════
  async function doRender() {
    const imgFile = currentTab === 'interior' ? files.interiorImage
                  : currentTab === 'exterior' ? files.exteriorImage
                  : files.drawingImage;

    if (!imgFile) {
      toast(
        currentTab === 'drawing'
          ? 'Hãy tải ảnh bản vẽ trước.'
          : 'Hãy tải ảnh SketchUp trước.',
        false
      );
      return;
    }

    pendingBeforeUrl = URL.createObjectURL(imgFile);

    // Lưu thông tin render gốc để "Render lại từ gốc" (C2)
    originalSourceFile   = imgFile;
    originalRefFile      = files.referenceImage || null;
    originalRenderParams = {
      mode: currentTab, input_type: currentInputType,
      lighting: $('lightingSelect').value, vegetation: $('vegetationSelect').value,
      style:   currentTab === 'interior' ? $('styleSelect').value  : $('drawingStyleSelect').value,
      context: currentTab === 'exterior' ? $('contextSelect').value : $('drawingContextSelect').value,
      weather: currentTab === 'exterior' ? $('weatherSelect').value : $('drawingWeatherSelect').value,
      prompt:  currentTab === 'interior' ? $('interiorPrompt').value
             : currentTab === 'exterior' ? $('exteriorPrompt').value
             : $('drawingPrompt').value,
      drawing_mode: currentDrawingMode, drawing_type: currentDrawingType,
      drawing_output: currentDrawingOutput,
    };
    appliedEdits = [];
    $('rebaseRenderBtn').classList.add('hidden');
    if ($('ppRebaseBtn')) $('ppRebaseBtn').disabled = true;

    const fd = new FormData();
    fd.append('mode',       currentTab);
    fd.append('image',      imgFile);
    fd.append('model',      $('modelSelect').value);
    fd.append('resolution', $('resolutionSelect').value);
    fd.append('seed',       $('seedInput').value.trim());
    fd.append('lighting',   $('lightingSelect').value);
    fd.append('vegetation', $('vegetationSelect').value);
    if (files.referenceImage) fd.append('reference_image', files.referenceImage);

    if (currentTab === 'interior') {
      fd.append('input_type', currentInputType);
      fd.append('style',      $('styleSelect').value);
      fd.append('prompt',     $('interiorPrompt').value);

    } else if (currentTab === 'exterior') {
      fd.append('input_type', currentInputType);
      fd.append('context',    $('contextSelect').value);
      fd.append('weather',    $('weatherSelect').value);
      fd.append('prompt',     $('exteriorPrompt').value);

    } else {
      // drawing tab
      fd.append('drawing_mode',   currentDrawingMode);
      fd.append('drawing_type',   currentDrawingType);
      fd.append('drawing_output', currentDrawingOutput);
      fd.append('prompt',         $('drawingPrompt').value);
      if (currentDrawingOutput === 'exterior') {
        fd.append('context', $('drawingContextSelect').value);
        fd.append('weather', $('drawingWeatherSelect').value);
      } else {
        fd.append('style', $('drawingStyleSelect').value);
      }
    }

    const loadingText = currentTab === 'drawing'
      ? currentDrawingMode === '2d_render'
          ? 'AI đang làm đẹp bản vẽ 2D…'
          : currentDrawingOutput === 'exterior'
              ? 'AI đang tạo phối cảnh ngoại thất 3D từ mặt đứng…'
              : 'AI đang tạo phối cảnh nội thất 3D từ mặt bằng…'
      : 'Đang diễn họa…';

    setLoading(true, loadingText);
    $('renderBtn').disabled = true;
    try {
      const data = await API.render(fd);
      await showResult(data);
      toast('Xong! Seed: ' + data.seed);
    } catch (e) {
      toast(e.message, false);
    } finally {
      setLoading(false);
      $('renderBtn').disabled = false;
    }
  }

  // ══════════════════════════════════════════════
  //  Inpaint
  // ══════════════════════════════════════════════
  async function doInpaint() {
    if (!currentResult) { toast('Chưa có ảnh để sửa.', false); return; }
    if (!maskTool.hasMask()) { toast('Hãy vẽ mask lên vùng cần sửa trước.', false); return; }
    const instruction = $('inpaintInstruction').value.trim();
    if (!instruction) { toast('Hãy nhập chỉ thị sửa.', false); return; }

    const imgBlob  = await (await fetch(currentResult.url)).blob();
    const maskBlob = await maskTool.exportMaskBlob();

    const fd = new FormData();
    fd.append('image',       imgBlob,  'render.png');
    fd.append('mask',        maskBlob, 'mask.png');
    fd.append('instruction', instruction);
    fd.append('model',       $('modelSelect').value);
    fd.append('resolution',  $('resolutionSelect').value);
    fd.append('seed',        $('seedInput').value.trim());

    setLoading(true, 'Đang sửa cục bộ…');
    $('inpaintBtn').disabled = true;
    try {
      const data = await API.inpaint(fd);
      await showResult(data);
      toast('Đã sửa xong! Seed: ' + data.seed);
      // Ghi nhận chỉnh sửa để "Render lại từ gốc" (C2)
      if (originalSourceFile) {
        appliedEdits.push({ type: 'mask', instruction });
        $('rebaseRenderBtn').classList.remove('hidden');
        if ($('ppRebaseBtn')) $('ppRebaseBtn').disabled = false;
      }
    } catch (e) {
      toast(e.message, false);
    } finally {
      setLoading(false);
      $('inpaintBtn').disabled = false;
    }
  }

  // ══════════════════════════════════════════════
  //  Text-only edit (không cần vẽ mask)
  // ══════════════════════════════════════════════
  async function doTextEdit() {
    if (!currentResult) { toast('Hãy render ảnh trước.', false); return; }
    const instruction = $('textEditInstruction').value.trim();
    if (!instruction) { toast('Hãy nhập mô tả chỉnh sửa.', false); return; }

    const imgBlob = await (await fetch(currentResult.url)).blob();
    const fd = new FormData();
    fd.append('image',       imgBlob, 'render.png');
    // Không gửi mask → backend nhận mask=None → text_edit path
    fd.append('instruction', instruction);
    fd.append('model',       $('modelSelect').value);
    fd.append('resolution',  $('resolutionSelect').value);
    fd.append('seed',        $('seedInput').value.trim());

    _pendingEditInstruction = instruction;  // lưu để push vào appliedEdits khi Apply
    setLoading(true, '✏️ AI đang chỉnh sửa theo mô tả…');
    $('textEditBtn').disabled = true;
    try {
      const data = await API.inpaint(fd);
      pendingEditResult = data;

      // So sánh: trước = ảnh hiện tại, sau = ảnh vừa edit
      $('cmpLabelBefore').textContent = 'Trước chỉnh sửa';
      $('cmpLabelAfter').textContent  = 'Sau chỉnh sửa';
      $('cmpBefore').src = currentResult.url;
      $('cmpAfter').src  = data.image_url;
      $('cmpAfter').style.clipPath = 'inset(0 50% 0 0)';
      $('cmpDivider').style.left   = '50%';
      switchToView('viewCompare');

      // Hiện nút Áp dụng / Giữ nguyên
      $('editPreviewActions').classList.remove('hidden');
      $('editPreviewActions').classList.add('flex');
      toast('Xem kết quả tại tab "So sánh" — bấm Áp dụng để xác nhận.');
    } catch (e) {
      toast(e.message, false);
    } finally {
      setLoading(false);
      $('textEditBtn').disabled = false;
    }
  }

  function initEditPreviewActions() {
    $('applyEditBtn').addEventListener('click', async () => {
      if (!pendingEditResult) return;
      const data = pendingEditResult;
      pendingEditResult = null;

      // Cập nhật currentResult và canvas mask
      currentResult = {
        url:       data.image_url,
        seed:      data.seed,
        filename:  data.image_filename,
        beforeUrl: null,
      };
      updatePostProcessLock();
      $('maskCanvas').classList.remove('hidden');
      await maskTool.load(data.image_url);
      stopMaskMode();

      // Cập nhật các UI liên quan
      $('adjImg').src = data.image_url;
      resetAdj();
      $('seedBadge').classList.remove('hidden');
      $('seedBadge').classList.add('flex');
      $('seedValue').textContent = data.seed;
      $('inpaintBtn').disabled  = false;
      $('textEditBtn').disabled = false;

      // Ẩn nút Áp dụng / Giữ nguyên
      $('editPreviewActions').classList.add('hidden');
      $('editPreviewActions').classList.remove('flex');

      // Ghi nhận chỉnh sửa để "Render lại từ gốc" (C2)
      if (originalSourceFile && _pendingEditInstruction) {
        appliedEdits.push({ type: 'text', instruction: _pendingEditInstruction });
        $('rebaseRenderBtn').classList.remove('hidden');
        if ($('ppRebaseBtn')) $('ppRebaseBtn').disabled = false;
      }
      _pendingEditInstruction = null;

      addHistory(data);
      switchToView('viewResult');
      toast('Đã áp dụng! Seed: ' + data.seed);
    });

    $('discardEditBtn').addEventListener('click', () => {
      pendingEditResult = null;
      $('editPreviewActions').classList.add('hidden');
      $('editPreviewActions').classList.remove('flex');
      switchToView('viewResult');
      toast('Đã giữ nguyên ảnh gốc.');
    });
  }

  // ══════════════════════════════════════════════
  //  AI Enhance
  // ══════════════════════════════════════════════
  async function doEnhance() {
    if (!currentResult) { toast('Hãy render ảnh trước.', false); return; }
    const blob = await (await fetch(currentResult.url)).blob();
    const fd   = new FormData();
    fd.append('image',      blob, 'render.png');
    fd.append('model',      $('modelSelect').value);
    fd.append('resolution', $('resolutionSelect').value);

    setLoading(true, '✨ AI đang nâng cao chất lượng ảnh…');
    $('enhanceBtn').disabled = true;
    if ($('ppEnhanceBtn')) $('ppEnhanceBtn').disabled = true;
    try {
      const data    = await API.enhance(fd);
      pendingBeforeUrl = currentResult.url;
      await showResult(data);
      toast('Nâng cao xong! Bấm "So sánh" để xem sự khác biệt.');
    } catch (e) {
      toast(e.message, false);
    } finally {
      setLoading(false);
      $('enhanceBtn').disabled = false;
      if ($('ppEnhanceBtn')) $('ppEnhanceBtn').disabled = false;
    }
  }

  // ══════════════════════════════════════════════
  //  Render lại từ gốc — gộp toàn bộ chỉnh sửa (C2)
  // ══════════════════════════════════════════════
  async function doRebaseRender() {
    if (!originalSourceFile || !originalRenderParams) {
      toast('Không có dữ liệu render gốc. Hãy render mới trước.', false);
      return;
    }
    const p = originalRenderParams;
    const editLines = appliedEdits
      .map((e, i) => `${i + 1}. [${e.type === 'mask' ? 'mask' : 'văn bản'}] ${e.instruction}`)
      .join('\n');
    const combinedPrompt = (p.prompt ? p.prompt + '\n\n' : '') +
      `Các chỉnh sửa cần tích hợp (${appliedEdits.length} thay đổi):\n${editLines}`;

    pendingBeforeUrl = URL.createObjectURL(originalSourceFile);

    const fd = new FormData();
    fd.append('mode',        p.mode);
    fd.append('image',       originalSourceFile);
    fd.append('model',       $('modelSelect').value);
    fd.append('resolution',  $('resolutionSelect').value);
    fd.append('seed',        '');
    fd.append('lighting',    p.lighting);
    fd.append('vegetation',  p.vegetation);
    fd.append('input_type',  p.input_type || 'wireframe');
    if (originalRefFile) fd.append('reference_image', originalRefFile);

    if (p.mode === 'interior') {
      fd.append('style',  p.style  || '');
      fd.append('prompt', combinedPrompt);
    } else if (p.mode === 'exterior') {
      fd.append('context', p.context || '');
      fd.append('weather', p.weather || '');
      fd.append('prompt',  combinedPrompt);
    } else {
      fd.append('drawing_mode',   p.drawing_mode   || '3d_perspective');
      fd.append('drawing_type',   p.drawing_type   || 'autocad');
      fd.append('drawing_output', p.drawing_output || 'interior');
      fd.append('prompt', combinedPrompt);
      if (p.drawing_output === 'exterior') {
        fd.append('context', p.context || '');
        fd.append('weather', p.weather || '');
      } else {
        fd.append('style', p.style || '');
      }
    }

    setLoading(true, `🔄 Render lại từ ảnh SketchUp gốc với ${appliedEdits.length} chỉnh sửa đã gộp — tránh lệch hình học tích lũy…`);
    $('rebaseRenderBtn').disabled = true;
    try {
      const data = await API.render(fd);
      appliedEdits = [];
      $('rebaseRenderBtn').classList.add('hidden');
      if ($('ppRebaseBtn')) $('ppRebaseBtn').disabled = true;
      await showResult(data);
      toast(`Render lại xong từ ảnh gốc! Seed: ${data.seed}`);
    } catch (e) {
      toast(e.message, false);
    } finally {
      setLoading(false);
      $('rebaseRenderBtn').disabled = false;
    }
  }

  // ══════════════════════════════════════════════
  //  Gợi ý màu AI (C3)
  // ══════════════════════════════════════════════
  async function doAnalyzeMood() {
    if (!currentResult) { toast('Hãy render ảnh trước.', false); return; }
    switchToView('viewAdjust');

    const blob = await (await fetch(currentResult.url)).blob();
    const fd   = new FormData();
    fd.append('image', blob, 'render.png');
    fd.append('mood',  $('moodSelect').value);
    fd.append('model', $('modelSelect').value);

    $('analyzeMoodBtn').disabled = true;
    const origHTML = $('analyzeMoodBtn').innerHTML;
    $('analyzeMoodBtn').textContent = '⏳ Đang phân tích…';
    try {
      const data = await API.analyzeMood(fd);
      $('adjBrightness').value = data.brightness;
      $('adjContrast').value   = data.contrast;
      $('adjSaturate').value   = data.saturate;
      $('adjWarmth').value     = data.warmth;
      document.querySelectorAll('.color-preset-btn').forEach((b) => b.classList.remove('active'));
      updateAdj();
      toast('🎨 Đã áp dụng gợi ý màu AI.');
    } catch (e) {
      toast(e.message, false);
    } finally {
      $('analyzeMoodBtn').disabled = false;
      $('analyzeMoodBtn').innerHTML = origHTML;
    }
  }

  // ══════════════════════════════════════════════
  //  License
  // ══════════════════════════════════════════════
  async function checkLicense() {
    try {
      const s = await API.getLicense();
      const banner = $('trialBanner');
      const modal  = $('licenseModal');
      const midEl  = $('machineIdDisplay');

      if (midEl) midEl.textContent = s.machine_id || '----';

      if (s.mode === 'licensed') {
        // Không cần hiện gì — ẩn hết
        if (banner) banner.classList.add('hidden');
        if (modal)  modal.classList.add('hidden');

      } else if (s.mode === 'trial') {
        // Hiện banner nhỏ
        const msg = $('trialMsg');
        if (msg) msg.textContent = `⏳ Đang dùng thử — còn ${s.days_remaining} ngày. Liên hệ Zalo 0903230616 để kích hoạt bản quyền đầy đủ.`;
        if (banner) banner.classList.remove('hidden');
        if (modal)  modal.classList.add('hidden');

      } else {
        // expired — hiện modal chặn, ẩn banner
        if (banner) banner.classList.add('hidden');
        const msgEl = $('licenseModalMsg');
        if (msgEl) msgEl.textContent = s.message || 'Hết hạn dùng thử.';
        if (modal)  modal.classList.remove('hidden');
        // Nút "Đóng" không hiện khi hết hạn — chỉ hiện khi mở từ trial banner
        const closeBtn = $('licenseModalClose');
        if (closeBtn) closeBtn.classList.add('hidden');
      }
    } catch (_) { /* Không block app nếu kiểm tra license lỗi */ }
  }

  function initLicense() {
    // Banner: bấm "Kích hoạt" → mở modal (có nút Đóng vì vẫn còn trial)
    $('trialActivateBtn')?.addEventListener('click', () => {
      $('licenseModalClose')?.classList.remove('hidden');
      $('licenseModal')?.classList.remove('hidden');
    });

    // Banner: bấm × → ẩn banner
    $('trialDismissBtn')?.addEventListener('click', () => {
      $('trialBanner')?.classList.add('hidden');
    });

    // Modal: bấm Đóng (chỉ khi còn trial)
    $('licenseModalClose')?.addEventListener('click', () => {
      $('licenseModal')?.classList.add('hidden');
    });

    // Modal: kích hoạt key
    $('activateLicenseBtn')?.addEventListener('click', async () => {
      const key = $('licenseKeyInput')?.value.trim();
      const errEl = $('activateError');
      if (!key) { if (errEl) { errEl.textContent = 'Hãy nhập license key.'; errEl.classList.remove('hidden'); } return; }

      const btn = $('activateLicenseBtn');
      btn.disabled = true;
      btn.textContent = '⏳ Đang xác thực…';
      if (errEl) errEl.classList.add('hidden');

      try {
        const res = await API.activateLicense(key);
        toast(res.message || 'Kích hoạt thành công!');
        $('licenseModal')?.classList.add('hidden');
        $('trialBanner')?.classList.add('hidden');
      } catch (e) {
        if (errEl) { errEl.textContent = e.message; errEl.classList.remove('hidden'); }
      } finally {
        btn.disabled = false;
        btn.textContent = '✅ Kích hoạt';
      }
    });

    // Cho phép Enter trong ô input
    $('licenseKeyInput')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') $('activateLicenseBtn')?.click();
    });
  }

  // ══════════════════════════════════════════════
  //  Khóa / mở khóa khối hậu kỳ + lịch sử
  // ══════════════════════════════════════════════
  function updatePostProcessLock() {
    const locked = currentResult === null;
    $('postProcessCard').classList.toggle('section-disabled', locked);
    $('historyCard').classList.toggle('section-disabled', locked);
    $('postProcessLockNote').classList.toggle('hidden', !locked);
  }

  // ══════════════════════════════════════════════
  //  Wire up all events
  // ══════════════════════════════════════════════
  function initActions() {
    $('renderBtn').addEventListener('click', doRender);
    $('inpaintBtn').addEventListener('click', doInpaint);
    $('textEditBtn').addEventListener('click', doTextEdit);
    $('enhanceBtn').addEventListener('click', doEnhance);
    $('rebaseRenderBtn').addEventListener('click', doRebaseRender);
    $('analyzeMoodBtn').addEventListener('click', doAnalyzeMood);
    $('saveKeysBtn').addEventListener('click', saveKeys);

    $('downloadBtn').addEventListener('click', async () => {
      if (!currentResult) return;
      try {
        const blob = await (await fetch(currentResult.url)).blob();
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement('a');
        a.href     = url;
        a.download = currentResult.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(url), 200);
      } catch (_) {
        toast('Không tải được ảnh gốc.', false);
      }
    });

    $('styleSelect').addEventListener('change', applyStylePlaceholder);
    $('contextSelect').addEventListener('change', applyContextPlaceholder);
    // Tech summary cập nhật khi đổi lighting / model / resolution
    ['lightingSelect', 'modelSelect', 'resolutionSelect'].forEach((id) => {
      $(id).addEventListener('change', updateTechSummary);
    });

    $('brushSize').addEventListener('input', (e) => {
      maskTool.setBrush(e.target.value);
      $('brushSizeVal').textContent = e.target.value;
    });

    $('drawMaskBtn').addEventListener('click', () => {
      if (maskTool.drawing && !maskTool.erasing) { stopMaskMode(); return; }
      setMaskMode('draw');
    });
    $('eraseMaskBtn').addEventListener('click', () => {
      if (maskTool.drawing && maskTool.erasing) { stopMaskMode(); return; }
      if (!maskTool.hasMask()) { toast('Hãy dùng ➕ Thêm vùng chọn để tô vùng cần sửa trước, rồi dùng ➖ Bớt để xóa bớt.', false); return; }
      setMaskMode('erase');
    });
    $('undoMaskBtn').addEventListener('click', () => {
      if (maskTool.undoStack.length === 0) { toast('Không có gì để hoàn tác.', false); return; }
      maskTool.undo();
      toast('Đã hoàn tác 1 nét.');
    });
    $('clearMaskBtn').addEventListener('click', () => { maskTool.clear(); toast('Đã xóa toàn bộ mask.'); });

    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && maskTool.drawing) {
        e.preventDefault();
        maskTool.undo();
      }
    });

    $('copySeed').addEventListener('click', () => {
      navigator.clipboard.writeText(currentResult.seed);
      toast('Đã copy Seed: ' + currentResult.seed);
    });

    $('useAsRefBtn').addEventListener('click', async () => {
      const blob = await (await fetch(currentResult.url)).blob();
      const file = new File([blob], currentResult.filename, { type: 'image/png' });
      files.referenceImage = file;
      const dz  = document.querySelector('.dropzone[data-target="referenceImage"]');
      const img = dz.querySelector('.preview');
      img.src = URL.createObjectURL(blob);
      img.classList.remove('hidden');
      dz.querySelector('.ph').classList.add('hidden');
      toast('Đã đặt ảnh này làm Reference cho góc tiếp theo.');
    });

    // ── Tầng 3: Quick actions ──
    $('ppAdjBtn').addEventListener('click', () => {
      if (!currentResult) { toast('Hãy render ảnh trước.', false); return; }
      const panel = $('ppAdjPanel');
      panel.classList.toggle('hidden');
      $('ppAdjBtn').classList.toggle('active', !panel.classList.contains('hidden'));
    });
    $('ppEnhanceBtn').addEventListener('click', doEnhance);
    $('ppRebaseBtn').addEventListener('click', doRebaseRender);

    // Mini sliders → sync về main sliders (state luôn ở main)
    [['ppBr','adjBrightness'],['ppCo','adjContrast'],
     ['ppSa','adjSaturate'], ['ppWa','adjWarmth']].forEach(([pp, main]) => {
      $(pp).addEventListener('input', (e) => {
        $(main).value = e.target.value;
        document.querySelectorAll('.color-preset-btn').forEach((b) => b.classList.remove('active'));
        updateAdj();
      });
    });
  }

  // ══════════════════════════════════════════════
  //  Khởi động
  // ══════════════════════════════════════════════
  window.addEventListener('DOMContentLoaded', () => {
    maskTool = new MaskTool($('maskCanvas'));
    initTabs();
    initViewTabs();
    initInputType();
    initDrawingTab();
    initDropzones();
    initCompareSlider();
    initColorPresets();
    initExportFormat();
    initAdjust();
    initInpaintModeToggle();
    initEditPreviewActions();
    initActions();
    updateTabDots();
    updatePostProcessLock();
    initLicense();
    checkLicense();
    loadPresets();
  });
})();
