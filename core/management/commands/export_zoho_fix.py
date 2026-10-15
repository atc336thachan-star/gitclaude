"""Thêm cột "Category URL" (slug danh mục đã tạo trên Zoho) và "Product Handle" (slug sản phẩm) vào items.csv,
rồi chia lại thành items_part1..N.csv (mặc định 1.000 dòng/file, file 1 ưu tiên 188 sản phẩm có giá).

Slug danh mục tính giống lúc tạo trên Zoho: bỏ dấu, Đ→D, trùng thì thêm hậu tố -2.

    python manage.py export_zoho_fix
"""
import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from catalog.models import Category, Product


def zoho_category_urls():
    cats = list(Category.objects.filter(is_active=True))
    by_id = {c.pk: c for c in cats}

    def depth(c):
        d = 0
        while c.parent_id:
            c = by_id[c.parent_id]
            d += 1
        return d

    used, out = set(), {}
    for c in sorted(cats, key=lambda c: (depth(c), c.parent_id or 0, c.sort_order, c.name)):
        base = slugify(c.name.replace("Đ", "D").replace("đ", "d")) or f"dm-{c.pk}"
        u, n = base, 2
        while u in used:
            u, n = f"{base}-{n}", n + 1
        used.add(u)
        out[c.pk] = u
    return out


class Command(BaseCommand):
    help = "Thêm Category URL / Product Handle vào items.csv và chia file import"

    def add_arguments(self, p):
        p.add_argument("--dir", default="zoho_export")
        p.add_argument("--size", type=int, default=1000)

    def handle(self, *a, dir, size, **kw):
        d = Path(dir)
        cat_url = zoho_category_urls()
        prod = {sku: (cid, slug) for sku, cid, slug in Product.objects.values_list("sku", "category_id", "slug")}
        with open(d / "items.csv", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        extra = ["Category URL", "Product Handle", "Hide Price", "Add To Quote", "Hide Add To Cart"]
        cols = [c for c in rows[0].keys() if c not in extra] + extra
        missing = 0
        for r in rows:
            cid, slug = prod[r["SKU"]]
            r["Category URL"] = cat_url.get(cid, "")
            r["Product Handle"] = slug
            missing += not r["Category URL"]
            priced = r["Selling Price"] not in ("", "0")
            # Sản phẩm "liên hệ báo giá": hiển thị trên cửa hàng, ẩn giá + nút mua, hiện nút Yêu cầu báo giá.
            r["Status"] = "Active"
            r["Show in Storefront"] = "true"
            r["Hide Price"] = "false" if priced else "true"
            r["Add To Quote"] = "false" if priced else "true"
            r["Hide Add To Cart"] = "false" if priced else "true"
        with open(d / "items.csv", "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        # Định dạng đã được Zoho chấp nhận khi import thử (20/20 dòng): bỏ Item Type/Product Type/Status/Category Name,
        # Show in Storefront = YES/NO, UTF-8 không BOM.
        cols = ["Item Name", "Product Handle", "Description", "Brand", "Selling Price", "SKU", "Category URL",
                "Show in Storefront", "Hide Add To Cart", "Add To Quote", "Hide Price", "Image URL", "Unit"]
        # Zoho bắt buộc Item Name duy nhất: bản trùng đầu tiên giữ nguyên, các bản sau thêm " (2)", " (3)"...
        seen = {}
        # Ảnh đã tải về, đổi sang JPG và đặt trên jsDelivr (nhánh "images" của repo): Zoho không tải được webp / URL có "?...".
        have = {p.stem for p in Path("zoho_images").glob("*.jpg")} if Path("zoho_images").exists() else set()
        for r in rows:
            r["Image URL"] = (f"https://cdn.jsdelivr.net/gh/atc336thachan-star/gitclaude@images/zoho_images/{r['SKU']}.jpg"
                              if r["SKU"] in have else "")
            r["Show in Storefront"] = "YES"
            k = r["Item Name"].strip().lower()
            seen[k] = seen.get(k, 0) + 1
            if seen[k] > 1:
                r["Item Name"] = f'{r["Item Name"].strip()} ({seen[k]})'
        # Bỏ 20 sản phẩm đã import thử để tránh báo lỗi "already exists"
        test = d / "items_test.csv"
        if test.exists():
            with open(test, encoding="utf-8", newline="") as f:
                done = {r["SKU"] for r in csv.DictReader(f)}
            rows = [r for r in rows if r["SKU"] not in done]
        act = [r for r in rows if r["Selling Price"] not in ("", "0")]  # có giá: đưa vào file 1 để thử trước
        rest = [r for r in rows if r["Selling Price"] in ("", "0")]
        first = act + rest[: max(0, size - len(act))]
        rest = rest[max(0, size - len(act)):]
        parts = [first] + [rest[i:i + size] for i in range(0, len(rest), size)]
        for old in d.glob("items_part*.csv"):
            old.unlink()
        for i, part in enumerate(parts, 1):
            with open(d / f"items_part{i}.csv", "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
                w.writeheader()
                w.writerows(part)
        self.stdout.write(self.style.SUCCESS(
            f"{len(rows)} sản phẩm → {len(parts)} file; thiếu Category URL: {missing}"))
