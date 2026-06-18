// HungArch AI Render — điều khiển chính của giao diện.
(() => {
  const $ = (id) => document.getElementById(id);
  const files = { interiorImage: null, exteriorImage: null, referenceImage: null };
  let currentTab = 'interior';
  let currentResult = null; // { url, seed, filename }
  let maskTool = null;
  const history = [];

  // ---------- Toast ----------
  function toast(msg, ok = true) {
    const t = $('toast');
    t.textContent = msg;
    t.className = 'fixed bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 rounded-lg text-sm shadow-lg z-50 ' +
      (ok ? 'bg-emerald-600 text-white' : 'bg-red-600 text-white');
    t.classList.remove('hidden');
    setTimeout(() => t.classList.add('hidden'), 3200);
  }

  // ---------- Dropzones ----------
  function initDropzones() {
    document.querySelectorAll('.dropzone').forEach((dz) => {
      const targetId = dz.dataset.target;
      const input = $(targetId);
      const img = dz.querySelector('.preview');
      const ph = dz.querySelector('.ph');

      const show = (file) => {
        files[targetId] = file;
        const url = URL.createObjectURL(file);
        img.src = url;
        img.classList.remove('hidden');
        ph.classList.add('hidden');
      };

      dz.addEventListener('click', () => input.click());
      input.addEventListener('change', (e) => { if (e.target.files[0]) show(e.target.files[0]); });
      dz.addEventListener('dragover', (e) => { e.preventDefault(); dz.classList.add('dragover'); });
      dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
      dz.addEventListener('drop', (e) => {
        e.preventDefault();
        dz.classList.remove('dragover');
        if (e.dataTransfer.files[0]) show(e.dataTransfer.files[0]);
      });
    });
  }

  // ---------- Tabs ----------
  function initTabs() {
    document.querySelectorAll('.tab-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        currentTab = btn.dataset.tab;
        document.querySelectorAll('.tab-btn').forEach((b) => b.classList.toggle('active', b === btn));
        $('tab-interior').classList.toggle('hidden', currentTab !== 'interior');
        $('tab-exterior').classList.toggle('hidden', currentTab !== 'exterior');
      });
    });
    document.querySelector('.tab-btn[data-tab="interior"]').classList.add('active');
  }

  // ---------- Presets ----------
  function fillSelect(sel, items) {
    sel.innerHTML = items.map((i) => `<option value="${i.key}">${i.label}</option>`).join('');
  }

  let engines = [];

  function updateEngineHint() {
    const key = $('engineSelect').value;
    const eng = engines.find((e) => e.key === key) || {};
    const hint = $('engineHint');
    if (key === 'replicate') {
      hint.textContent = 'Replicate: SEED là số nguyên & tái lập 100%. Giữ hình học bằng ControlNet depth. Trả phí theo ảnh, chậm hơn Gemini.';
    } else {
      hint.textContent = 'Gemini: nhanh, dùng Reference Image để đồng nhất. Seed chỉ là mã truy vết (không tái lập y hệt).';
    }
    if (eng.available === false) {
      hint.textContent += ' ⚠️ Chưa cấu hình API key cho engine này trong .env.';
    }
  }

  async function loadPresets() {
    try {
      const p = await API.getPresets();
      fillSelect($('styleSelect'), p.interior_styles);
      fillSelect($('contextSelect'), p.exterior_contexts);
      fillSelect($('weatherSelect'), p.exterior_weather);
      fillSelect($('modelSelect'), p.models);
      engines = p.engines || [];
      $('engineSelect').innerHTML = engines
        .map((e) => `<option value="${e.key}" ${e.key === p.default_engine ? 'selected' : ''}>${e.label}${e.available ? '' : ' (chưa cấu hình)'}</option>`).join('');
      updateEngineHint();
      $('resolutionSelect').innerHTML = p.resolutions
        .map((r) => `<option ${r === p.default_resolution ? 'selected' : ''}>${r}</option>`).join('');

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
    const parts = [];
    parts.push(s.api_key_configured ? 'Gemini ✓' : 'Gemini ✗');
    parts.push(s.replicate_configured ? 'Replicate ✓' : 'Replicate ✗');
    $('keySummary').textContent = '— ' + parts.join(' · ');
    // Mở sẵn panel nhập khóa nếu chưa có khóa nào.
    if (!s.api_key_configured && !s.replicate_configured) {
      $('keyPanel').open = true;
    }
  }

  async function saveKeys() {
    const gemini = $('geminiKey').value.trim();
    const replicate = $('replicateKey').value.trim();
    if (!gemini && !replicate) { toast('Hãy nhập ít nhất một khóa.', false); return; }
    const body = {};
    if (gemini) body.gemini_api_key = gemini;
    if (replicate) body.replicate_api_token = replicate;
    try {
      await API.setConfig(body);
      $('geminiKey').value = '';
      $('replicateKey').value = '';
      await loadPresets();           // làm mới trạng thái + engine khả dụng
      toast('Đã lưu khóa API.');
    } catch (e) {
      toast(e.message, false);
    }
  }

  // ---------- Loading ----------
  function setLoading(on, text) {
    $('loadingOverlay').classList.toggle('hidden', !on);
    if (text) $('loadingText').textContent = text;
  }

  // ---------- Hiển thị kết quả ----------
  async function showResult(data) {
    currentResult = { url: data.image_url, seed: data.seed, filename: data.image_filename };
    $('resultPlaceholder').classList.add('hidden');
    const canvas = $('maskCanvas');
    canvas.classList.remove('hidden');
    await maskTool.load(data.image_url);

    $('seedBadge').classList.remove('hidden');
    $('seedBadge').classList.add('flex');
    $('seedValue').textContent = data.seed;

    $('resultActions').classList.remove('hidden');
    const dl = $('downloadBtn');
    dl.href = data.image_url;
    dl.setAttribute('download', data.image_filename);

    $('inpaintBtn').disabled = false;
    addHistory(data);
  }

  function addHistory(data) {
    history.unshift(data);
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

  // ---------- Render ----------
  async function doRender() {
    const imgFile = currentTab === 'interior' ? files.interiorImage : files.exteriorImage;
    if (!imgFile) { toast('Hãy tải ảnh SketchUp trước.', false); return; }

    const fd = new FormData();
    fd.append('mode', currentTab);
    fd.append('image', imgFile);
    fd.append('engine', $('engineSelect').value);
    fd.append('model', $('modelSelect').value);
    fd.append('resolution', $('resolutionSelect').value);
    fd.append('seed', $('seedInput').value.trim());
    if (files.referenceImage) fd.append('reference_image', files.referenceImage);

    if (currentTab === 'interior') {
      fd.append('style', $('styleSelect').value);
      fd.append('prompt', $('interiorPrompt').value);
    } else {
      fd.append('context', $('contextSelect').value);
      fd.append('weather', $('weatherSelect').value);
      fd.append('prompt', $('exteriorPrompt').value);
    }

    setLoading(true, 'Đang diễn họa…');
    $('renderBtn').disabled = true;
    try {
      const data = await API.render(fd);
      await showResult(data);
      toast('Render xong! Seed: ' + data.seed);
    } catch (e) {
      toast(e.message, false);
    } finally {
      setLoading(false);
      $('renderBtn').disabled = false;
    }
  }

  // ---------- Inpaint ----------
  async function doInpaint() {
    if (!currentResult) { toast('Chưa có ảnh để sửa.', false); return; }
    if (!maskTool.hasMask()) { toast('Hãy bật "vẽ mask" và bôi vùng cần sửa.', false); return; }
    const instruction = $('inpaintInstruction').value.trim();
    if (!instruction) { toast('Hãy nhập chỉ thị sửa.', false); return; }

    const imgBlob = await (await fetch(currentResult.url)).blob();
    const maskBlob = await maskTool.exportMaskBlob();

    const fd = new FormData();
    fd.append('image', imgBlob, 'render.png');
    fd.append('mask', maskBlob, 'mask.png');
    fd.append('instruction', instruction);
    fd.append('engine', $('engineSelect').value);
    fd.append('model', $('modelSelect').value);
    fd.append('resolution', $('resolutionSelect').value);
    fd.append('seed', $('seedInput').value.trim());

    setLoading(true, 'Đang sửa cục bộ…');
    $('inpaintBtn').disabled = true;
    try {
      const data = await API.inpaint(fd);
      maskTool.enable(false);
      await showResult(data);
      toast('Đã sửa xong! Seed: ' + data.seed);
    } catch (e) {
      toast(e.message, false);
    } finally {
      setLoading(false);
      $('inpaintBtn').disabled = false;
    }
  }

  // ---------- Sự kiện khác ----------
  function initActions() {
    $('renderBtn').addEventListener('click', doRender);
    $('inpaintBtn').addEventListener('click', doInpaint);
    $('engineSelect').addEventListener('change', updateEngineHint);
    $('saveKeysBtn').addEventListener('click', saveKeys);
    $('brushSize').addEventListener('input', (e) => maskTool.setBrush(e.target.value));
    $('clearMaskBtn').addEventListener('click', () => maskTool.clear());

    $('toggleMaskBtn').addEventListener('click', () => {
      const on = !maskTool.drawing;
      maskTool.enable(on);
      toast(on ? 'Đã bật chế độ vẽ mask — bôi lên vùng cần sửa.' : 'Đã tắt vẽ mask.');
    });

    $('copySeed').addEventListener('click', () => {
      navigator.clipboard.writeText(currentResult.seed);
      toast('Đã copy Seed: ' + currentResult.seed);
    });

    $('useAsRefBtn').addEventListener('click', async () => {
      const blob = await (await fetch(currentResult.url)).blob();
      const file = new File([blob], currentResult.filename, { type: 'image/png' });
      files.referenceImage = file;
      const dz = document.querySelector('.dropzone[data-target="referenceImage"]');
      const img = dz.querySelector('.preview');
      img.src = URL.createObjectURL(blob);
      img.classList.remove('hidden');
      dz.querySelector('.ph').classList.add('hidden');
      toast('Đã đặt ảnh này làm Reference cho góc tiếp theo.');
    });
  }

  // ---------- Khởi động ----------
  window.addEventListener('DOMContentLoaded', () => {
    maskTool = new MaskTool($('maskCanvas'));
    initTabs();
    initDropzones();
    initActions();
    loadPresets();
  });
})();
