from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from core.models import TimeStamped
from core.utils import clean_html, optimize_image


def unique_slug(instance, source, max_len=190):
    base = slugify(source, allow_unicode=False)[:max_len] or "muc"
    slug, n = base, 2
    qs = type(instance).objects.exclude(pk=instance.pk)
    while qs.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


class Category(TimeStamped):
    name = models.CharField("Tên danh mục", max_length=150)
    slug = models.SlugField("Slug", max_length=190, unique=True, blank=True)
    parent = models.ForeignKey("self", verbose_name="Danh mục cha", null=True, blank=True,
                               on_delete=models.PROTECT, related_name="children")
    description = models.TextField("Mô tả ngắn", blank=True)
    seo_content = models.TextField("Nội dung SEO (cuối trang)", blank=True,
                                   help_text="Nội dung hữu ích cho người đọc, không nhồi từ khóa.")
    image = models.ImageField("Ảnh đại diện", upload_to="categories/", blank=True)
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=170, blank=True)
    sort_order = models.PositiveIntegerField("Thứ tự", default=0)
    is_active = models.BooleanField("Hiển thị", default=True)
    is_demo = models.BooleanField("Dữ liệu mẫu", default=False)
    legacy_id = models.CharField("ID site cũ", max_length=40, null=True, blank=True, unique=True, editable=False)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Danh mục"
        verbose_name_plural = "Danh mục sản phẩm"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        self.seo_content = clean_html(self.seo_content)
        if self.image and not self.image.name.endswith(".webp") and not self.image._committed:
            f, _ = optimize_image(self.image.file)
            if f:
                self.image.save(f.name, f, save=False)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:category", args=[self.slug])

    def ancestors(self):
        chain, node = [], self.parent
        while node:
            chain.insert(0, node)
            node = node.parent
        return chain

    def descendant_ids(self):
        ids, frontier = [self.pk], [self.pk]
        while frontier:
            frontier = list(Category.objects.filter(parent_id__in=frontier).values_list("pk", flat=True))
            ids += frontier
        return ids


class Brand(TimeStamped):
    name = models.CharField("Tên thương hiệu", max_length=120)
    slug = models.SlugField(max_length=150, unique=True, blank=True)
    description = models.TextField("Mô tả", blank=True)
    logo = models.ImageField(upload_to="brands/", blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField("Hiển thị", default=True)
    is_demo = models.BooleanField("Dữ liệu mẫu", default=False)

    class Meta:
        ordering = ["name"]
        verbose_name = "Thương hiệu"
        verbose_name_plural = "Thương hiệu"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name, 150)
        super().save(*args, **kwargs)


