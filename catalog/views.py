from decimal import Decimal, InvalidOperation

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from leads.forms import QuoteForm

from .models import Brand, Category, Product

SORTS = {
    "moi": ("-updated_at", "Mới cập nhật"),
    "ten": ("name", "Tên A–Z"),
    "gia-tang": ("price", "Giá thấp → cao"),
    "gia-giam": ("-price", "Giá cao → thấp"),
}
PER_PAGE = 12


def _dec(v):
    try:
        return Decimal(v) if v else None
    except InvalidOperation:
        return None


def _listing(request, category=None):
    qs = Product.objects.filter(is_active=True, category__is_active=True).select_related("category", "brand").prefetch_related("images")
    base = qs
    if category:
        qs = base = qs.filter(category_id__in=category.descendant_ids())
    g = request.GET
    q = g.get("q", "").strip()[:100]
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(short_description__icontains=q))
    brands = [b for b in g.getlist("thuong-hieu") if b][:10]
    if brands:
        qs = qs.filter(brand__slug__in=brands)
    for param, field in (("chat-lieu", "material"), ("mau-sac", "color"), ("cong-nang", "function")):
        vals = [v for v in g.getlist(param) if v][:10]
        if vals:
            qs = qs.filter(**{f"{field}__in": vals})
    if g.get("danh-muc") and not category:
        c = Category.objects.filter(slug=g["danh-muc"], is_active=True).first()
        if c:
            qs = qs.filter(category_id__in=c.descendant_ids())
    lo, hi = _dec(g.get("gia-tu")), _dec(g.get("gia-den"))
    if lo is not None:
        qs = qs.filter(price__gte=lo)
    if hi is not None:
        qs = qs.filter(price__lte=hi)
    sort = g.get("sap-xep", "moi")
    if sort not in SORTS:
        sort = "moi"
    qs = qs.order_by(SORTS[sort][0], "id")
    page = Paginator(qs, PER_PAGE).get_page(g.get("page"))
    facets = {
        "brands": Brand.objects.filter(is_active=True, products__in=base).distinct().order_by("name"),
        "materials": sorted(set(base.exclude(material="").values_list("material", flat=True))),
        "colors": sorted(set(base.exclude(color="").values_list("color", flat=True))),
        "functions": sorted(set(base.exclude(function="").values_list("function", flat=True))),
    }
    active = {
        "thuong-hieu": brands, "chat-lieu": g.getlist("chat-lieu"), "mau-sac": g.getlist("mau-sac"),
        "cong-nang": g.getlist("cong-nang"),
    }
    has_prices = base.filter(price__isnull=False).exists()
    n_active = sum(len(v) for v in active.values()) + bool(lo is not None) + bool(hi is not None)
    return {"page": page, "facets": facets, "active": active, "q": q, "sort": sort, "sorts": SORTS,
            "gia_tu": g.get("gia-tu", ""), "gia_den": g.get("gia-den", ""), "n_active": n_active,
            "filtered": bool(q or n_active), "has_prices": has_prices,
            "sel_brand": active["thuong-hieu"], "sel_material": active["chat-lieu"],
            "sel_color": active["mau-sac"], "sel_function": active["cong-nang"]}


def product_list(request):
    legacy = request.GET.get("categoryId")  # URL cũ: /san-pham?categoryId=<id>
    if legacy:
        c = Category.objects.filter(legacy_id=legacy).first()
        return redirect(c.get_absolute_url(), permanent=True) if c else redirect("catalog:list", permanent=True)
    ctx = _listing(request)
    ctx["categories"] = Category.objects.filter(is_active=True, parent__isnull=True)
    ctx["items"] = [("Sản phẩm", None)]
    return render(request, "catalog/list.html", ctx)


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    ctx = _listing(request, category)
    ctx["categories"] = Category.objects.filter(is_active=True, parent__isnull=True)
    ctx.update(category=category, children=category.children.filter(is_active=True),
               items=[("Sản phẩm", reverse("catalog:list"))] + [(c.name, c.get_absolute_url()) for c in category.ancestors()] + [(category.name, None)])
    return render(request, "catalog/list.html", ctx)


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("category", "brand").prefetch_related("images", "specs"),
        slug=slug, is_active=True)
    related = (Product.objects.filter(is_active=True, category=product.category).exclude(pk=product.pk)
               .select_related("category", "brand").prefetch_related("images")[:4])
    return render(request, "catalog/detail.html", {
        "product": product, "related": related,
        "items": [("Sản phẩm", reverse("catalog:list"))] + [(c.name, c.get_absolute_url()) for c in product.category.ancestors() + [product.category]] + [(product.name, None)],
        "quote_form": QuoteForm(initial={"product": product.pk, "product_text": product.name, "unit": product.unit}),
        "projects": product.projects.filter(is_published=True)[:3],
    })


def supplier_list(request):
    from .models import Supplier, SupplierCategory
    qs = Supplier.objects.filter(is_active=True).prefetch_related("categories")
    q = request.GET.get("q", "").strip()[:100]
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(website__icontains=q))
    cat = SupplierCategory.objects.filter(slug=request.GET.get("nhom", "")).first()
    if cat:
        qs = qs.filter(categories__in=cat.descendant_ids()).distinct()
    page = Paginator(qs, 24).get_page(request.GET.get("page"))
    groups = SupplierCategory.objects.filter(parent__isnull=True).prefetch_related("children")
    return render(request, "catalog/suppliers.html", {
        "page": page, "q": q, "cat": cat, "groups": groups, "items": [("Nhà cung cấp", None)],
        "filtered": bool(q or cat)})
