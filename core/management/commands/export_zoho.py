"""Xuất catalog sang file CSV theo định dạng import của Zoho (Commerce / Inventory / Billing).

    python manage.py export_zoho                 # ghi vào zoho_export/
    python manage.py export_zoho --out D:\\tmp   # thư mục khác

Tạo: categories.csv, items.csv, images.csv, specs.csv.
Sản phẩm "liên hệ báo giá" xuất Selling Price = 0 và Status = Inactive để không bán nhầm trên storefront
(đổi thủ công khi có giá xác nhận). Ảnh nằm ở cột Image URL (đường dẫn tuyệt đối theo SITE_URL).
"""
import csv
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from catalog.models import Category, Product, ProductImage, ProductSpec

ITEM_COLS = ["Item Name", "SKU", "Description", "Selling Price", "Unit", "Item Type", "Product Type",
             "Category Name", "Brand", "Status", "Show in Storefront", "Image URL", "Source URL",
             "Price Note", "Material", "Color", "Size", "Thickness", "Surface", "Function"]


def plain(html, n=500):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()[:n]


def cat_path(cat):
    return " > ".join([c.name for c in cat.ancestors()] + [cat.name])


class Command(BaseCommand):
    help = "Xuất danh mục/sản phẩm sang CSV import cho Zoho"

    def add_arguments(self, parser):
        parser.add_argument("--out", default="zoho_export")

    def handle(self, *a, out, **kw):
        site = getattr(settings, "SITE_URL", "").rstrip("/")
        d = Path(out)
        d.mkdir(parents=True, exist_ok=True)

        def w(name, cols):
            f = open(d / name, "w", newline="", encoding="utf-8-sig")
            wr = csv.DictWriter(f, fieldnames=cols)
            wr.writeheader()
            return f, wr

        f, wr = w("categories.csv", ["Category Name", "Parent Category", "Full Path", "Description", "Status", "Sort Order"])
        n_cat = 0
        for c in Category.objects.select_related("parent").filter(is_active=True):
            wr.writerow({"Category Name": c.name, "Parent Category": c.parent.name if c.parent else "",
                         "Full Path": cat_path(c), "Description": c.description, "Status": "Active",
                         "Sort Order": c.sort_order})
            n_cat += 1
        f.close()

        f, wr = w("items.csv", ITEM_COLS)
        n_item = 0
        qs = (Product.objects.filter(is_active=True).select_related("category", "brand")
              .prefetch_related("images").order_by("id"))
        for p in qs.iterator(chunk_size=500):
            img = p.main_image
            priced = p.has_price
            wr.writerow({
                "Item Name": p.name, "SKU": p.sku,
                "Description": p.short_description or plain(p.description),
                "Selling Price": int(p.price) if priced else 0,
                "Unit": p.unit or "cái", "Item Type": "Sales", "Product Type": "goods",
                "Category Name": p.category.name, "Brand": p.brand.name if p.brand else "",
                "Status": "Active" if priced else "Inactive",
                "Show in Storefront": "true" if priced else "false",
                "Image URL": f"{site}{img.image.url}" if img else "",
                "Source URL": f"{site}/san-pham/{p.slug}/",
                "Price Note": "" if priced else "Liên hệ báo giá",
                "Material": p.material, "Color": p.color, "Size": p.size,
                "Thickness": p.thickness, "Surface": p.surface, "Function": p.function,
            })
            n_item += 1
        f.close()

        f, wr = w("images.csv", ["SKU", "Image URL", "Alt", "Sort Order"])
        for im in ProductImage.objects.select_related("product").order_by("product_id", "sort_order", "id").iterator():
            wr.writerow({"SKU": im.product.sku, "Image URL": f"{site}{im.image.url}", "Alt": im.alt,
                         "Sort Order": im.sort_order})
        f.close()

        f, wr = w("specs.csv", ["SKU", "Spec Name", "Spec Value"])
        for s in ProductSpec.objects.select_related("product").order_by("product_id", "sort_order").iterator():
            wr.writerow({"SKU": s.product.sku, "Spec Name": s.name, "Spec Value": s.value})
        f.close()

        self.stdout.write(self.style.SUCCESS(f"Đã xuất {n_cat} danh mục, {n_item} sản phẩm vào {d.resolve()}"))
