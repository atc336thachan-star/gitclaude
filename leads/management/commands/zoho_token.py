"""Đổi mã Self Client (code) của Zoho thành refresh token và ghi vào .env.

    1. Điền ZOHO_CLIENT_ID và ZOHO_CLIENT_SECRET vào .env
    2. api-console.zoho.com -> Self Client -> Generate Code (hiệu lực 10 phút)
         scope: ZohoCRM.modules.leads.ALL,ZohoCRM.modules.notes.CREATE
    3. python manage.py zoho_token --code <mã vừa tạo>

Refresh token được ghi thẳng vào .env, không in ra màn hình. Mã chỉ dùng được một lần.
"""
import re
import urllib.parse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from leads import zoho


def write_env(path, key, value):
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    line = f"{key}={value}"
    if re.search(rf"^{key}=.*$", text, flags=re.M):
        text = re.sub(rf"^{key}=.*$", lambda m: line, text, flags=re.M)
    else:
        text = text.rstrip("\n") + ("\n" if text else "") + line + "\n"
    path.write_text(text, encoding="utf-8")


class Command(BaseCommand):
    help = "Đổi code Self Client Zoho thành refresh token (ghi vào .env)"

    def add_arguments(self, parser):
        parser.add_argument("--code", required=True, help="Mã tạo ở Self Client > Generate Code")

    def handle(self, *a, code, **kw):
        if not (settings.ZOHO_CLIENT_ID and settings.ZOHO_CLIENT_SECRET):
            raise CommandError("Hãy điền ZOHO_CLIENT_ID và ZOHO_CLIENT_SECRET vào .env trước.")
        q = urllib.parse.urlencode({
            "grant_type": "authorization_code", "client_id": settings.ZOHO_CLIENT_ID,
            "client_secret": settings.ZOHO_CLIENT_SECRET, "code": code.strip()})
        try:
            res = zoho._request("POST", f"{settings.ZOHO_ACCOUNTS_URL}/oauth/v2/token?{q}", data=b"")
        except zoho.ZohoError as e:
            raise CommandError(str(e))
        token = res.get("refresh_token")
        if not token:
            raise CommandError(
                f"Zoho không trả refresh token ({res.get('error', 'không rõ lỗi')}). Mã có thể đã hết hạn/đã dùng, "
                "hoặc sai data center: kiểm tra ZOHO_ACCOUNTS_URL (.com/.eu/.in...). Tạo lại mã và chạy lại.")
        write_env(settings.BASE_DIR / ".env", "ZOHO_REFRESH_TOKEN", token)
        self.stdout.write(self.style.SUCCESS(
            "Đã ghi ZOHO_REFRESH_TOKEN vào .env. Khởi động lại server rồi chạy: python manage.py sync_zoho --check"))
