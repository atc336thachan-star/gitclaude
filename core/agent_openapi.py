"""OpenAPI 3.0 cho API agent. Dán vào Zoho Zia Agents > Tools > Custom Tool (import OpenAPI)."""


def schema(server_url):
    product = {"type": "object", "properties": {
        "sku": {"type": "string"}, "name": {"type": "string"}, "category": {"type": "string"},
        "brand": {"type": "string"}, "short_description": {"type": "string"},
        "price_vnd": {"type": "integer", "nullable": True, "description": "null nếu sản phẩm liên hệ báo giá"},
        "price_type": {"type": "string", "enum": ["fixed", "reference", "quote"]},
        "price_note": {"type": "string"}, "unit": {"type": "string"}, "material": {"type": "string"},
        "color": {"type": "string"}, "size": {"type": "string"}, "thickness": {"type": "string"},
        "surface": {"type": "string"}, "function": {"type": "string"},
        "url": {"type": "string"}, "image_url": {"type": "string"}}}
    key = [{"ApiKeyAuth": []}]
    return {
        "openapi": "3.0.3",
        "info": {"title": "VatLieuNoiThat Agent API", "version": "1.0.0",
                 "description": "Tra cứu sản phẩm và tạo yêu cầu báo giá cho agent bán hàng."},
        "servers": [{"url": server_url}],
        "components": {"securitySchemes": {"ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"}},
                       "schemas": {"Product": product}},
        "paths": {
            "/api/agent/products/": {"get": {
                "operationId": "searchProducts", "security": key,
                "summary": "Tìm sản phẩm theo từ khóa, danh mục, thương hiệu, khoảng giá",
                "description": "Chỉ đề xuất sản phẩm có trong kết quả. price_vnd = null nghĩa là phải liên hệ báo giá.",
                "parameters": [
                    {"name": "q", "in": "query", "schema": {"type": "string"}, "description": "Từ khóa (tên, mã, chất liệu, màu...)"},
                    {"name": "category", "in": "query", "schema": {"type": "string"}, "description": "Tên hoặc slug danh mục"},
                    {"name": "brand", "in": "query", "schema": {"type": "string"}},
                    {"name": "price_min", "in": "query", "schema": {"type": "number"}},
                    {"name": "price_max", "in": "query", "schema": {"type": "number"}},
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 5, "maximum": 10}}],
                "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {
                    "type": "object", "properties": {
                        "total": {"type": "integer"}, "returned": {"type": "integer"},
                        "products": {"type": "array", "items": {"$ref": "#/components/schemas/Product"}}}}}}}}}},
            "/api/agent/products/{sku}/": {"get": {
                "operationId": "getProduct", "security": key,
                "summary": "Chi tiết sản phẩm theo mã SKU (mô tả, thông số, ứng dụng, hướng dẫn)",
                "parameters": [{"name": "sku", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "OK", "content": {"application/json": {
                    "schema": {"$ref": "#/components/schemas/Product"}}}},
                              "404": {"description": "Không tìm thấy"}}}},
            "/api/agent/quotes/": {"post": {
                "operationId": "createQuoteRequest", "security": key,
                "summary": "Ghi nhận yêu cầu báo giá của khách (nhân viên sẽ liên hệ, không phải báo giá chính thức)",
                "description": "Chỉ gọi khi đã có họ tên, số điện thoại và sản phẩm/nhu cầu. Chỉ báo đã ghi nhận khi trả 201.",
                "requestBody": {"required": True, "content": {"application/json": {"schema": {
                    "type": "object", "required": ["name", "phone"], "properties": {
                        "name": {"type": "string"}, "phone": {"type": "string", "description": "VD 0988123456"},
                        "email": {"type": "string"}, "product_sku": {"type": "string"},
                        "product_text": {"type": "string", "description": "Sản phẩm quan tâm nếu không có SKU"},
                        "quantity": {"type": "number"}, "unit": {"type": "string"},
                        "province": {"type": "string", "description": "Tỉnh/thành - khu vực công trình"},
                        "need_delivery": {"type": "boolean"}, "need_installation": {"type": "boolean"},
                        "message": {"type": "string"}}}}}},
                "responses": {"201": {"description": "Đã ghi nhận"}, "400": {"description": "Dữ liệu chưa hợp lệ"}}}},
        },
    }
