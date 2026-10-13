"""Xuất phần còn lại để chuyển sang Zoho Commerce: nhà cung cấp, bài viết, bảng ánh xạ URL cũ.

    python manage.py export_zoho_extra            # ghi vào zoho_export/
"""
import csv
import re
from pathlib import Path

from django.core.management.base import BaseCommand

from catalog.models import Product, Supplier
from content.models import Article
from core.models import Redirect


def plain(html, n=0):
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()
    return t[:n] if n else t


class Command(BaseCommand):
    help = "Xuất suppliers.csv, articles.csv, legacy_urls.csv cho việc chuyển sang Zoho Commerce"

    def add_arguments(self, parser):
        parser.add_argument("--out", default="zoho_export")

    def handle(self, *a, out, **kw):
        d = Path(out)
        d.mkdir(parents=True, exist_ok=True)

        def w(name, cols):
            f = open(d / name, "w", newline="", encoding="utf-8-sig")
            wr = csv.DictWriter(f, fieldnames=cols)
            wr.writeheader()
            return f, wr

        # Nhà cung cấp: dùng để nhập vào Zoho CRM (Vendors/Accounts) hoặc làm trang tĩnh; dữ liệu bên thứ ba, cần rà soát.
        f, wr = w("suppliers.csv", ["Name", "Groups", "Phone", "Email", "Website", "Address", "Logo File"])
        n = 0
        for s in Supplier.objects.filter(is_active=True).prefetch_related("categories"):
            wr.writerow({"Name": s.name, "Groups": " | ".join(c.name for c in s.categories.all()),
                         "Phone": s.phone, "Email": s.email, "Website": s.website, "Address": s.address,
                         "Logo File": s.logo.name if s.logo else ""})
            n += 1
        f.close()

        f, wr = w("articles.csv", ["Title", "Slug", "Category", "Published", "Excerpt", "Body (text)", "Cover File"])
        m = 0
        for a_ in Article.objects.select_related("category"):
            wr.writerow({"Title": a_.title, "Slug": a_.slug, "Category": a_.category.name if a_.category else "",
                         "Published": a_.published_at.date().isoformat() if a_.published_at else "",
                         "Excerpt": a_.excerpt, "Body (text)": plain(a_.body), "Cover File": a_.cover.name if a_.cover else ""})
            m += 1
        f.close()

        # URL cũ -> SKU. Sau khi import vào Zoho, tra URL mới theo SKU rồi tạo redirect 301 trong Zoho Commerce.
        f, wr = w("legacy_urls.csv", ["Old Path", "Type", "SKU / Key", "Name"])
        k = 0
        for p in Product.objects.filter(is_active=True).only("slug", "sku", "name").iterator():
            wr.writerow({"Old Path": f"/san-pham/{p.slug}", "Type": "product", "SKU / Key": p.sku, "Name": p.name})
            k += 1
        for r in Redirect.objects.all().iterator():
            wr.writerow({"Old Path": r.old_path, "Type": "category", "SKU / Key": r.new_path, "Name": ""})
            k += 1
        f.close()
        self.stdout.write(self.style.SUCCESS(f"Đã xuất {n} nhà cung cấp, {m} bài viết, {k} URL cũ vào {d.resolve()}"))
