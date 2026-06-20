// Công cụ vẽ mask cho tính năng Inpaint.
// Hỗ trợ: vẽ magenta, tẩy, undo (tối đa 20 bước), xuất PNG độ phân giải gốc.
class MaskTool {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.baseImage = null;
    this.natW = 0;
    this.natH = 0;
    this.drawing = false;
    this.painting = false;
    this.erasing = false;
    this.brush = 30;
    this.dirty = false;
    this.undoStack = [];           // mảng ImageData, tối đa 20

    this.maskCanvas = document.createElement('canvas');
    this.maskCtx = this.maskCanvas.getContext('2d');

    this._bind();
  }

  setBrush(size) { this.brush = +size; }

  enable(on) {
    this.drawing = on;
    this.canvas.classList.toggle('drawing', on && !this.erasing);
    this.canvas.classList.toggle('erasing', on && this.erasing);
  }

  setMode(mode) {   // 'draw' | 'erase'
    this.erasing = mode === 'erase';
    if (this.drawing) {
      this.canvas.classList.toggle('drawing', !this.erasing);
      this.canvas.classList.toggle('erasing', this.erasing);
    }
  }

  hasMask() { return this.dirty; }

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
        this.undoStack = [];
        this._fitCanvas();
        this._redraw();
        resolve();
      };
      img.src = url;
    });
  }

  clear() {
    if (!this.baseImage) return;
    this._saveUndo();
    this.maskCtx.clearRect(0, 0, this.natW, this.natH);
    this.dirty = false;
    this._redraw();
  }

  undo() {
    if (this.undoStack.length === 0) return;
    const state = this.undoStack.pop();
    this.maskCtx.putImageData(state, 0, 0);
    const data = this.maskCtx.getImageData(0, 0, this.natW, this.natH).data;
    this.dirty = data.some((v) => v > 0);
    this._redraw();
  }

  _saveUndo() {
    if (!this.baseImage) return;
    if (this.undoStack.length >= 20) this.undoStack.shift();
    this.undoStack.push(
      this.maskCtx.getImageData(0, 0, this.natW, this.natH)
    );
  }

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
    this.ctx.globalAlpha = 0.68;
    this.ctx.drawImage(this.maskCanvas, 0, 0);
    this.ctx.globalAlpha = 1;
  }

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

    if (this.erasing) {
      this.maskCtx.globalCompositeOperation = 'destination-out';
      this.maskCtx.fillStyle = 'rgba(0,0,0,1)';
    } else {
      this.maskCtx.globalCompositeOperation = 'source-over';
      this.maskCtx.fillStyle = '#ff00ff';
      this.dirty = true;
    }

    this.maskCtx.beginPath();
    this.maskCtx.arc(x, y, r, 0, Math.PI * 2);
    this.maskCtx.fill();
    this.maskCtx.globalCompositeOperation = 'source-over';
    this._redraw();
  }

  _bind() {
    const start = (e) => {
      if (!this.drawing || !this.baseImage) return;
      this._saveUndo();
      this.painting = true;
      this._paint(e);
      e.preventDefault();
    };
    // mousemove trên document để nét không bị đứt khi kéo nhanh ra ngoài canvas
    const move = (e) => { if (this.painting) { this._paint(e); } };
    const end  = () => { this.painting = false; };

    this.canvas.addEventListener('mousedown', start);
    document.addEventListener('mousemove', move);
    document.addEventListener('mouseup', end);
    this.canvas.addEventListener('touchstart', start, { passive: false });
    this.canvas.addEventListener('touchmove', move, { passive: false });
    document.addEventListener('touchend', end);
  }

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
