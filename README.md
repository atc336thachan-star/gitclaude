# Vật Liệu Nội Thất — website & quản trị (Django)

Website thương mại vật liệu nội thất: danh mục/sản phẩm có lọc, báo giá, công trình, kiến thức, liên hệ; admin có phân quyền.
Render phía server (SEO tốt, ít JavaScript). Thay thế bản SPA Nuxt hiện tại của vatlieunoithat.vn.

## 1. Audit website hiện tại (tóm tắt)
Truy cập ngày 12/10/2026 (HTML thô + trình duyệt):
- Nuxt SPA chạy hoàn toàn phía client (`data-ssr="false"`): HTML trả về gần như rỗng (~2 KB) → công cụ tìm kiếm/mạng xã hội khó đọc nội dung; không có SSR.
- `robots.txt` và `sitemap.xml` trả HTTP 404 (nhưng phần thân vẫn là trang SPA, nội dung 404 "mềm").
- Route không tồn tại (`/gioi-thieu`) cũng trả 404 kèm shell SPA; trang chủ có liên kết `#` vô tác dụng.
- Meta description chứa thực thể HTML bị mã hóa thừa (`&#224;`…).
- Backend là API ngoài (`cloud.synck.io.vn`) do bên thứ ba; trang liên kết sang subdomain `vatlieunoithat.synck.io.vn` (phân mảnh URL/SEO).
- Mô hình hiện tại là "sàn giao thương" (nhà cung cấp, đăng ký, cổng NCC). Bản mới tập trung catalog + báo giá; các route NCC/đăng ký được 301 về `/lien-he/` — **cần chủ website xác nhận** có giữ tính năng nhà cung cấp không.
- Không có nội dung/số liệu nào của site cũ được sao chép; số hotline/Zalo/email lấy từ site cũ chỉ để khởi tạo cấu hình (**cần xác nhận** trong Admin).

## 2. Kiến trúc
Django 5 + PostgreSQL (prod) / SQLite (dev), templates server-side, WhiteNoise cho static, Django Admin tùy biến làm trang quản trị.

| App | Nội dung |
|---|---|
| `core` | SiteSetting (singleton), trang chủ/giới thiệu/liên hệ, sitemap, robots, redirect URL cũ, admin dashboard, lệnh `setup_roles` `init_site` `seed_demo` |
| `catalog` | Category (cây), Brand, Product, ProductImage (tự chuyển WebP), ProductSpec |
| `content` | Article, ArticleCategory, Project, ProjectImage |
| `leads` | Lead (gom theo SĐT), QuoteRequest (5 trạng thái), ContactMessage |

URL: `/san-pham/`, `/danh-muc/<slug>/`, `/san-pham/<slug>/`, `/bao-gia/`, `/cong-trinh/`, `/tin-tuc/`, `/ve-chung-toi/`, `/lien-he/`, `/sitemap.xml`, `/robots.txt`, admin `/quan-tri/` (đổi qua `ADMIN_URL`).

## 3. Chạy local
```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
copy .env.example .env            # đặt DJANGO_DEBUG=1 khi dev
python manage.py migrate
python manage.py setup_roles      # tạo nhóm phân quyền
python manage.py init_site        # khởi tạo thông tin doanh nghiệp (cần xác nhận lại)
python manage.py seed_demo        # (tùy chọn) dữ liệu MẪU, gắn nhãn "Dữ liệu mẫu"; xóa: seed_demo --clear
python manage.py createsuperuser
python manage.py runserver
python manage.py test tests       # 23 test
```
Phân quyền (Admin → Người dùng → Nhóm): **Biên tập nội dung** (sản phẩm/bài viết/công trình), **Kinh doanh** (xử lý báo giá, khách hàng), **Quản lý website** (cả hai + thông tin doanh nghiệp/SEO). Superuser có toàn quyền. Quyền được kiểm tra ở backend (Django permissions), không chỉ ẩn nút.

## 4. Biến môi trường
Xem `.env.example`. `DJANGO_SECRET_KEY` bắt buộc khi `DJANGO_DEBUG=0`. Không đưa secret vào frontend/mã nguồn.

