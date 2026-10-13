"""API JSON cho agent bán hàng (Zoho Zia Agents) gọi vào web.

    GET  /api/agent/products/?q=&category=&brand=&price_min=&price_max=&limit=   tìm sản phẩm
    GET  /api/agent/products/<sku>/                                              chi tiết sản phẩm
    POST /api/agent/quotes/                                                      tạo yêu cầu báo giá
    GET  /api/agent/openapi.json                                                 schema (công khai, không chứa bí mật)

Xác thực: header `X-API-Key` khớp AGENT_API_KEY trong .env (để trống = API tắt, trả 503).
Chỉ trả dữ liệu đã công khai trên web (sản phẩm đang hiển thị); giá chỉ có khi sản phẩm có giá niêm yết/tham khảo.
"""
import hmac
import json
import re
import time
from decimal import Decimal, InvalidOperation
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from catalog.models import Category, Product
from leads import zoho
from leads.forms import QuoteForm
from leads.models import QuoteRequest
from leads.views import _get_lead

MAX_LIMIT = 10
PRICE_NOTE = {
    Product.PRICE_FIXED: "Giá niêm yết, có thể thay đổi theo số lượng và thời điểm",
    Product.PRICE_REF: "Giá tham khảo, cần nhân viên xác nhận",
    Product.PRICE_QUOTE: "Liên hệ báo giá",
}


def _err(msg, status):
    return JsonResponse({"error": msg}, status=status, json_dumps_params={"ensure_ascii": False})


def _ok(data, status=200):
    return JsonResponse(data, status=status, json_dumps_params={"ensure_ascii": False})


def api_key_required(view):
    @wraps(view)
    def wrapper(request, *a, **kw):
        key = getattr(settings, "AGENT_API_KEY", "")
        if not key:
            return _err("API chưa được bật (thiếu AGENT_API_KEY).", 503)
        sent = request.headers.get("X-API-Key", "")
        if not hmac.compare_digest(sent.encode(), key.encode()):
            return _err("Sai hoặc thiếu API key.", 401)
        bucket = f"agentapi:{int(time.time() // 60)}"
        cache.add(bucket, 0, 120)
        if cache.incr(bucket) > getattr(settings, "AGENT_API_RATE_PER_MIN", 60):
            return _err("Quá nhiều yêu cầu, thử lại sau.", 429)
        return view(request, *a, **kw)
    return wrapper


def _plain(html, n=800):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()[:n]


def _abs(path):
    return f"{settings.SITE_URL}{path}"


def _product(p, detail=False):
    img = p.main_image
    cat = " > ".join([c.name for c in p.category.ancestors()] + [p.category.name])
    d = {
        "sku": p.sku, "name": p.name, "category": cat, "brand": p.brand.name if p.brand else "",
        "short_description": p.short_description,
        "price_vnd": int(p.price) if p.has_price else None,
        "price_type": p.price_type, "price_note": PRICE_NOTE.get(p.price_type, ""),
        "unit": p.unit, "material": p.material, "color": p.color, "size": p.size,
        "thickness": p.thickness, "surface": p.surface, "function": p.function,
        "url": _abs(f"/san-pham/{p.slug}/"), "image_url": _abs(img.image.url) if img else "",
    }
    if detail:
        d["description"] = _plain(p.description)
        d["applications"] = _plain(p.applications)
        d["usage_guide"] = _plain(p.usage_guide)
        d["specs"] = [{"name": s.name, "value": s.value} for s in p.specs.all()]
        d["images"] = [_abs(i.image.url) for i in p.images.all()[:6]]
    return d


def _dec(v):
    try:
        return Decimal(v) if v not in (None, "") else None
    except InvalidOperation:
        return None


def _qs():
    return (Product.objects.filter(is_active=True, category__is_active=True)
            .select_related("category", "brand").prefetch_related("images"))


@require_GET
@api_key_required
def products(request):
    g = request.GET
    qs = _qs()
    for term in g.get("q", "").strip()[:100].split()[:6]:   # mọi từ khóa phải khớp
        qs = qs.filter(Q(name__icontains=term) | Q(sku__icontains=term) | Q(short_description__icontains=term)
                       | Q(material__icontains=term) | Q(color__icontains=term) | Q(category__name__icontains=term))
    if g.get("category"):
        c = Category.objects.filter(Q(slug=g["category"]) | Q(name__iexact=g["category"]), is_active=True).first()
        qs = qs.filter(category_id__in=c.descendant_ids()) if c else qs.none()
    if g.get("brand"):
        qs = qs.filter(brand__name__icontains=g["brand"][:80])
    lo, hi = _dec(g.get("price_min")), _dec(g.get("price_max"))
    if lo is not None:
        qs = qs.filter(price__gte=lo)
    if hi is not None:
        qs = qs.filter(price__lte=hi)
    try:
        limit = max(1, min(int(g.get("limit", 5)), MAX_LIMIT))
    except ValueError:
        limit = 5
    total = qs.count()
    items = [_product(p) for p in qs.order_by("-is_featured", "-updated_at", "id")[:limit]]
    return _ok({"total": total, "returned": len(items), "products": items})


@require_GET
@api_key_required
def product_detail(request, sku):
    p = _qs().prefetch_related("specs").filter(sku=sku).first()
    if not p:
        return _err("Không tìm thấy sản phẩm.", 404)
    return _ok(_product(p, detail=True))


@csrf_exempt
@require_POST
@api_key_required
def create_quote(request):
    try:
        body = json.loads(request.body or b"{}")
        assert isinstance(body, dict)
    except (ValueError, AssertionError):
        return _err("Body phải là JSON object.", 400)
    data = {k: body.get(k) for k in ("name", "phone", "email", "customer_type", "product_text", "unit",
                                    "province", "message", "quantity") if body.get(k) not in (None, "")}
    data["need_delivery"] = "on" if body.get("need_delivery") else ""
    data["need_installation"] = "on" if body.get("need_installation") else ""
    sku = str(body.get("product_sku") or "").strip()
    if sku:
        p = _qs().filter(sku=sku).first()
        if not p:
            return _err(f"Không tìm thấy sản phẩm có mã {sku}.", 404)
        data["product"] = p.pk
        data.setdefault("product_text", p.name)
        data.setdefault("unit", p.unit)
    form = QuoteForm(data)
    if not form.is_valid():
        return _ok({"error": "Dữ liệu chưa hợp lệ.", "fields": {k: v[0] for k, v in form.errors.items()}}, 400)
    d = form.cleaned_data
    with transaction.atomic():
        lead = _get_lead(d, "quote")
        q = QuoteRequest.objects.create(
            lead=lead, product=d.get("product"), product_text=d.get("product_text", ""), quantity=d.get("quantity"),
            unit=d.get("unit", ""), province=d.get("province", ""), need_delivery=d["need_delivery"],
            need_installation=d["need_installation"], message=("[Zia Agent] " + d.get("message", "")).strip())
        zoho.push_async("quote", q.pk)
    return _ok({"ok": True, "quote_id": f"BG-{q.pk}",
                "message": "Đã ghi nhận yêu cầu báo giá. Nhân viên sẽ liên hệ xác nhận, chưa phải báo giá chính thức."}, 201)


@require_GET
def openapi(request):
    from .agent_openapi import schema
    return _ok(schema(settings.SITE_URL))
