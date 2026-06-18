# HungArch AI Render

Ứng dụng web chạy local biến **ảnh chụp khối thô SketchUp** thành **ảnh diễn họa chân thực (photorealistic)**, giữ nguyên hình học / góc camera / bố cục. Dùng Google Gemini Image làm "bộ não AI".

## Tính năng

- **2 tab làm việc:**
  - 🛋️ **Nội thất** — phong cách: Hiện đại, Tối giản, Japandi, Tân cổ điển, Thiền/Á Đông, Nhiệt đới + ô mô tả vật liệu & ánh sáng.
  - 🏙️ **Ngoại thất** — bối cảnh VN (Phố cổ Hà Nội, Shophouse, Nhà ống, Làng quê Bắc Bộ, Đồi núi sương mù, Miệt vườn) + thời tiết (Nắng gắt, U ám sau mưa, Giờ xanh).
- **2 Engine AI lựa chọn:**
  - **Gemini** — nhanh, dễ dùng, hỗ trợ Reference Image để đồng nhất.
  - **Replicate** (FLUX + ControlNet depth) — **seed thật** (tái lập 100%) + giữ hình học chính xác hơn; inpaint bằng mask thật (flux-fill). Trả phí theo ảnh.
- **Đồng bộ Style** — tải ảnh render ưng ý làm reference để "hút" tone màu & vật liệu.
- **Khóa Seed / mã ảnh** — mỗi ảnh có mã Seed copy được để truy vết (Replicate: seed số nguyên tái lập được).
- **Hậu kỳ (Inpaint)** — bôi mask lên ảnh kết quả rồi sửa cục bộ bằng text.
- **Output** — ảnh độ phân giải cao (1K/2K/4K), tải về, lịch sử phiên.

## Yêu cầu

- **Python 3.10+** đã cài (tích "Add Python to PATH" khi cài đặt).
- **Gemini API key** (miễn phí): https://aistudio.google.com/apikey
- (Tùy chọn) **Replicate API token** nếu muốn dùng engine Replicate: https://replicate.com/account/api-tokens — điền `REPLICATE_API_TOKEN=...` vào `.env`.

## Cài đặt & chạy (Windows)

1. Lấy API key ở link trên.
2. Mở thư mục dự án, copy `.env.example` thành `.env`, điền:
   ```
   GEMINI_API_KEY=khoa_cua_ban
   ```
   (Nếu quên, `run.bat` sẽ tự tạo `.env` cho bạn — chỉ cần điền key rồi chạy lại.)
3. Bấm đúp **`run.bat`**. Lần đầu sẽ tự cài thư viện (mất vài phút).
4. Trình duyệt tự mở `http://localhost:8000`.

## Cách dùng nhanh

1. Chọn tab Nội thất / Ngoại thất → tải ảnh SketchUp.
2. Chọn phong cách / bối cảnh, nhập mô tả → **TẠO RENDER**.
3. Muốn các góc đồng nhất: bấm **Dùng làm Reference** rồi render góc tiếp theo.
4. Sửa cục bộ: bấm **Bật/tắt vẽ mask**, bôi vùng cần sửa, nhập chỉ thị → **SỬA VÙNG ĐÃ CHỌN**.
5. Bấm **Tải về** và copy **Seed** nếu cần lưu.

## Lưu ý kỹ thuật

- **Giữ hình học:** với **Gemini** dùng prompt khóa cứng (rất tốt nhưng không tuyệt đối 100%); với **Replicate** dùng ControlNet depth nên giữ khối chính xác hơn.
- **Seed:** Gemini không có seed tái lập y hệt → dùng cùng Reference Image + phong cách để đồng nhất. **Replicate có seed thật** (số nguyên) — nhập cùng một số Seed sẽ ra kết quả ổn định.
- Ảnh kết quả lưu trong thư mục `outputs/` (kèm file `.json` ghi prompt/metadata).

## Cấu trúc

```
backend/   FastAPI (config, prompts, store, gemini_client, replicate_client, main)
frontend/  HTML + CSS + JS thuần (index.html, css/, js/)
outputs/   Ảnh đã render + metadata
run.bat    Chạy 1 chạm
```

## Đưa code lên GitHub

Repo git đã được khởi tạo & commit sẵn (đã loại trừ `.env`, `.venv`, `outputs/`). Để đẩy lên tài khoản của bạn (đã cài sẵn `gh`):

```bash
gh auth login                 # đăng nhập GitHub (1 lần, qua trình duyệt)
gh repo create hungarch-ai-render --source=. --private --push
```

## Mở rộng tương lai

- Render hàng loạt nhiều góc, xuất thẳng vào SketchUp.
- Engine ComfyUI local (tận dụng GPU NVIDIA) — chạy miễn phí không giới hạn ảnh.
