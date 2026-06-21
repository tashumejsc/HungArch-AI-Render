// Lớp gọi API tới backend FastAPI.
const API = {
  async getPresets() {
    const r = await fetch('/api/presets');
    if (!r.ok) throw new Error('Không tải được preset.');
    return r.json();
  },

  async setConfig(body) {
    const r = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || 'Không lưu được khóa.');
    return data;
  },

  async render(formData) {
    const r = await fetch('/api/render', { method: 'POST', body: formData });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || 'Lỗi khi render.');
    return data;
  },

  async inpaint(formData) {
    const r = await fetch('/api/inpaint', { method: 'POST', body: formData });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || 'Lỗi khi sửa cục bộ.');
    return data;
  },

  async enhance(formData) {
    const r = await fetch('/api/enhance', { method: 'POST', body: formData });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || 'Lỗi khi nâng cao ảnh.');
    return data;
  },

  async analyzeMood(formData) {
    const r = await fetch('/api/analyze-mood', { method: 'POST', body: formData });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || 'Lỗi khi phân tích mood màu.');
    return data;
  },

  async getLicense() {
    const r = await fetch('/api/license');
    if (!r.ok) throw new Error('Không kiểm tra được license.');
    return r.json();
  },

  async activateLicense(key) {
    const r = await fetch('/api/license/activate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key }),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || 'Kích hoạt thất bại.');
    return data;
  },
};
