from django.conf import settings
from django.core.cache import cache

from .models import SiteSetting


def site(request):
    s = cache.get("site_setting")
    if s is None:
        s = SiteSetting.load()
        cache.set("site_setting", s, 60)
    from catalog.models import Category
    nav = cache.get("nav_categories")
    if nav is None:
        nav = list(Category.objects.filter(is_active=True, parent__isnull=True).order_by("sort_order", "name")[:8])
        cache.set("nav_categories", nav, 60)
    return {"site": s, "nav_categories": nav, "SITE_URL": settings.SITE_URL}
