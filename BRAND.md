# Chuẩn nhận diện thương hiệu — Vật Liệu Nội Thất

Nguồn: logo hiện có của vatlieunoithat.vn (`static/brand/logo.webp`, 775×170, nền trong suốt). Màu dưới đây được đo trực tiếp từ logo, không tự đặt.

## 1. Logo
Logo chữ ngang: **VATLIEU** (xanh, chữ đậm) + **NOITHAT** (vàng, chữ mảnh), chữ V có nét vàng ở góc trái trên.

| File | Dùng cho |
|---|---|
| `static/brand/logo.webp` / `logo.png` | Header, chân trang, email, báo giá |
| `static/brand/icon-512.png` | Biểu tượng vuông (chữ V), avatar mạng xã hội, Zoho |
| `static/brand/apple-touch-icon.png` | Biểu tượng khi lưu trang lên màn hình điện thoại |
| `static/brand/favicon.ico`, `favicon.png` | Biểu tượng tab trình duyệt |

**Quy tắc dùng**
- Chiều cao tối thiểu: 28px trên màn hình, 12mm khi in. Chiều rộng không vượt 200px ở header.
- Vùng an toàn: chừa quanh logo ít nhất bằng chiều cao chữ V.
- Đặt trên nền trắng hoặc kem `#faf8f4`. Trên nền tối/ảnh dùng khung nền trắng bo góc phía sau logo; không đổi màu logo.
- Không kéo giãn, xoay, thêm bóng, hay đổi vị trí hai nửa chữ.

## 2. Màu sắc
| Vai trò | Tên | Mã | Dùng cho |
|---|---|---|---|
| Chính | Xanh rừng | `#276657` | Nút chính, liên kết, tiêu đề nhấn, hero |
| Chính đậm | Xanh đậm | `#1b4a3e` | Hover, trạng thái nhấn |
| Chính nhạt | Xanh nhạt | `#e6f0ec` | Nền thanh danh mục, nhãn |
| Nhấn | Vàng | `#d5a915` | Viền header, gạch chân tiêu đề, huy hiệu, nút phụ |
| Nhấn đậm | Vàng đậm | `#b88f0c` | Hover của nút vàng |
| Nền | Kem | `#faf8f4` | Nền trang |
| Nền phụ | Be | `#f1ede6` | Khối nhóm nội dung |
| Chữ | Than | `#2b2a27` | Nội dung |
| Chữ phụ | Xám ấm | `#6c675e` | Chú thích |
| Viền | Be đậm | `#e3ddd2` | Đường kẻ |
| Thành công / Lỗi | `#2f6b3f` / `#b3261e` | Thông báo |

**Độ tương phản (WCAG AA)**: chữ trắng trên xanh `#276657` đạt khoảng 7:1; chữ than trên vàng `#d5a915` đạt khoảng 8:1. **Không dùng chữ vàng trên nền trắng/kem** (chỉ khoảng 2,2:1, không đọc được); vàng chỉ làm nền, viền hay gạch chân.

Tỷ lệ gợi ý: 60% nền kem/trắng, 30% xanh, 10% vàng.

## 3. Chữ
- Phông: **Be Vietnam Pro** (hỗ trợ tiếng Việt đầy đủ), dự phòng `system-ui`.
- Nội dung 16px / dòng 1,6; tiêu đề đậm 600–700; không viết hoa toàn bộ trừ nhãn ngắn.

## 4. Thành phần giao diện
- Bo góc 10px; bóng nhẹ chỉ ở thẻ khi hover.
- Nút chính: nền xanh, chữ trắng. Nút phụ: viền than. Nút nhấn mạnh (ví dụ "Yêu cầu báo giá" ở vị trí nổi): `btn--gold`.
- Header có viền dưới vàng 3px; tiêu đề mỗi khối có gạch vàng ngắn.
- Ảnh sản phẩm tỷ lệ 4:3, nền be khi chưa có ảnh.

## 5. Giọng văn
Rõ ràng, thực tế, không phóng đại. Gọi khách là "Quý khách" hoặc "bạn"; giá chưa có thì ghi "Liên hệ báo giá" thay vì để 0đ. Thông tin liên hệ lấy từ cấu hình trang, chưa chốt hotline (`0948487868` hay `0988716132`).

## 6. Áp dụng trên Zoho Commerce
Khi dựng cửa hàng trên Zoho (Online Store → Themes → Customize):
- Màu chính `#276657`, màu phụ/nhấn `#d5a915`, nền `#faf8f4`.
- Tải `logo.webp` làm logo, `favicon.png` làm favicon, `icon-512.png` làm ảnh chia sẻ mạng xã hội.
- Phông: Be Vietnam Pro (chọn trong Typography nếu có, nếu không dùng phông sans-serif gần nhất).
