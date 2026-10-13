from django.db import models

from .utils import clean_html


class TimeStamped(models.Model):
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    updated_at = models.DateTimeField("Cập nhật", auto_now=True)

    class Meta:
        abstract = True


class Redirect(models.Model):
    """301 từ URL cũ (vd /san-pham/xxx-c103.html) sang URL mới."""
    old_path = models.CharField("URL cũ", max_length=300, unique=True)
    new_path = models.CharField("URL mới", max_length=300)

    class Meta:
        verbose_name = "Chuyển hướng 301"
        verbose_name_plural = "Chuyển hướng 301"

    def __str__(self):
        return f"{self.old_path} → {self.new_path}"


class SiteSetting(models.Model):
    """Thông tin doanh nghiệp & SEO. Chỉ có 1 bản ghi (singleton)."""
    site_name = models.CharField("Tên website", max_length=120, default="Vật Liệu Nội Thất")
    company_name = models.CharField("Tên pháp lý doanh nghiệp", max_length=200, blank=True,
                                    help_text="Chưa xác minh – điền tên chính thức.")
    tagline = models.CharField("Khẩu hiệu", max_length=200, blank=True)
    hotline = models.CharField("Hotline", max_length=30, blank=True)
    zalo = models.CharField("Số Zalo", max_length=30, blank=True)
    email = models.EmailField("Email", blank=True)
    address = models.CharField("Địa chỉ", max_length=300, blank=True,
                               help_text="Chỉ khi có địa chỉ chính xác mới hiển thị bản đồ.")
    map_embed_url = models.URLField("URL nhúng Google Maps", blank=True, max_length=800)
    working_hours = models.CharField("Giờ làm việc", max_length=200, blank=True)
    service_area = models.CharField("Khu vực phục vụ", max_length=300, blank=True)
    facebook_url = models.URLField("Facebook", blank=True)
    about_html = models.TextField("Nội dung giới thiệu", blank=True)
    shipping_policy = models.TextField("Chính sách vận chuyển", blank=True)
    warranty_policy = models.TextField("Chính sách bảo hành", blank=True)
    return_policy = models.TextField("Chính sách đổi trả", blank=True)
    hero_title = models.CharField("Tiêu đề hero", max_length=200, blank=True)
    hero_subtitle = models.CharField("Mô tả hero", max_length=300, blank=True)
    hero_image = models.ImageField("Ảnh hero", upload_to="site/", blank=True)
    logo = models.ImageField("Logo", upload_to="site/", blank=True)
    seo_title = models.CharField("SEO title mặc định", max_length=70, blank=True)
    seo_description = models.CharField("SEO description mặc định", max_length=170, blank=True)
    og_image = models.ImageField("Ảnh Open Graph mặc định", upload_to="site/", blank=True)
    updated_at = models.DateTimeField("Cập nhật", auto_now=True)

    class Meta:
        verbose_name = "Thông tin doanh nghiệp & SEO"
        verbose_name_plural = "Thông tin doanh nghiệp & SEO"

    def __str__(self):
        return self.site_name

    def save(self, *args, **kwargs):
        self.pk = 1
        for f in ("about_html", "shipping_policy", "warranty_policy", "return_policy"):
            setattr(self, f, clean_html(getattr(self, f)))
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # không cho xóa singleton
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
