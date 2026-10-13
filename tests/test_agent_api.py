import json

from django.core.cache import cache
from django.test import override_settings

from leads.models import QuoteRequest

from .test_site import Base

KEY = {"HTTP_X_API_KEY": "k-test"}


@override_settings(AGENT_API_KEY="k-test", SECURE_SSL_REDIRECT=False)
class AgentApi(Base):
    def get(self, url, **kw):
        return self.client.get(url, **kw)

    def post(self, body, headers=KEY):
        return self.client.post("/api/agent/quotes/", json.dumps(body), content_type="application/json", **headers)

    def test_auth(self):
        self.assertEqual(self.get("/api/agent/products/").status_code, 401)
        self.assertEqual(self.get("/api/agent/products/", HTTP_X_API_KEY="sai").status_code, 401)
        self.assertEqual(self.get("/api/agent/products/", **KEY).status_code, 200)
        with override_settings(AGENT_API_KEY=""):
            self.assertEqual(self.get("/api/agent/products/", **KEY).status_code, 503)

    def test_search_hides_inactive_and_hides_fake_price(self):
        r = self.get("/api/agent/products/", **KEY).json()
        skus = {p["sku"]: p for p in r["products"]}
        self.assertEqual(set(skus), {"A1", "B1"})            # sản phẩm ẩn không lộ ra
        self.assertEqual(skus["A1"]["price_vnd"], 100000)
        self.assertIsNone(skus["B1"]["price_vnd"])            # giá "báo giá" không bao giờ trả ra
        self.assertEqual(skus["B1"]["price_note"], "Liên hệ báo giá")

    def test_filters(self):
        q = lambda s: self.get("/api/agent/products/" + s, **KEY).json()
        self.assertEqual([p["sku"] for p in q("?q=nâu")["products"]], ["A1"])
        self.assertEqual([p["sku"] for p in q("?brand=Hãng")["products"]], ["A1"])
        self.assertEqual(q("?price_min=200000")["total"], 0)
        self.assertEqual(q("?category=khong-co")["total"], 0)
        self.assertEqual(q("?limit=1")["returned"], 1)
        self.assertEqual(q("?limit=999")["returned"], 2)       # bị chặn ở MAX_LIMIT, chỉ có 2 sp hiển thị

    def test_detail(self):
        r = self.get("/api/agent/products/A1/", **KEY)
        self.assertEqual(r.json()["name"], "Sàn A")
        self.assertEqual(self.get("/api/agent/products/H1/", **KEY).status_code, 404)
        self.assertEqual(self.get("/api/agent/products/XX/", **KEY).status_code, 404)

    def test_create_quote_ok_no_csrf_and_requires_key(self):
        body = {"name": "An", "phone": "0988123456", "product_sku": "A1", "quantity": 20, "province": "Hà Nội",
                "need_delivery": True, "message": "Cần gấp"}
        self.assertEqual(self.post(body, headers={}).status_code, 401)
        r = self.post(body)
        self.assertEqual(r.status_code, 201)
        q = QuoteRequest.objects.get()
        self.assertEqual(r.json()["quote_id"], f"BG-{q.pk}")
        self.assertEqual(q.product, self.p1)
        self.assertTrue(q.need_delivery and not q.need_installation)
        self.assertTrue(q.message.startswith("[Zia Agent]"))
        self.assertEqual(q.lead.phone, "0988123456")

    def test_create_quote_validation(self):
        r = self.post({"name": "An", "phone": "123", "product_text": "x"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("phone", r.json()["fields"])
        self.assertEqual(self.post({"name": "An", "phone": "0988123456"}).status_code, 400)   # thiếu nhu cầu
        self.assertEqual(self.post({"name": "An", "phone": "0988123456", "product_sku": "H1"}).status_code, 404)
        self.assertEqual(QuoteRequest.objects.count(), 0)
        bad = self.client.post("/api/agent/quotes/", "không phải json", content_type="application/json", **KEY)
        self.assertEqual(bad.status_code, 400)

    def test_rate_limit(self):
        with override_settings(AGENT_API_RATE_PER_MIN=2):
            cache.clear()
            codes = [self.get("/api/agent/products/", **KEY).status_code for _ in range(3)]
        self.assertEqual(codes, [200, 200, 429])

    def test_openapi_public_no_secrets(self):
        r = self.get("/api/agent/openapi.json")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("k-test", r.content.decode())
        self.assertEqual(set(r.json()["paths"]), {"/api/agent/products/", "/api/agent/products/{sku}/", "/api/agent/quotes/"})