## 5. Deploy production (gợi ý Linux + Nginx + Gunicorn + PostgreSQL)
1. Tạo DB: `createdb vlnt` và user; đặt `DATABASE_URL`.
2. `pip install -r requirements.txt`, đặt `.env` (DEBUG=0, HOSTS, CSRF origins, SITE_URL, ADMIN_URL khó đoán).
3. `python manage.py migrate && python manage.py collectstatic --noinput && python manage.py setup_roles && python manage.py init_site && python manage.py createsuperuser`
4. Chạy: `gunicorn config.wsgi:application --workers 3 --bind 127.0.0.1:8000` (systemd), Nginx reverse proxy + HTTPS (Let's Encrypt), đặt `TRUST_X_FORWARDED_FOR=1` và header `X-Forwarded-Proto`.
5. Nginx phục vụ `/media/` trực tiếp từ thư mục `media/`; **không** public thư mục `private_media/` (tệp khách đính kèm — chỉ tải qua `/tep-bao-gia/<id>/` cho nhân viên có quyền).
6. Throttle form dùng cache cục bộ theo từng worker; nếu cần chặt hơn hãy cấu hình Redis/DB cache trong `CACHES`.
7. `python manage.py check --deploy` chỉ còn cảnh báo tùy chọn W021 (HSTS preload).
8. Chuyển domain: các URL `/san-pham`, `/bao-gia`, `/tin-tuc`, `/lien-he`, `/ve-chung-toi`, `/tu-van` giữ nguyên; `/gioi-thieu`, `/nha-cung-cap`, `/dang-ky`, `/nha-cung-cap-portal/dang-nhap` → 301. URL sản phẩm cũ dạng `?categoryId=`/`synck.io.vn` cần ánh xạ riêng khi có dữ liệu cũ (chưa làm — chưa có dữ liệu).

## 6. Sao lưu & phục hồi
```bash
# Sao lưu (cron hằng ngày)
pg_dump -Fc "$DATABASE_URL" > backups/vlnt_$(date +%F).dump
tar czf backups/media_$(date +%F).tgz media private_media
# Phục hồi
pg_restore --clean --no-owner -d vlnt backups/vlnt_YYYY-MM-DD.dump
tar xzf backups/media_YYYY-MM-DD.tgz
```
Lưu bản sao ở nơi khác máy chủ và thử phục hồi định kỳ. Với SQLite (dev): sao chép `db.sqlite3`.

## 7. Bảo mật đã triển khai
CSRF, mật khẩu băm PBKDF2 (tối thiểu 10 ký tự), cookie Secure/HttpOnly/SameSite + HSTS khi production, honeypot + throttle theo IP cho form, kiểm tra SĐT/email/độ dài ở backend, làm sạch HTML nhập từ admin (bleach), upload đính kèm chỉ JPG/PNG/WebP/PDF ≤ 5 MB (xác minh nội dung thật, đổi tên ngẫu nhiên, lưu ngoài thư mục public), ảnh admin tự chuyển WebP, `X-Frame-Options: DENY`, đường dẫn admin cấu hình được.

## 8. Cần doanh nghiệp cung cấp
Tên pháp lý, địa chỉ chính xác (để hiện bản đồ), giờ làm việc, khu vực phục vụ, logo, ảnh hero, nội dung giới thiệu, chính sách vận chuyển/bảo hành/đổi trả, danh mục + sản phẩm thật (ảnh, mã, thông số, giá nếu muốn công khai), thương hiệu phân phối, công trình thực tế (có ảnh/khẳng định được), bài viết, xác nhận hotline/Zalo/email, quyết định về tính năng nhà cung cấp.

## 9. Chưa làm / chưa kiểm thử
- Chưa có ảnh thật (thẻ dùng ô giữ chỗ); font hệ thống (chưa nhúng webfont).
- Chưa import dữ liệu từ site cũ (API ngoài, chưa xác minh quyền/cấu trúc).
- Chưa đo Core Web Vitals trên dữ liệu người dùng thật; chưa test trên nhiều trình duyệt/thiết bị thật (mới kiểm tra viewport 375 px và desktop trong trình duyệt tích hợp).
- Chưa chạy trên PostgreSQL (test dùng SQLite), chưa gửi email thông báo khi có báo giá mới (xem trong Admin), chưa có tính năng so sánh sản phẩm, chưa có nhà cung cấp/cổng đăng nhập khách.
- Trình soạn thảo nội dung admin là textarea HTML (đã làm sạch), chưa có WYSIWYG.
