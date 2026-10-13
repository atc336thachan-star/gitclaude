"""Thử lại đồng bộ Zoho CRM cho các yêu cầu báo giá / liên hệ chưa đồng bộ.

    python manage.py sync_zoho            # đồng bộ các bản ghi còn thiếu
    python manage.py sync_zoho --check    # chỉ kiểm tra cấu hình + kết nối (lấy access token)
"""
from django.core.management.base import BaseCommand, CommandError

from leads import zoho
from leads.models import ContactMessage, QuoteRequest


class Command(BaseCommand):
    help = "Đồng bộ lead/báo giá chưa gửi sang Zoho CRM"

    def add_arguments(self, parser):
        parser.add_argument("--check", action="store_true")

    def handle(self, *a, check, **kw):
        if not zoho.enabled():
            raise CommandError("Chưa cấu hình ZOHO_CLIENT_ID / ZOHO_CLIENT_SECRET / ZOHO_REFRESH_TOKEN trong .env")
        if check:
            try:
                zoho._access_token()
            except zoho.ZohoError as e:
                raise CommandError(str(e))
            self.stdout.write(self.style.SUCCESS("Kết nối Zoho OK (đã lấy access token)."))
            return
        ok = bad = 0
        for q in QuoteRequest.objects.filter(zoho_synced_at__isnull=True).select_related("lead").order_by("id"):
            ok, bad = (ok + 1, bad) if zoho.sync_quote(q) else (ok, bad + 1)
        for m in ContactMessage.objects.filter(zoho_synced_at__isnull=True).select_related("lead").order_by("id"):
            ok, bad = (ok + 1, bad) if zoho.sync_message(m) else (ok, bad + 1)
        self.stdout.write(f"Đồng bộ thành công {ok}, lỗi {bad}.")
