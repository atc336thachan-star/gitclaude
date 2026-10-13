from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render

from catalog.models import Category, Product
from content.models import Article, Project
from core.models import SiteSetting
from leads.forms import ContactForm


def _category_cover(cat):
    """Ảnh đại diện danh mục: ảnh riêng, nếu không có thì ảnh của sản phẩm đầu tiên trong nhánh."""
    from django.core.cache import cache
    from catalog.models import ProductImage
    key = f"catcover:{cat.pk}"
    url = cache.get(key)
    if url is None:
        url = cat.image.url if cat.image else ""
        if not url:
            im = (ProductImage.objects.filter(product__category_id__in=cat.descendant_ids(), product__is_active=True)
                  .order_by("-product__is_featured", "product__id").first())
            url = im.image.url if im else ""
        cache.set(key, url, 600)
    return url


def home(request):
    from catalog.models import ProductImage
    cats = list(Category.objects.filter(is_active=True, parent__isnull=True)[:8])
    for c in cats:
        c.cover_url = _category_cover(c)
    hero_imgs = list(ProductImage.objects.filter(product__is_active=True, product__is_featured=True)
                     .select_related("product").order_by("product__id")[:4]) if not SiteSetting.load().hero_image else []
    return render(request, "core/home.html", {
        "hero_imgs": hero_imgs,
        "categories": cats,
        "featured": Product.objects.filter(is_active=True, is_featured=True).select_related("category", "brand").prefetch_related("images")[:8],
        "projects": Project.objects.filter(is_published=True)[:3],
        "articles": Article.objects.filter(is_published=True)[:3],
        "form": ContactForm(initial={"source": "consult"}),
    })


def about(request):
    return render(request, "core/about.html", {"items": [("Giới thiệu", None)]})


def contact(request):
    done = request.session.pop("contact_done", False)
    return render(request, "core/contact.html", {"form": ContactForm(), "done": done, "items": [("Liên hệ", None)]})


def robots(request):
    lines = ["User-agent: *", "Disallow: /" + settings.ADMIN_URL, "Disallow: /bao-gia/da-gui/",
             "Disallow: /tep-bao-gia/", f"Sitemap: {settings.SITE_URL}/sitemap.xml"]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


def not_found(request, exception=None):
    return render(request, "404.html", status=404)


def server_error(request):
    return render(request, "500.html", status=500)
