from django.contrib.admin import AdminSite
from django.contrib.admin.apps import AdminConfig
from django.urls import reverse
from django.utils import timezone


class SiteAdmin(AdminSite):
    site_header = "Quản trị Vật Liệu Nội Thất"
    site_title = "Quản trị"
    index_title = "Tổng quan"
    index_template = "admin/dashboard.html"

    def index(self, request, extra_context=None):
        from catalog.models import Product
        from content.models import Article, Project
        from leads.models import ContactMessage, QuoteRequest
        user = request.user
        stats = []
        if user.has_perm("leads.view_quoterequest"):
            q = QuoteRequest.objects
            stats += [("Báo giá mới", q.filter(status="new").count(), "admin:leads_quoterequest_changelist?status__exact=new"),
                      ("Đang liên hệ", q.filter(status="contacting").count(), "admin:leads_quoterequest_changelist?status__exact=contacting"),
                      ("Báo giá 7 ngày qua", q.filter(created_at__gte=timezone.now() - timezone.timedelta(days=7)).count(),
                       "admin:leads_quoterequest_changelist")]
            stats.append(("Tin nhắn chưa xử lý", ContactMessage.objects.filter(status="new").count(),
                          "admin:leads_contactmessage_changelist?status__exact=new"))
        if user.has_perm("catalog.view_product"):
            stats.append(("Sản phẩm đang hiển thị", Product.objects.filter(is_active=True).count(), "admin:catalog_product_changelist"))
        if user.has_perm("content.view_article"):
            stats.append(("Bài viết đã xuất bản", Article.objects.filter(is_published=True).count(), "admin:content_article_changelist"))
        if user.has_perm("content.view_project"):
            stats.append(("Công trình hiển thị", Project.objects.filter(is_published=True).count(), "admin:content_project_changelist"))
        def href(spec):
            name, _, query = spec.partition("?")
            return reverse(name) + (f"?{query}" if query else "")
        stats = [(label, value, href(spec)) for label, value, spec in stats]
        extra_context = {**(extra_context or {}), "stats": stats}
        return super().index(request, extra_context)


class CoreAdminConfig(AdminConfig):
    default_site = "core.admin_site.SiteAdmin"
