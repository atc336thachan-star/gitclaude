"""Nhập dữ liệu từ website cũ (API công khai mà vatlieunoithat.vn đang dùng) sang CSDL mới.

Chạy lại được nhiều lần (khớp theo legacy_id / slug, không tạo trùng). Ví dụ:
    python manage.py import_legacy                  # toàn bộ
    python manage.py import_legacy --limit 50       # thử 50 sản phẩm
    python manage.py import_legacy --no-images      # bỏ qua tải ảnh
    python manage.py import_legacy --only settings,categories
"""
import re
import json
import logging
import urllib.request
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify

from catalog.models import Category, Product, ProductImage, Supplier, SupplierCategory
from content.models import Article, ArticleCategory
from core.models import Redirect, SiteSetting
from core.utils import clean_html

log = logging.getLogger(__name__)
API = "https://cloud.synck.io.vn/api/u"
ORIGIN = "vatlieunoithat.gensi.vn"
UA = {"User-Agent": "Mozilla/5.0 (migration script)"}
PREFIX = re.compile(r"^\s*\d+\s*-\s*")


def get(url, binary=False, timeout=40, tries=3):
    url = quote(url, safe=":/?&=%#+@,")  # URL có khoảng trắng/ký tự đặc biệt
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                data = r.read()
            return data if binary else json.loads(data)
        except Exception as e:
            if i == tries - 1:
                log.warning("GET failed %s: %s", url[:120], e)
                return None


def api(path, **params):
    q = "&".join(f"{k}={v}" for k, v in {**params, "origin": ORIGIN}.items())
    j = get(f"{API}/{path}?{q}")
    return (j or {}).get("data")


def img_url(item):
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return item.get("url") or item.get("src") or item.get("thumbnail") or item.get("path")
    return None