class Product(TimeStamped):
    PRICE_FIXED, PRICE_REF, PRICE_QUOTE = "fixed", "reference", "quote"
    PRICE_TYPES = [(PRICE_FIXED, "Giá niêm yết"), (PRICE_REF, "Giá tham khảo (cần xác nhận)"),
                   (PRICE_QUOTE, "Liên hệ báo giá")]

    name = models.CharField("Tên sản phẩm", max_length=250)
    slug = models.SlugField(max_length=190, unique=True, blank=True)
    sku = models.CharField("Mã sản phẩm", max_length=60, unique=True, blank=True)
    category = models.ForeignKey(Category, verbose_name="Danh mục", on_delete=models.PROTECT, related_name="products")
    brand = models.ForeignKey(Brand, verbose_name="Thương hiệu", null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="products")
    short_description = models.CharField("Mô tả ngắn", max_length=300, blank=True)
    description = models.TextField("Mô tả chi tiết", blank=True)
    applications = models.TextField("Ứng dụng thực tế", blank=True)
    usage_guide = models.TextField("Hướng dẫn sử dụng / thi công", blank=True)

    price_type = models.CharField("Loại giá", max_length=10, choices=PRICE_TYPES, default=PRICE_QUOTE)
    price = models.DecimalField("Giá (VND)", max_digits=14, decimal_places=0, null=True, blank=True)
    unit = models.CharField("Đơn vị tính", max_length=30, blank=True, help_text="VD: m², m, tấm, bộ")

    material = models.CharField("Chất liệu", max_length=100, blank=True, db_index=True)
    color = models.CharField("Màu sắc", max_length=60, blank=True, db_index=True)
    size = models.CharField("Kích thước", max_length=100, blank=True)
    thickness = models.CharField("Độ dày", max_length=40, blank=True)
    surface = models.CharField("Bề mặt", max_length=60, blank=True)
    function = models.CharField("Công năng", max_length=100, blank=True)

    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=170, blank=True)
    is_active = models.BooleanField("Hiển thị", default=True, db_index=True)
    is_featured = models.BooleanField("Nổi bật / được quan tâm", default=False)
    is_demo = models.BooleanField("Dữ liệu mẫu", default=False)
    legacy_id = models.CharField("ID site cũ", max_length=40, null=True, blank=True, unique=True, editable=False)
    view_count = models.PositiveIntegerField("Lượt xem (site cũ)", default=0, editable=False)

    class Meta:
        ordering = ["-is_featured", "-updated_at"]
        verbose_name = "Sản phẩm"
        verbose_name_plural = "Sản phẩm"
        indexes = [models.Index(fields=["is_active", "category"]), models.Index(fields=["is_active", "-updated_at"])]

    def __str__(self):
        return f"{self.sku} – {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        if not self.sku:  # mã tạm khi chưa nhập: SP-<id>
            super().save(*args, **kwargs)
            self.sku = f"SP-{self.pk}"
            kwargs.pop("force_insert", None)
        if self.price_type == self.PRICE_QUOTE:
            self.price = None  # giá cần báo giá thì không lưu giá
        for f in ("description", "applications", "usage_guide"):
            setattr(self, f, clean_html(getattr(self, f)))
        super().save(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.price_type in (self.PRICE_FIXED, self.PRICE_REF) and not self.price:
            raise ValidationError({"price": "Cần nhập giá khi chọn giá niêm yết hoặc giá tham khảo."})

    def get_absolute_url(self):
        return reverse("catalog:product", args=[self.slug])

    @property
    def has_price(self):
        return self.price_type != self.PRICE_QUOTE and self.price is not None

    @property
    def main_image(self):
        imgs = list(self.images.all())
        return imgs[0] if imgs else None


class ProductImage(TimeStamped):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField("Ảnh", upload_to="products/")
    alt = models.CharField("Mô tả ảnh (alt)", max_length=200, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True, editable=False)
    height = models.PositiveIntegerField(null=True, blank=True, editable=False)
    sort_order = models.PositiveIntegerField("Thứ tự", default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Ảnh sản phẩm"
        verbose_name_plural = "Ảnh sản phẩm"

    def save(self, *args, **kwargs):
        if self.image and not self.image._committed:  # ảnh mới upload -> chuẩn hóa WebP, lưu kích thước
            f, size = optimize_image(self.image.file)
            if f:
                self.image.save(f.name, f, save=False)
                self.width, self.height = size
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Ảnh #{self.pk} của {self.product_id}"


class ProductSpec(models.Model):
    """Thông số kỹ thuật dạng cặp tên–giá trị. Chỉ nhập khi có dữ liệu xác minh."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="specs")
    name = models.CharField("Thông số", max_length=100)
    value = models.CharField("Giá trị", max_length=250)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Thông số kỹ thuật"
        verbose_name_plural = "Thông số kỹ thuật"

    def __str__(self):
        return f"{self.name}: {self.value}"


class SupplierCategory(models.Model):
    name = models.CharField("Nhóm nhà cung cấp", max_length=150)
    slug = models.SlugField(max_length=190, unique=True, blank=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children",
                               verbose_name="Nhóm cha")
    sort_order = models.PositiveIntegerField("Thứ tự", default=0)
    legacy_id = models.CharField(max_length=40, null=True, blank=True, unique=True, editable=False)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Nhóm nhà cung cấp"
        verbose_name_plural = "Nhóm nhà cung cấp"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def descendant_ids(self):
        ids, frontier = [self.pk], [self.pk]
        while frontier:
            frontier = list(SupplierCategory.objects.filter(parent_id__in=frontier).values_list("pk", flat=True))
            ids += frontier
        return ids


class Supplier(TimeStamped):
    """Nhà cung cấp / đối tác. Thông tin liên hệ cần được xác minh trước khi công khai."""
    name = models.CharField("Tên nhà cung cấp", max_length=250)
    slug = models.SlugField(max_length=190, unique=True, blank=True)
    categories = models.ManyToManyField(SupplierCategory, blank=True, related_name="suppliers", verbose_name="Nhóm")
    logo = models.ImageField(upload_to="suppliers/", blank=True)
    phone = models.CharField("Điện thoại", max_length=80, blank=True)
    email = models.CharField("Email", max_length=200, blank=True)
    website = models.URLField("Website", max_length=300, blank=True)
    address = models.CharField("Địa chỉ", max_length=400, blank=True)
    notes = models.TextField("Ghi chú", blank=True)
    is_active = models.BooleanField("Hiển thị", default=True, db_index=True)
    legacy_id = models.CharField(max_length=40, null=True, blank=True, unique=True, editable=False)

    class Meta:
        ordering = ["name"]
        verbose_name = "Nhà cung cấp"
        verbose_name_plural = "Nhà cung cấp"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        if self.logo and not self.logo._committed:
            f, _ = optimize_image(self.logo.file, max_side=400)
            if f:
                self.logo.save(f.name, f, save=False)
        super().save(*args, **kwargs)
