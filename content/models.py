from django.db import models
from django.urls import reverse
from django.utils import timezone

from catalog.models import Product, unique_slug
from core.models import TimeStamped
from core.utils import clean_html, optimize_image


def _webp(instance, field_name):
    f = getattr(instance, field_name)
    if f and not f._committed:
        new, _ = optimize_image(f.file)
        if new:
            f.save(new.name, new, save=False)


class ArticleCategory(models.Model):
    name = models.CharField("Tên chuyên mục", max_length=120)
    slug = models.SlugField(max_length=150, unique=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Chuyên mục kiến thức"
        verbose_name_plural = "Chuyên mục kiến thức"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name, 150)
        super().save(*args, **kwargs)


class Article(TimeStamped):
    title = models.CharField("Tiêu đề", max_length=250)
    slug = models.SlugField(max_length=190, unique=True, blank=True)
    category = models.ForeignKey(ArticleCategory, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name="articles", verbose_name="Chuyên mục")
    excerpt = models.CharField("Tóm tắt", max_length=300, blank=True)
    body = models.TextField("Nội dung")
    cover = models.ImageField("Ảnh bìa", upload_to="articles/", blank=True)
    related_products = models.ManyToManyField(Product, blank=True, related_name="articles", verbose_name="Sản phẩm liên quan")
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=170, blank=True)
    is_published = models.BooleanField("Xuất bản", default=False, db_index=True)
    published_at = models.DateTimeField("Ngày xuất bản", null=True, blank=True)
    is_demo = models.BooleanField("Dữ liệu mẫu", default=False)

    class Meta:
        ordering = ["-published_at", "-id"]
        verbose_name = "Bài viết"
        verbose_name_plural = "Bài viết kiến thức"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.title)
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        self.body = clean_html(self.body)
        _webp(self, "cover")
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("content:article", args=[self.slug])


class Project(TimeStamped):
    title = models.CharField("Tên công trình", max_length=250)
    slug = models.SlugField(max_length=190, unique=True, blank=True)
    location = models.CharField("Khu vực", max_length=150, blank=True)
    project_type = models.CharField("Loại công trình", max_length=100, blank=True)
    summary = models.CharField("Tóm tắt", max_length=300, blank=True)
    description = models.TextField("Mô tả", blank=True)
    materials_used = models.CharField("Vật liệu sử dụng", max_length=300, blank=True)
    cover = models.ImageField("Ảnh bìa", upload_to="projects/", blank=True)
    products = models.ManyToManyField(Product, blank=True, related_name="projects", verbose_name="Sản phẩm liên quan")
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=170, blank=True)
    is_published = models.BooleanField("Hiển thị", default=False, db_index=True)
    sort_order = models.PositiveIntegerField("Thứ tự", default=0)
    is_demo = models.BooleanField("Dữ liệu mẫu", default=False)

    class Meta:
        ordering = ["sort_order", "-created_at"]
        verbose_name = "Công trình"
        verbose_name_plural = "Công trình / dự án"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.title)
        self.description = clean_html(self.description)
        _webp(self, "cover")
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("content:project", args=[self.slug])


class ProjectImage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="projects/")
    alt = models.CharField(max_length=200, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Ảnh công trình"
        verbose_name_plural = "Ảnh công trình"

    def save(self, *args, **kwargs):
        _webp(self, "image")
        super().save(*args, **kwargs)
