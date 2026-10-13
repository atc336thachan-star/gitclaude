from django.contrib import admin
from django.core.cache import cache

from .models import Redirect, SiteSetting


@admin.register(Redirect)
class RedirectAdmin(admin.ModelAdmin):
    list_display = ["old_path", "new_path"]
    search_fields = ["old_path", "new_path"]


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    fieldsets = [
        ("Doanh nghiệp", {"fields": ["site_name", "company_name", "tagline", "logo"]}),
        ("Liên hệ", {"fields": ["hotline", "zalo", "email", "facebook_url", "address", "map_embed_url",
                                "working_hours", "service_area"]}),
        ("Trang chủ (Hero)", {"fields": ["hero_title", "hero_subtitle", "hero_image"]}),
        ("Nội dung & chính sách", {"fields": ["about_html", "shipping_policy", "warranty_policy", "return_policy"]}),
        ("SEO mặc định", {"fields": ["seo_title", "seo_description", "og_image"]}),
    ]

    def has_add_permission(self, request):
        return not SiteSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        cache.delete("site_setting")
