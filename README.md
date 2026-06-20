# HungArch AI Render

Ứng dụng web chạy local biến **ảnh chụp khối thô SketchUp** thành **ảnh diễn họa chân thực (photorealistic)**, giữ nguyên hình học / góc camera / bố cục. Dùng Google Gemini Image làm "bộ não AI".

## Tính năng

- **3 tab làm việc:**
  - 🛋️ **Nội thất** — phong cách: Hiện đại, Tối giản, Japandi, Tân cổ điển, Thiền/Á Đông, Nhiệt đới, Văn phòng, Nhà hàng, Resort...
  - 🏙️ **Ngoại thất** — bối cảnh VN (Phố cổ Hà Nội, Shophouse, Nhà ống, Làng quê Bắc Bộ, Đồi núi sương mù, Resort biển...) + thời tiết (Nắng gắt, U ám sau mưa, Giờ xanh).
  - ✏️ **Bản vẽ 2D** — chuyển mặt bằng AutoCAD / phác thảo tay → phối cảnh nội thất hoặc ngoại thất 3D; hoặc làm đẹp bản vẽ 2D.
- **Đồng bộ Style** — tải ảnh render ưng ý làm reference để "hút" tone màu & vật liệu.
- **Hậu kỳ (Inpaint):**
  - ✍️ **Vẽ mask** — bôi vùng cần sửa bằng cọ, nhập mô tả, AI sửa đúng vùng đó.
  - 📝 **Mô tả văn bản** — chỉnh sửa không cần vẽ (VD: "thay sàn gỗ phòng khách bằng đá granite").
  - So sánh trước/sau trước khi áp dụng.
- **🔄 Render lại từ gốc** — sau nhiều lần sửa, gộp toàn bộ chỉnh sửa và render lại từ ảnh SketchUp gốc để tránh lệch hình học tích lũy.
- **✨ AI Nâng cao** — tăng độ sắc nét texture, PBR, ánh sáng không cần render lại.
- **🎨 Gợi ý màu AI** — phân tích ảnh và đề xuất thông số colour-grading theo mood (Ấm áp sang trọng, Lạnh tối giản...).
- **Điều chỉnh màu thủ công** — brightness, contrast, saturation, warmth + preset (Film, Cinematic, B&W...).
- **Seed / mã ảnh** — mỗi ảnh có mã ID = tên file thật trong `outputs/`, copy được để truy vết.

## Yêu cầu

- **Python 3.10+** đã cài (tích "Add Python to PATH" khi cài đặt).
- **Gemini API key** (cần bật billing — Gemini Image không có free tier): https://aistudio.google.com/apikey

## Cài đặt & chạy (Windows)

1. Lấy API key ở link trên, bật billing tại console.cloud.google.com.
2. Mở thư mục dự án, copy `.env.example` thành `.env`, điền:
   ```
   GEMINI_API_KEY=khoa_cua_ban
   ```
   (Nếu quên, có thể nhập key trực tiếp trong app — mục "🔑 Cấu hình khóa API".)
3. Bấm đúp **`run.bat`**. Lần đầu sẽ tự cài thư viện (mất vài phút).
4. Trình duyệt tự mở `http://localhost:8000`.

## Cách dùng nhanh

1. Chọn tab Nội thất / Ngoại thất / Bản vẽ 2D → tải ảnh SketchUp.
2. Chọn phong cách / bối cảnh, nhập mô tả → **TẠO RENDER**.
3. Muốn các góc đồng nhất: bấm **Dùng làm Reference** rồi render góc tiếp theo.
4. Sửa cục bộ: chọn chế độ **Vẽ mask** hoặc **Mô tả văn bản** → sửa → so sánh trước/sau → Áp dụng.
5. Bấm **Tải về** và ghi nhớ **Seed** (= tên file trong `outputs/`) nếu cần truy vết.

## Lưu ý kỹ thuật

- **Giữ hình học:** prompt khóa cứng (GEOMETRY_LOCK) bảo Gemini giữ nguyên bố cục SketchUp — tốt nhưng không tuyệt đối 100%.
- **Seed:** Gemini không có seed tái lập y hệt → dùng cùng Reference Image + phong cách để giữ đồng nhất giữa các góc render. Mã Seed trong app = tên file thật trong `outputs/` để truy vết.
- **Tránh lệch hình học:** sau nhiều lần inpaint liên tiếp, dùng "🔄 Render lại từ gốc" để gộp và render sạch từ ảnh SketchUp ban đầu.
- Ảnh kết quả lưu trong `outputs/` (kèm file `.json` ghi prompt/metadata).

## Cấu trúc

```
backend/   FastAPI (config, prompts, store, gemini_client, main)
frontend/  HTML + CSS + JS thuần (index.html, css/, js/)
outputs/   Ảnh đã render + metadata
run.bat    Chạy 1 chạm
```

## Đưa code lên GitHub

```bash
gh auth login
gh repo create hungarch-ai-render --source=. --private --push
```

## Mở rộng tương lai

- Render hàng loạt nhiều góc, xuất thẳng vào SketchUp.
- Engine ComfyUI local (tận dụng GPU NVIDIA) — chạy miễn phí không giới hạn ảnh.
