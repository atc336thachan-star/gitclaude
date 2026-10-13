"""Ghi đè cột "Image URL" trong zoho_export/items.csv bằng URL ảnh GỐC (đang công khai) của site cũ.

Dùng khi chưa có nơi lưu ảnh công khai riêng. Lưu ý: URL này sẽ hỏng khi site cũ tắt – nên chuyển ảnh sang
nơi bạn kiểm soát trước đó (Zoho Commerce tải ảnh về khi import, nên sau khi import xong ảnh nằm trên Zoho).

    python manage.py export_zoho_legacy_images
"""
import csv
import json
import urllib.request
from pathlib import Path
from urllib.parse import quote

from django.core.management.base import BaseCommand

from catalog.models import Category, Product

API = "https://cloud.synck.io.vn/api/u/products"
ORIGIN = "vatlieunoithat.gensi.vn"


def fetch_page(page):
    url = f"{API}?origin={ORIGIN}&limit=100&page={page}&sortBy=order&sortOrder=desc"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (migration)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["data"]


class Command(BaseCommand):
    help = "Điền Image URL gốc từ site cũ vào zoho_export/items.csv"

    def add_arguments(self, p):
        p.add_argument("--dir", default="zoho_export")

    def handle(self, *a, dir, **kw):
        d = Path(dir)
        thumb = {}
        page, total = 1, None
        while True:
            data = fetch_page(page)
            total = data["pagination"]["total"]
            for p in data["products"]:
                if p.get("thumbnail"):
                    thumb[p["_id"]] = quote(p["thumbnail"], safe=":/?&=%#+@,")
            if page * 100 >= total:
                break
            page += 1
        sku_to_url = {sku: thumb.get(lid, "") for sku, lid in Product.objects.values_list("sku", "legacy_id")}
        dup = {n for n in Category.objects.values_list("name", flat=True) if Category.objects.filter(name=n).count() > 1}

        path = d / "items.csv"
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
            cols = f.name and list(rows[0].keys())
        hit = 0
        for r in rows:
            url = sku_to_url.get(r["SKU"], "")
            r["Image URL"] = url
            hit += bool(url)
            if r["Category Name"] == "NỘI THẤT" and Product.objects.filter(sku=r["SKU"], category__legacy_id__isnull=False,
                                                                           category__parent__isnull=True,
                                                                           category__sort_order__gt=100).exists():
                r["Category Name"] = "NỘI THẤT (2)"  # khớp tên đã tạo trong Zoho
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        self.stdout.write(self.style.SUCCESS(
            f"{len(rows)} sản phẩm, {hit} có URL ảnh gốc. Danh mục trùng tên (Zoho có thể khớp nhầm): {sorted(dup)}"))
