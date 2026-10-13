from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, re_path
from django.views.static import serve

from core import agent_api
from core import views as core_views
from core.sitemaps import SITEMAPS

app_name_core = "core"
core_patterns = ([
    path("", core_views.home, name="home"),
    path("ve-chung-toi/", core_views.about, name="about"),
    path("lien-he/", core_views.contact, name="contact"),
], "core")

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include(core_patterns)),
    path("", include("catalog.urls")),
    path("", include("content.urls")),
    path("", include("leads.urls")),
    path("tu-van/", core_views.contact, name="consult"),
    path("api/agent/products/", agent_api.products, name="agent_products"),
    path("api/agent/products/<str:sku>/", agent_api.product_detail, name="agent_product"),
    path("api/agent/quotes/", agent_api.create_quote, name="agent_quote"),
    path("api/agent/openapi.json", agent_api.openapi, name="agent_openapi"),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    path("robots.txt", core_views.robots),
]
# Ảnh công khai: phục vụ qua Django ở dev; production nên để Nginx/CDN phục vụ /media/.
if settings.DEBUG or not getattr(settings, "MEDIA_SERVED_BY_PROXY", False):
    urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT})]

handler404 = "core.views.not_found"
handler500 = "core.views.server_error"
