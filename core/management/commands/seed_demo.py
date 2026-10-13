"""Dữ liệu MẪU để xem giao diện. Mọi bản ghi gắn is_demo=True; xóa bằng `seed_demo --clear`.

Không có giá, tồn kho, thông số kỹ thuật hay công trình thật được tạo ở đây: sản phẩm mẫu đều ở dạng
"liên hệ báo giá"; bài viết/công trình chỉ chứa nội dung giữ chỗ.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from catalog.models import Brand, Category, Product
from content.models import Article, ArticleCategory, Project
from core.models import SiteSetting

CATS = ["Sàn gỗ & sàn nhựa", "Gạch ốp lát", "Tấm ốp tường", "Đá nhân tạo", "Phụ kiện nội thất", "Đèn & thiết bị"]
BRANDS = ["Thương hiệu mẫu A", "Thương hiệu mẫu B"]
MATERIALS = ["Gỗ công nghiệp", "Gốm", "PVC", "Đá nhân tạo", "Kim loại"]
COLORS = ["Vân gỗ sáng", "Xám nhạt", "Kem", "Trắng"]

PLACEHOLDER = "<p>[Nội dung mẫu – thay bằng nội dung chính thức đã được xác minh.]</p>"


class Command(BaseCommand):
    help = "Tạo (hoặc --clear để xóa) dữ liệu mẫu."

    def add_arguments(self, p):
        p.add_argument("--clear", action="store_true")

    def handle(self, *a, clear=False, **o):
        if clear:
            for m in (Project, Article, Product, Brand):
                m.objects.filter(is_demo=True).delete()
            Category.objects.filter(is_demo=True, products__isnull=True).delete()
            self.stdout.write("Đã xóa dữ liệu mẫu.")
            return
        cats = [Category.objects.get_or_create(name=n, defaults={"is_demo": True, "sort_order": i,
                "description": "[Mẫu] Mô tả danh mục – cần thay bằng nội dung thật."})[0] for i, n in enumerate(CATS)]
        brands = [Brand.objects.get_or_create(name=n, defaults={"is_demo": True})[0] for n in BRANDS]
        n = 0
        for ci, cat in enumerate(cats):
            for k in range(1, 5):
                n += 1
                Product.objects.get_or_create(sku=f"DEMO-{n:03d}", defaults=dict(
                    name=f"[Mẫu] {cat.name} {k}", category=cat, brand=brands[n % 2],
                    price_type="quote", unit="m²" if ci < 4 else "bộ",
                    material=MATERIALS[(ci + k) % len(MATERIALS)], color=COLORS[(n) % len(COLORS)],
                    short_description="Sản phẩm mẫu để xem bố cục – chưa phải sản phẩm thật.",
                    description=PLACEHOLDER, is_featured=(k == 1), is_demo=True))
        ac, _ = ArticleCategory.objects.get_or_create(name="Hướng dẫn lựa chọn")
        for t in ["[Mẫu] Cách chọn sàn cho phòng khách", "[Mẫu] So sánh các loại tấm ốp tường"]:
            Article.objects.get_or_create(title=t, defaults=dict(
                category=ac, excerpt="Bài viết mẫu – thay bằng nội dung biên tập thật.", body=PLACEHOLDER,
                is_published=True, published_at=timezone.now(), is_demo=True))
        Project.objects.get_or_create(title="[Mẫu] Công trình minh họa", defaults=dict(
            location="[Khu vực]", project_type="[Loại công trình]", summary="Công trình mẫu – chưa phải dự án thật.",
            description=PLACEHOLDER, is_published=True, is_demo=True))
        self.stdout.write(f"Đã tạo dữ liệu mẫu ({n} sản phẩm). Chạy `seed_demo --clear` để xóa.")
