import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from catalog.models import Brand, Category, Product
from content.models import Article, Project
from core.models import SiteSetting
from leads.models import Lead, QuoteRequest

TMP = tempfile.mkdtemp()


def png_bytes():
    b = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(b, "PNG")
    return b.getvalue()


@override_settings(MEDIA_ROOT=TMP, PRIVATE_MEDIA_ROOT=TMP, SECURE_SSL_REDIRECT=False)
class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSetting.load()
        cls.cat = Category.objects.create(name="Sàn gỗ")
        cls.brand = Brand.objects.create(name="Hãng A")
        cls.p1 = Product.objects.create(name="Sàn A", sku="A1", category=cls.cat, brand=cls.brand,
                                        price_type="fixed", price=100000, unit="m²", color="Nâu")
        cls.p2 = Product.objects.create(name="Sàn B", sku="B1", category=cls.cat, price_type="quote",
                                        price=999, color="Trắng")
        cls.p_hidden = Product.objects.create(name="Ẩn", sku="H1", category=cls.cat, is_active=False)

    def setUp(self):
        cache.clear()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP, ignore_errors=True)


class PublicPages(Base):
    def test_pages_ok(self):
        art = Article.objects.create(title="Bài", body="<p>x</p>", is_published=True)
        proj = Project.objects.create(title="CT", is_published=True)
        for url in ["/", "/san-pham/", self.cat.get_absolute_url(), self.p1.get_absolute_url(), "/bao-gia/",
                    "/lien-he/", "/tu-van/", "/ve-chung-toi/", "/tin-tuc/", art.get_absolute_url(),
                    "/cong-trinh/", proj.get_absolute_url(), "/nha-cung-cap/", "/sitemap.xml", "/robots.txt"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_404_and_hidden_product(self):
        self.assertEqual(self.client.get("/khong-co/").status_code, 404)
        self.assertEqual(self.client.get(self.p_hidden.get_absolute_url()).status_code, 404)

    def test_legacy_redirects(self):
        r = self.client.get("/dang-ky")
        self.assertEqual((r.status_code, r["Location"]), (301, "/lien-he/"))

    def test_quote_price_not_stored_and_not_shown(self):
        self.p2.refresh_from_db()
        self.assertIsNone(self.p2.price)
        r = self.client.get(self.p2.get_absolute_url())
        self.assertContains(r, "Liên hệ báo giá")

    def test_no_fake_offer_in_jsonld_for_quote_price(self):
        self.assertNotContains(self.client.get(self.p2.get_absolute_url()), '"offers"')
        self.assertContains(self.client.get(self.p1.get_absolute_url()), '"offers"')
        self.assertNotContains(self.client.get(self.p1.get_absolute_url()), "aggregateRating")

    def test_hidden_not_in_list_or_sitemap(self):
        self.assertNotContains(self.client.get("/san-pham/"), "H1")
        self.assertNotContains(self.client.get("/sitemap.xml"), self.p_hidden.get_absolute_url())

    def test_filter_sort_empty_state(self):
        r = self.client.get("/san-pham/", {"mau-sac": "Nâu"})
        self.assertContains(r, "Sàn A"); self.assertNotContains(r, "Sàn B")
        r = self.client.get("/san-pham/", {"thuong-hieu": "khong-ton-tai"})
        self.assertContains(r, "Không tìm thấy sản phẩm phù hợp")
        self.assertEqual(self.client.get("/san-pham/", {"sap-xep": "bậy", "gia-tu": "abc"}).status_code, 200)

    def test_html_sanitised(self):
        p = Product.objects.create(name="X", sku="X1", category=self.cat,
                                   description="<p>ok</p><script>alert(1)</script>")
        self.assertNotIn("<script>", p.description)


class QuoteFlow(Base):
    data = {"name": "Nguyễn A", "phone": "0988 123 456", "product_text": "Sàn A", "quantity": "20", "unit": "m²"}

    def test_success_saves_then_confirms(self):
        r = self.client.post("/bao-gia/", {**self.data, "product": self.p1.pk}, follow=True)
        self.assertEqual(QuoteRequest.objects.count(), 1)
        q = QuoteRequest.objects.get()
        self.assertEqual((q.lead.phone, q.status, q.product_id), ("0988123456", "new", self.p1.pk))
        self.assertContains(r, f"BG-{q.pk}")

    def test_done_page_without_submission_redirects(self):
        self.assertEqual(self.client.get("/bao-gia/da-gui/").status_code, 302)

    def test_validation_errors_nothing_saved(self):
        r = self.client.post("/bao-gia/", {**self.data, "phone": "123"})
        self.assertContains(r, "Số điện thoại không hợp lệ")
        r = self.client.post("/bao-gia/", {"name": "A", "phone": "0988123456"})
        self.assertContains(r, "Vui lòng cho biết")
        self.assertEqual(QuoteRequest.objects.count(), 0)

    def test_honeypot(self):
        self.client.post("/bao-gia/", {**self.data, "website": "http://spam"})
        self.assertEqual(QuoteRequest.objects.count(), 0)

    @override_settings(FORM_THROTTLE_LIMIT=2)
    def test_throttle(self):
        for _ in range(4):
            self.client.post("/bao-gia/", self.data)
        self.assertEqual(QuoteRequest.objects.count(), 2)

    def test_lead_dedup_by_phone(self):
        self.client.post("/bao-gia/", self.data)
        self.client.post("/bao-gia/", {**self.data, "name": "Tên mới"})
        self.assertEqual(Lead.objects.count(), 1)
        self.assertEqual(QuoteRequest.objects.count(), 2)

    def test_csrf_enforced(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        self.assertEqual(c.post("/bao-gia/", self.data).status_code, 403)

    def test_attachment_rules(self):
        ok = SimpleUploadedFile("a.png", png_bytes(), "image/png")
        self.client.post("/bao-gia/", {**self.data, "attachment": ok})
        self.assertEqual(QuoteRequest.objects.count(), 1)
        self.assertTrue(QuoteRequest.objects.get().attachment.name.startswith("quotes/"))
        for bad in (SimpleUploadedFile("x.exe", b"MZ", "application/octet-stream"),
                    SimpleUploadedFile("x.png", b"not an image", "image/png"),
                    SimpleUploadedFile("x.pdf", b"not pdf", "application/pdf")):
            r = self.client.post("/bao-gia/", {**self.data, "phone": "0911222333", "attachment": bad})
            self.assertEqual(r.status_code, 200)
        self.assertEqual(QuoteRequest.objects.count(), 1)

    def test_contact_form(self):
        r = self.client.post("/lien-he/gui/", {"name": "B", "phone": "0912345678", "message": "Xin tư vấn"}, follow=True)
        self.assertContains(r, "đã nhận được")
        self.assertEqual(Lead.objects.get().messages.count(), 1)
        r = self.client.post("/lien-he/gui/", {"name": "B", "phone": "xx", "message": ""})
        self.assertEqual(r.status_code, 400)


class AdminSecurity(Base):
    def setUp(self):
        super().setUp()
        call_command("setup_roles", verbosity=0)
        User = get_user_model()
        self.su = User.objects.create_superuser("root", "r@x.vn", "Sup3r-secret-pass")
        self.editor = User.objects.create_user("ed", password="Ed1tor-secret-pass", is_staff=True)
        self.editor.groups.add(Group.objects.get(name="Biên tập nội dung"))
        self.sales = User.objects.create_user("sa", password="Sal3s-secret-pass", is_staff=True)
        self.sales.groups.add(Group.objects.get(name="Kinh doanh"))
        self.q = QuoteRequest.objects.create(lead=Lead.objects.create(name="K", phone="0900000000"),
                                             attachment=SimpleUploadedFile("a.png", png_bytes()))

    def test_anonymous_blocked(self):
        for url in ["/quan-tri/", "/quan-tri/catalog/product/", "/quan-tri/leads/quoterequest/",
                    f"/tep-bao-gia/{self.q.pk}/"]:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertIn("login", r["Location"])

    def test_backend_permissions_by_role(self):
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get("/quan-tri/catalog/product/").status_code, 200)
        self.assertEqual(self.client.get("/quan-tri/leads/quoterequest/").status_code, 403)
        self.assertEqual(self.client.get(f"/tep-bao-gia/{self.q.pk}/").status_code, 404)
        self.client.force_login(self.sales)
        self.assertEqual(self.client.get("/quan-tri/leads/quoterequest/").status_code, 200)
        self.assertEqual(self.client.get("/quan-tri/catalog/product/add/").status_code, 403)
        self.assertEqual(self.client.get(f"/tep-bao-gia/{self.q.pk}/").status_code, 200)

    def test_quote_status_workflow(self):
        self.client.force_login(self.sales)
        r = self.client.post(f"/quan-tri/leads/quoterequest/{self.q.pk}/change/", {
            "product_text": "", "unit": "", "province": "", "message": "", "status": "contacting",
            "internal_note": "đã gọi", "assigned_to": ""})
        self.q.refresh_from_db()
        self.assertEqual(self.q.status, "contacting")

    def test_superuser_dashboard_and_crud(self):
        self.client.force_login(self.su)
        self.assertContains(self.client.get("/quan-tri/"), "Báo giá mới")
        r = self.client.post("/quan-tri/catalog/category/add/", {"name": "Mới", "sort_order": 0, "is_active": "on"})
        self.assertTrue(Category.objects.filter(name="Mới").exists())

    def test_password_not_plaintext(self):
        self.assertTrue(self.su.password.startswith(("pbkdf2_", "argon2", "bcrypt")))


class Seed(TestCase):
    def test_seed_flags_demo_and_clear(self):
        call_command("seed_demo", verbosity=0)
        self.assertFalse(Product.objects.filter(is_demo=False).exists())
        self.assertFalse(Product.objects.exclude(price_type="quote").exists())  # không bịa giá
        call_command("seed_demo", "--clear", verbosity=0)
        self.assertEqual(Product.objects.count(), 0)
