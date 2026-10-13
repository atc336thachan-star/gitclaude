# Chuyển vatlieunoithat.vn sang Zoho Commerce (thay thế Django)

Trạng thái: **đã chuẩn bị dữ liệu, chưa ghi gì vào tài khoản Zoho.** Django chỉ còn là nguồn dữ liệu/sao lưu.

## File dữ liệu (thư mục `zoho_export/`)
| File | Nội dung | Dùng để |
|---|---|---|
| `categories.csv` | 389 danh mục (có cây cha/con) | Tạo Categories trong Commerce |
| `items.csv` | 3.632 sản phẩm (188 có giá → Active; còn lại giá 0, Inactive, ẩn khỏi storefront) | Import Items |
| `images.csv` | 7.071 ảnh theo SKU | Gắn ảnh phụ |
| `suppliers.csv` | 495 nhà cung cấp (dữ liệu bên thứ ba, cần rà soát) | Trang tĩnh "Nhà cung cấp" hoặc Zoho CRM |
| `articles.csv` | 17 bài viết (chỉ văn bản; nhiều bài chỉ có ảnh bìa) | Blog/trang tĩnh |
| `legacy_urls.csv` | 3.929 URL cũ → SKU | Tạo redirect 301 sau khi import |

Tạo lại bất cứ lúc nào: `python manage.py export_zoho` và `python manage.py export_zoho_extra`.

## Việc phải làm trước khi import
1. **Ảnh phải có URL công khai.** Cột `Image URL` hiện trỏ về `http://localhost:8000/media/...` nên Zoho không tải được. Cách xử lý: đưa thư mục `media/` (2,6 GB) lên một host/CDN công khai, đặt `SITE_URL` thành địa chỉ đó rồi chạy lại `export_zoho`; hoặc tải ảnh lên Zoho Commerce theo từng sản phẩm.
2. **Sản phẩm chưa có giá (3.444/3.632).** Zoho Commerce là cửa hàng bán trực tiếp, không có sẵn nút "yêu cầu báo giá". Các sản phẩm này đang để Inactive. Chọn một: (a) nhập giá thật rồi bật Active; (b) dùng trang/biểu mẫu "Yêu cầu báo giá" riêng (Zoho Forms/trang tĩnh gắn CRM) và để sản phẩm hiển thị dạng giới thiệu.
3. **Mã SKU** hiện là mã tạm `VLNT-xxxxxxxx`; thay bằng mã thật nếu có (giữ nguyên SKU khi cần đối chiếu `legacy_urls.csv`).
4. **Hotline**: cần chốt `0948487868` hay `0988716132` trước khi nhập vào cấu hình cửa hàng.

## Các bước
1. Tạo cửa hàng trong Zoho Commerce: tên, theme, múi giờ/tiền tệ VND, phương thức thanh toán và vận chuyển (làm trong giao diện Zoho).
2. Tạo danh mục từ `categories.csv` (có thể do Claude làm qua API khi có `organization_id` và được bạn đồng ý).
3. Import `items.csv` (Items → Import), ánh xạ cột: Item Name, SKU, Description, Selling Price, Unit, Category Name, Status, Image URL.
4. Kiểm tra: số lượng item (3.632), vài sản phẩm mẫu, ảnh, danh mục.
5. Tạo trang tĩnh: Giới thiệu (nội dung ở Admin Django → Thông tin doanh nghiệp), Liên hệ, Nhà cung cấp, Kiến thức.
6. Chuyển domain: tạo redirect 301 từ URL cũ sang URL mới theo `legacy_urls.csv`, trỏ DNS `vatlieunoithat.vn` về Zoho Commerce.

## Mất/đổi khi bỏ Django
- Quản trị phân quyền 3 nhóm, trạng thái báo giá 5 bước: chuyển sang Zoho CRM (Leads/Deals) nếu cần.
- Lọc theo thương hiệu/chất liệu/màu và trang công trình: phụ thuộc theme/tính năng Zoho Commerce, cần kiểm tra.
- Danh bạ nhà cung cấp, blog: làm bằng trang tĩnh/blog của Zoho.