class Command(BaseCommand):
    help = "Nhập dữ liệu từ vatlieunoithat.vn (cấu hình, danh mục, sản phẩm, ảnh, bài viết)."

    def add_arguments(self, p):
        p.add_argument("--limit", type=int, default=0, help="Chỉ nhập N sản phẩm đầu (thử nghiệm)")
        p.add_argument("--no-images", action="store_true")
        p.add_argument("--only", default="settings,categories,products,articles,suppliers")
        p.add_argument("--threads", type=int, default=8)

    def handle(self, *a, **o):
        self.opt = o
        parts = set(o["only"].split(","))
        if "settings" in parts:
            self.settings()
        if "categories" in parts:
            self.categories()
        if "products" in parts:
            self.products()
        if "articles" in parts:
            self.articles()
        if "suppliers" in parts:
            self.suppliers()
        self.stdout.write(self.style.SUCCESS("Hoàn tất."))

    # ---------- ảnh ----------
    def fetch_image(self, url):
        if not url or self.opt["no_images"]:
            return None
        return get(url, binary=True, timeout=60)

    # ---------- cấu hình ----------
    def settings(self):
        d = api("settings")
        if not d:
            self.stderr.write("Không đọc được settings"); return
        s = d["setting"]
        obj = SiteSetting.load()
        obj.company_name = s.get("companyName") or obj.company_name
        obj.address = (s.get("headquarters") or "").replace("  ", " ").strip() or obj.address
        phones = re.findall(r"0\d{9}", s.get("phone") or "")
        if phones:
            obj.hotline = phones[0]
            obj.zalo = phones[-1]
        obj.email = obj.email or s.get("email") or ""
        obj.tagline = (re.sub(r"<[^>]+>", "", s.get("descriptions") or "")[:190]) or obj.tagline
        fb = [x["link"] for x in s.get("socials", []) if x.get("link")]
        if fb:
            obj.facebook_url = fb[0]
        parts = []
        for key in ("homeDescriptions", "descriptionBusinessFieldFirst"):
            if s.get(key):
                parts.append(s[key])
        for pr in s.get("projects", []) or []:
            parts.append(f"<h3>{pr.get('title', '')}</h3>{pr.get('content', '')}")
        if s.get("titleBusinessFieldSecond") or s.get("descriptionBusinessFieldSecond"):
            parts.append(f"<h2>{s.get('titleBusinessFieldSecond', '')}</h2>{s.get('descriptionBusinessFieldSecond', '')}")
        for ft in s.get("featureds", []) or []:
            parts.append(f"<h3>{ft.get('title', '')}</h3>{ft.get('content', '')}")
        obj.about_html = "\n".join(parts)
        logo = self.fetch_image(s.get("logo"))
        if logo and not obj.logo:
            obj.logo.save("logo.webp", ContentFile(logo), save=False)
        obj.save()
        self.stdout.write("Đã nhập cấu hình doanh nghiệp (kiểm tra lại trong Admin).")

    # ---------- danh mục ----------
    def categories(self):
        d = api("products-collections", limit=500, order="order:asc")
        cols = d["collections"]
        by_id = {c["_id"]: c for c in cols}
        made = {}

        def ensure(c):
            if c["_id"] in made:
                return made[c["_id"]]
            parent = None
            pid = (c.get("parent") or {}).get("id")
            if pid and pid in by_id:
                parent = ensure(by_id[pid])
            name = PREFIX.sub("", c["name"]).strip() or c["name"]
            obj = Category.objects.filter(legacy_id=c["_id"]).first()
            if not obj:
                obj = Category(legacy_id=c["_id"], slug=None)
                base = c.get("slug") or slugify(name)
                if not Category.objects.filter(slug=base).exists():
                    obj.slug = base
            obj.name, obj.parent = name, parent
            obj.sort_order = int(c.get("order") or 0)
            obj.is_active = bool(c.get("isPublic", True)) and c.get("status", "active") == "active"
            obj.description = re.sub(r"<[^>]+>", "", c.get("description") or "")[:2000]
            obj.save()
            made[c["_id"]] = obj
            if c.get("urlNoDomain"):
                Redirect.objects.update_or_create(old_path=c["urlNoDomain"], defaults={"new_path": obj.get_absolute_url()})
            return obj

        for c in cols:
            ensure(c)
        self.cat_by_legacy = made
        self.stdout.write(f"Danh mục: {len(made)}")

    def _cats(self):
        return {c.legacy_id: c for c in Category.objects.exclude(legacy_id=None)}

    # ---------- sản phẩm ----------
    def products(self):
        cats = self._cats()
        misc, _ = Category.objects.get_or_create(slug="chua-phan-loai", defaults={"name": "Chưa phân loại", "sort_order": 9999})
        items, page = [], 1
        while True:
            d = api("products", limit=100, page=page, sortBy="order", sortOrder="desc")
            if not d or not d.get("products"):
                break
            items += d["products"]
            if len(items) >= d["pagination"]["total"] or (self.opt["limit"] and len(items) >= self.opt["limit"]):
                break
            page += 1
        if self.opt["limit"]:
            items = items[: self.opt["limit"]]
        self.stdout.write(f"Đọc được {len(items)} sản phẩm, đang tải chi tiết…")
        existing = set(Product.objects.exclude(legacy_id=None).values_list("legacy_id", flat=True))
        noimg = set(Product.objects.exclude(legacy_id=None).filter(images__isnull=True).values_list("legacy_id", flat=True))
        todo = [p for p in items if p["_id"] not in existing or p["_id"] in noimg]
        self.stdout.write(f"Cần nhập mới: {len(todo)} (đã có: {len(items) - len(todo)})")

        def work(p):
            det = api(f"products/{p['slug']}")
            det = (det or {}).get("product") or p
            urls = [img_url(p.get("thumbnail"))] + [img_url(i) for i in (det.get("images") or [])]
            urls = list(dict.fromkeys(u for u in urls if u))[:6]
            blobs = [self.fetch_image(u) for u in urls]
            return p, det, [b for b in blobs if b]

        done = 0
        with ThreadPoolExecutor(self.opt["threads"]) as ex:
            for p, det, blobs in ex.map(work, todo):
                try:
                    self.save_product(p, det, blobs, cats, misc)
                except Exception as e:
                    self.stderr.write(f"Lỗi {p.get('slug')}: {e}")
                done += 1
                if done % 100 == 0:
                    self.stdout.write(f"  {done}/{len(todo)}")
        self.stdout.write(f"Sản phẩm: tổng {Product.objects.exclude(legacy_id=None).count()}")

    def save_product(self, p, det, blobs, cats, misc):
        cat = next((cats[c["_id"]] for c in det.get("categories", p.get("categories", [])) if c.get("_id") in cats), misc)
        old = Product.objects.filter(legacy_id=p["_id"]).first()
        if old:  # đã nhập trước đó: chỉ bổ sung ảnh còn thiếu
            for i, b in enumerate(blobs):
                im = ProductImage(product=old, alt=old.name, sort_order=i)
                im.image.save("src.webp", ContentFile(b), save=False)
                im.save()
            return
        price = det.get("price") or 0
        slug = p["slug"] if not Product.objects.filter(slug=p["slug"]).exists() else None
        prod = Product(legacy_id=p["_id"], name=p["name"][:250], slug=slug, sku=f"VLNT-{p['_id'][-8:].upper()}",
                       category=cat, price_type="fixed" if price else "quote", price=Decimal(price) if price else None,
                       description=det.get("content") or "", is_active=det.get("status", "active") == "active",
                       is_featured=bool(det.get("showHome")), view_count=int(det.get("view") or 0))
        prod.save()
        for i, b in enumerate(blobs):
            im = ProductImage(product=prod, alt=prod.name, sort_order=i)
            im.image.save("src.webp", ContentFile(b), save=False)
            im.save()

    # ---------- bài viết ----------
    def articles(self):
        d = api("blogs", limit=200)
        n = 0
        for b in (d or {}).get("blogs", []):
            full = (api(f"blogs/{b['slug']}") or {}).get("blog") or b
            body = full.get("content") or full.get("descriptions") or ""
            junk = len(re.sub(r"<[^>]+>", "", body)) < 3 and not full.get("thumbnail")
            cat = None
            c = full.get("category")
            c = c[0] if isinstance(c, list) and c else c
            if isinstance(c, dict) and c.get("slug"):
                cat, _ = ArticleCategory.objects.get_or_create(slug=c["slug"], defaults={"name": c.get("title") or c["slug"]})
            a, created = Article.objects.get_or_create(slug=b["slug"], defaults={"title": full["title"][:250], "body": body})
            if created:
                a.category, a.is_published = cat, not junk and b["slug"] != "46456456"
                a.published_at = parse_datetime(full["createdAt"]) if full.get("createdAt") else None
                img = self.fetch_image(full.get("thumbnail"))
                if img:
                    a.cover.save("cover.webp", ContentFile(img), save=False)
                a.save()
                n += 1
        self.stdout.write(f"Bài viết mới: {n}")

    # ---------- nhà cung cấp ----------
    def suppliers(self):
        cd = api("categories", limit=500, type="partner") or {}
        cats = cd.get("categories", [])
        made = {}
        by_id = {c["_id"]: c for c in cats}

        def ensure(c):
            if c["_id"] in made:
                return made[c["_id"]]
            pid = (c.get("parent") or {}).get("id")
            parent = ensure(by_id[pid]) if pid and pid in by_id else None
            name = PREFIX.sub("", c["title"]).strip() or c["title"]
            obj = SupplierCategory.objects.filter(legacy_id=c["_id"]).first() or SupplierCategory(legacy_id=c["_id"])
            obj.name, obj.parent = name, parent
            obj.save()
            made[c["_id"]] = obj
            return obj

        for c in cats:
            ensure(c)
        d = api("partners", sortBy="order", sortOrder="asc", limit=1000) or {}
        partners = d.get("partners", [])
        existing = set(Supplier.objects.exclude(legacy_id=None).values_list("legacy_id", flat=True))
        todo = [p for p in partners if p["_id"] not in existing]
        self.stdout.write(f"Nhóm NCC: {len(made)}; nhà cung cấp: {len(partners)} (mới: {len(todo)})")

        def work(p):
            return p, self.fetch_image(p.get("logo"))

        with ThreadPoolExecutor(self.opt["threads"]) as ex:
            for p, logo in ex.map(work, todo):
                site = (p.get("website") or "").strip()
                if site and not site.startswith(("http://", "https://")):
                    site = "http://" + site
                sup = Supplier(legacy_id=p["_id"], name=p["name"][:250], phone=(p.get("phone") or "")[:80],
                               email=(p.get("email") or "")[:200], website=site[:300],
                               address=(p.get("address") or "")[:400], notes=p.get("notes") or "")
                if logo:
                    sup.logo.save("logo.webp", ContentFile(logo), save=False)
                sup.save()
                for c in p.get("category") or []:
                    if c.get("id") in made:
                        sup.categories.add(made[c["id"]])
        self.stdout.write(f"Nhà cung cấp: tổng {Supplier.objects.count()}")
