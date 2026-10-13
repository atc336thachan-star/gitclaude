from django.core.management.base import BaseCommand

from core.models import SiteSetting


class Command(BaseCommand):
    help = "Khởi tạo thông tin doanh nghiệp ban đầu. Liên hệ lấy từ website hiện tại – quản trị viên cần xác nhận."

    def handle(self, *a, **o):
        s = SiteSetting.load()
        if s.hotline or s.email:
            self.stdout.write("SiteSetting đã có dữ liệu, bỏ qua.")
            return
        s.site_name = "Vật Liệu Nội Thất"
        s.tagline = "Kênh kết nối nhà cung cấp, đơn vị thiết kế và nhà thầu nội thất"  # lấy từ mô tả website cũ
        s.hotline = "0988716132"                      # từ vatlieunoithat.vn (CẦN XÁC NHẬN)
        s.zalo = "0903232317"                         # từ vatlieunoithat.vn (CẦN XÁC NHẬN)
        s.email = "vatlieunoithat.vn@gmail.com"       # từ vatlieunoithat.vn (CẦN XÁC NHẬN)
        s.facebook_url = "https://www.facebook.com/vatlieunoithat.vn/"
        s.hero_title = "Vật liệu nội thất cho mọi không gian"
        s.hero_subtitle = "Tìm kiếm vật liệu, nhận tư vấn và báo giá từ đội ngũ chuyên môn."
        s.about_html = ("<p>[CHỜ NỘI DUNG CHÍNH THỨC] Giới thiệu doanh nghiệp, năng lực và lĩnh vực hoạt động. "
                        "Chỉ đăng thông tin đã được xác minh.</p>")
        s.save()
        self.stdout.write("Đã khởi tạo SiteSetting.")
