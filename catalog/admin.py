from django.contrib import admin
from django.core.cache import cache
from django.utils.html import format_html

from .models import Brand, Category, Product, ProductImage, ProductSpec


class DemoFilter(admin.SimpleListFilter):
    title = "Dữ liệu mẫu"
    parameter_name = "demo"

    def lookups(self, request, model_admin):
        return [("1", "Chỉ dữ liệu mẫu"), ("0", "Dữ liệu thật")]

    def queryset(self, request, qs):
        if self.value() in ("0", "1"):
            return qs.filter(is_demo=self.value() == "1")
        return qs


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "sort_order", "is_active", "is_demo", "updated_at"]
    list_filter = ["is_active", "parent", DemoFilter]
    search_fields = ["name", "slug"]
    list_editable = ["sort_order", "is_active"]
    prepopulated_fields = {}

    def save_model(self, *a):
        super().save_model(*a)
        cache.delete("nav_categories")


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "is_demo", "updated_at"]
    list_filter = ["is_active", DemoFilter]
    search_fields = ["name"]


class ImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ["image", "alt", "sort_order"]


class SpecInline(admin.TabularInline):
    model = ProductSpec
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["sku", "name", "category", "brand", "price_type", "price", "unit", "is_active", "is_featured",
                    "is_demo", "updated_at"]
    list_filter = ["is_active", "is_featured", "price_type", "category", "brand", DemoFilter]
    search_fields = ["sku", "name"]
    list_editable = ["is_active", "is_featured"]
    list_select_related = ["category", "brand"]
    date_hierarchy = "updated_at"
    inlines = [ImageInline, SpecInline]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = [
        (None, {"fields": ["name", "slug", "sku", "category", "brand", "is_active", "is_featured", "is_demo"]}),
        ("Giá", {"fields": ["price_type", "price", "unit"],
                 "description": "Chọn 'Liên hệ báo giá' nếu chưa có giá xác nhận – hệ thống sẽ không hiển thị giá."}),
        ("Thuộc tính (dùng cho bộ lọc)", {"fields": ["material", "color", "size", "thickness", "surface", "function"]}),
        ("Nội dung", {"fields": ["short_description", "description", "applications", "usage_guide"]}),
        ("SEO", {"classes": ["collapse"], "fields": ["meta_title", "meta_description"]}),
        ("Thời gian", {"fields": ["created_at", "updated_at"]}),
    ]


from .models import Supplier, SupplierCategory  # noqa: E402


@admin.register(SupplierCategory)
class SupplierCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "sort_order"]
    search_fields = ["name"]


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "phone", "email", "website", "is_active", "updated_at"]
    list_filter = ["is_active", "categories"]
    search_fields = ["name", "phone", "email", "website"]
    list_editable = ["is_active"]
    filter_horizontal = ["categories"]
