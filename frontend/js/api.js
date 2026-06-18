// Lớp gọi API tới backend FastAPI.
const API = {
  async getPresets() {
    const r = await fetch('/api/presets');
    if (!r.ok) throw new Error('Không tải được preset.');
    return r.json();
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
};
