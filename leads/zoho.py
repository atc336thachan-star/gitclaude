"""Đồng bộ khách hàng tiềm năng / yêu cầu báo giá sang Zoho CRM (một chiều: Django -> Zoho).

Cấu hình qua .env (xem .env.example). Thiếu khóa thì tự tắt, web chạy bình thường.
Lỗi Zoho không bao giờ làm hỏng việc gửi form của khách: dữ liệu luôn lưu DB trước,
đẩy sang Zoho sau khi commit; bản ghi lỗi được thử lại bằng `python manage.py sync_zoho`.
"""
import json
import logging
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.db import transaction
from django.utils import timezone

log = logging.getLogger(__name__)

_token = {"value": "", "exp": 0.0}
_token_lock = threading.Lock()


class ZohoError(Exception):
    pass


def enabled():
    return all(getattr(settings, k, "") for k in ("ZOHO_CLIENT_ID", "ZOHO_CLIENT_SECRET", "ZOHO_REFRESH_TOKEN"))


def _request(method, url, *, data=None, headers=None, timeout=15):
    body = None
    if data is not None:
        body = data if isinstance(data, bytes) else json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raise ZohoError(f"HTTP {e.code} {method} {urllib.parse.urlsplit(url).path}: {e.read()[:300]!r}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ZohoError(f"{method} {urllib.parse.urlsplit(url).path}: {e}") from None


def _access_token():
    with _token_lock:
        if _token["value"] and time.time() < _token["exp"] - 60:
            return _token["value"]
        q = urllib.parse.urlencode({
            "refresh_token": settings.ZOHO_REFRESH_TOKEN, "client_id": settings.ZOHO_CLIENT_ID,
            "client_secret": settings.ZOHO_CLIENT_SECRET, "grant_type": "refresh_token"})
        res = _request("POST", f"{settings.ZOHO_ACCOUNTS_URL}/oauth/v2/token?{q}", data=b"")
        if "access_token" not in res:
            raise ZohoError(f"Không lấy được access token: {res.get('error', 'unknown')}")
        _token.update(value=res["access_token"], exp=time.time() + int(res.get("expires_in", 3600)))
        return _token["value"]


def _api(method, path, payload):
    return _request(method, f"{settings.ZOHO_API_DOMAIN}/crm/v6/{path}", data=payload, headers={
        "Authorization": f"Zoho-oauthtoken {_access_token()}", "Content-Type": "application/json"})


def _detail_id(res):
    row = (res.get("data") or [{}])[0]
    if row.get("status") != "success":
        raise ZohoError(f"Zoho từ chối: {row.get('code')} {row.get('message')}")
    return row["details"]["id"]


def upsert_lead(lead):
    """Tạo/cập nhật Lead trong CRM (khớp theo số điện thoại). Trả về ID Zoho."""
    rec = {"Last_Name": lead.name, "Phone": lead.phone, "Company": "Khách website",
           "Description": f"Nguồn website: {lead.get_source_display()}"}
    if lead.email:
        rec["Email"] = lead.email
    res = _api("POST", "Leads/upsert", {"data": [rec], "duplicate_check_fields": ["Phone"]})
    return _detail_id(res)


def add_note(zoho_lead_id, title, content):
    res = _api("POST", "Notes", {"data": [{
        "Note_Title": title[:120], "Note_Content": content[:30000],
        "Parent_Id": {"module": {"api_name": "Leads"}, "id": zoho_lead_id}}]})
    return _detail_id(res)


def quote_text(q):
    rows = [("Sản phẩm", q.product_label), ("Số lượng", f"{q.quantity or ''} {q.unit}".strip()),
            ("Khu vực", q.province), ("Cần vận chuyển", "Có" if q.need_delivery else "Không"),
            ("Cần thi công", "Có" if q.need_installation else "Không"), ("Nội dung", q.message),
            ("Mã trong web", f"BG-{q.pk}")]
    return "\n".join(f"{k}: {v}" for k, v in rows if v)


def sync_quote(q):
    """Đẩy một QuoteRequest. Trả về True nếu thành công; ghi lỗi vào log (không ném)."""
    return _sync(q.lead, f"Yêu cầu báo giá BG-{q.pk}", quote_text(q), q)


def sync_message(m):
    return _sync(m.lead, f"Liên hệ: {m.subject or 'Tin nhắn mới'}", m.message, m)


def _sync(lead, title, content, obj):
    if not enabled():
        return False
    try:
        if not lead.zoho_lead_id:
            lead.zoho_lead_id = upsert_lead(lead)
            type(lead).objects.filter(pk=lead.pk).update(zoho_lead_id=lead.zoho_lead_id)
        add_note(lead.zoho_lead_id, title, content)
    except ZohoError as e:
        log.warning("Zoho sync lỗi (%s #%s): %s", type(obj).__name__, obj.pk, e)
        return False
    type(obj).objects.filter(pk=obj.pk).update(zoho_synced_at=timezone.now())
    return True


def push_async(kind, pk):
    """Gọi sau khi form lưu DB xong: chạy nền, không chặn phản hồi cho khách."""
    if not enabled():
        return

    def run():
        from .models import ContactMessage, QuoteRequest
        model, fn = (QuoteRequest, sync_quote) if kind == "quote" else (ContactMessage, sync_message)
        obj = model.objects.select_related("lead").filter(pk=pk).first()
        if obj:
            fn(obj)

    transaction.on_commit(lambda: threading.Thread(target=run, daemon=True).start())
