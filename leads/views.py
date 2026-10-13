import logging

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from catalog.models import Product
from core.utils import client_ip

from . import zoho
from .forms import ContactForm, QuoteForm
from .models import ContactMessage, Lead, QuoteRequest

log = logging.getLogger(__name__)


def _throttled(request, scope):
    """Giới hạn lượt gửi form theo IP (cache). Trả True nếu vượt ngưỡng."""
    key = f"throttle:{scope}:{client_ip(request)}"
    cache.add(key, 0, settings.FORM_THROTTLE_WINDOW)
    try:
        n = cache.incr(key)
    except ValueError:
        cache.set(key, 1, settings.FORM_THROTTLE_WINDOW)
        n = 1
    return n > settings.FORM_THROTTLE_LIMIT


def _get_lead(data, source):
    lead = Lead.objects.filter(phone=data["phone"]).first()
    if lead:
        lead.name = data["name"] or lead.name
        lead.email = data.get("email") or lead.email
        lead.customer_type = data.get("customer_type") or lead.customer_type
        lead.save()
        return lead
    return Lead.objects.create(name=data["name"], phone=data["phone"], email=data.get("email", ""),
                               customer_type=data.get("customer_type", ""), source=source)


@require_http_methods(["GET", "POST"])
def quote(request):
    initial = {}
    slug = request.GET.get("san-pham")
    product = Product.objects.filter(slug=slug, is_active=True).select_related("category").first() if slug else None
    if product:
        initial = {"product": product.pk, "product_text": product.name, "unit": product.unit}
    if request.method == "POST":
        form = QuoteForm(request.POST, request.FILES)
        if _throttled(request, "quote"):
            form.add_error(None, "Bạn gửi quá nhiều yêu cầu trong thời gian ngắn. Vui lòng thử lại sau ít phút hoặc gọi hotline.")
        elif form.is_valid():
            d = form.cleaned_data
            try:
                with transaction.atomic():
                    lead = _get_lead(d, "quote")
                    q = QuoteRequest.objects.create(
                        lead=lead, product=d.get("product"), product_text=d.get("product_text", ""),
                        quantity=d.get("quantity"), unit=d.get("unit", ""), province=d.get("province", ""),
                        need_delivery=d["need_delivery"], need_installation=d["need_installation"],
                        message=d.get("message", ""), attachment=d.get("attachment") or "")
                    zoho.push_async("quote", q.pk)
            except Exception:
                log.exception("Không lưu được yêu cầu báo giá")
                form.add_error(None, "Hệ thống chưa lưu được yêu cầu của bạn. Vui lòng thử lại hoặc gọi hotline.")
            else:
                log.info("Quote request created id=%s lead=%s", q.pk, lead.pk)
                request.session["quote_done"] = q.pk
                return redirect("leads:quote_done")   # PRG: chỉ báo thành công sau khi đã lưu DB
    else:
        form = QuoteForm(initial=initial)
    return render(request, "leads/quote.html", {"form": form, "product": product, "items": [("Yêu cầu báo giá", None)]})


def quote_done(request):
    pk = request.session.pop("quote_done", None)
    if not pk:
        return redirect("leads:quote")
    return render(request, "leads/quote_done.html", {"quote_id": pk})


@require_http_methods(["POST"])
def contact_submit(request):
    """Xử lý form liên hệ/tư vấn (trang chủ + trang liên hệ)."""
    form = ContactForm(request.POST)
    if _throttled(request, "contact"):
        form.add_error(None, "Bạn gửi quá nhiều tin nhắn trong thời gian ngắn. Vui lòng thử lại sau.")
    elif form.is_valid():
        d = form.cleaned_data
        try:
            with transaction.atomic():
                lead = _get_lead(d, d.get("source") or "contact")
                m = ContactMessage.objects.create(lead=lead, subject=d.get("subject", ""), message=d["message"])
                zoho.push_async("message", m.pk)
        except Exception:
            log.exception("Không lưu được liên hệ")
            form.add_error(None, "Hệ thống chưa lưu được tin nhắn. Vui lòng thử lại hoặc gọi hotline.")
        else:
            request.session["contact_done"] = True
            return redirect("core:contact")
    return render(request, "core/contact.html", {"form": form, "items": [("Liên hệ", None)]}, status=400 if form.errors else 200)


@staff_member_required
def download_attachment(request, pk):
    """Tệp đính kèm báo giá chỉ cho nhân viên có quyền xem QuoteRequest."""
    if not request.user.has_perm("leads.view_quoterequest"):
        raise Http404
    q = get_object_or_404(QuoteRequest, pk=pk)
    if not q.attachment:
        raise Http404
    resp = FileResponse(q.attachment.open("rb"), as_attachment=True)
    resp["X-Content-Type-Options"] = "nosniff"
    return resp
