// Công cụ vẽ mask trên canvas cho tính năng Inpaint.
// Người dùng bôi magenta lên vùng cần sửa; mask được xuất ở độ phân giải gốc.
class MaskTool {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.baseImage = null;     // <img> ảnh kết quả hiện tại
    this.natW = 0;
    this.natH = 0;
    this.drawing = false;      // chế độ vẽ bật/tắt
    this.painting = false;     // đang nhấn chuột/chạm
    this.brush = 30;
    this.dirty = false;        // đã có nét nào chưa

    // Canvas ẩn lưu mask ở độ phân giải gốc (đen = giữ, magenta = sửa).
    this.maskCanvas = document.createElement('canvas');
    this.maskCtx = this.maskCanvas.getContext('2d');

    this._bind();
  }

  setBrush(size) { this.brush = +size; }
  enable(on) {
    this.drawing = on;
    this.canvas.classList.toggle('drawing', on);
  }
  hasMask() { return this.dirty; }

  // Nạp ảnh kết quả mới -> reset mask.
  load(url) {
    return new Promise((resolve) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => {
        this.baseImage = img;
        this.natW = img.naturalWidth;
        this.natH = img.naturalHeight;
        this.maskCanvas.width = this.natW;
        this.maskCanvas.height = this.natH;
        this.maskCtx.clearRect(0, 0, this.natW, this.natH);
        this.dirty = false;
        this._fitCanvas();
        this._redraw();
        resolve();
      };
      img.src = url;
    });
  }

  clear() {
    if (!this.baseImage) return;
    this.maskCtx.clearRect(0, 0, this.natW, this.natH);
    this.dirty = false;
    this._redraw();
  }

  // Đặt kích thước hiển thị canvas vừa khung, giữ tỉ lệ.
  _fitCanvas() {
    const maxW = this.canvas.parentElement.clientWidth || 600;
    const maxH = Math.min(window.innerHeight * 0.6, 600);
    const ratio = this.natW / this.natH;
    let w = maxW, h = w / ratio;
    if (h > maxH) { h = maxH; w = h * ratio; }
    this.canvas.width = this.natW;
    this.canvas.height = this.natH;
    this.canvas.style.width = w + 'px';
    this.canvas.style.height = h + 'px';
  }

  _redraw() {
    if (!this.baseImage) return;
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    this.ctx.drawImage(this.baseImage, 0, 0, this.natW, this.natH);
    // Phủ mask bán trong suốt để người dùng thấy vùng đã bôi.
    this.ctx.globalAlpha = 0.5;
    this.ctx.drawImage(this.maskCanvas, 0, 0);
    this.ctx.globalAlpha = 1;
  }

  // Toạ độ chuột/chạm -> toạ độ pixel gốc.
  _pos(e) {
    const rect = this.canvas.getBoundingClientRect();
    const cx = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left;
    const cy = (e.touches ? e.touches[0].clientY : e.clientY) - rect.top;
    return {
      x: cx * (this.natW / rect.width),
      y: cy * (this.natH / rect.height),
    };
  }

  _paint(e) {
    const { x, y } = this._pos(e);
    const r = this.brush * (this.natW / this.canvas.getBoundingClientRect().width);
    this.maskCtx.fillStyle = '#ff00ff';
    this.maskCtx.beginPath();
    this.maskCtx.arc(x, y, r, 0, Math.PI * 2);
    this.maskCtx.fill();
    this.dirty = true;
    this._redraw();
  }

  _bind() {
    const start = (e) => { if (!this.drawing || !this.baseImage) return; this.painting = true; this._paint(e); e.preventDefault(); };
    const move = (e) => { if (this.painting) { this._paint(e); e.preventDefault(); } };
    const end = () => { this.painting = false; };

    this.canvas.addEventListener('mousedown', start);
    this.canvas.addEventListener('mousemove', move);
    window.addEventListener('mouseup', end);
    this.canvas.addEventListener('touchstart', start, { passive: false });
    this.canvas.addEventListener('touchmove', move, { passive: false });
    window.addEventListener('touchend', end);
  }

  // Xuất mask PNG ở độ phân giải gốc: nền đen, vùng sửa magenta.
  exportMaskBlob() {
    const out = document.createElement('canvas');
    out.width = this.natW;
    out.height = this.natH;
    const c = out.getContext('2d');
    c.fillStyle = '#000000';
    c.fillRect(0, 0, this.natW, this.natH);
    c.drawImage(this.maskCanvas, 0, 0);
    return new Promise((res) => out.toBlob(res, 'image/png'));
  }
}
