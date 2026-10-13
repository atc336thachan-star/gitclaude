import io
import logging
import secrets

import bleach
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

log = logging.getLogger(__name__)

ALLOWED_TAGS = ["p", "br", "strong", "b", "em", "i", "u", "ul", "ol", "li", "h2", "h3", "h4",
                "blockquote", "a", "table", "thead", "tbody", "tr", "th", "td", "img", "figure", "figcaption"]
ALLOWED_ATTRS = {"a": ["href", "title", "rel"], "img": ["src", "alt", "width", "height", "loading"]}


def clean_html(value: str) -> str:
    """Làm sạch HTML nhập từ admin trước khi lưu (chống XSS lưu trữ)."""
    return bleach.clean(value or "", tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS,
                        protocols=["http", "https", "mailto", "tel"], strip=True)


def optimize_image(field_file, max_side=1600, quality=82):
    """Đổi ảnh upload sang WebP, giới hạn kích thước. Trả về (ContentFile, (w, h)) hoặc (None, None)."""
    try:
        field_file.seek(0)
        img = Image.open(field_file)
        img = ImageOps.exif_transpose(img)
        img.thumbnail((max_side, max_side))
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, "WEBP", quality=quality, method=4)
        return ContentFile(buf.getvalue(), name=f"{secrets.token_hex(8)}.webp"), img.size
    except Exception:  # ảnh hỏng / không hỗ trợ
        log.warning("optimize_image failed", exc_info=True)
        return None, None


def validate_quote_attachment(f):
    """Chỉ nhận JPG/PNG/WebP (xác minh bằng Pillow) hoặc PDF (magic bytes), tối đa N MB."""
    limit = settings.QUOTE_ATTACHMENT_MAX_MB * 1024 * 1024
    if f.size > limit:
        raise ValidationError(f"Tệp quá lớn (tối đa {settings.QUOTE_ATTACHMENT_MAX_MB} MB).")
    name = f.name.lower()
    f.seek(0)
    head = f.read(8)
    f.seek(0)
    if name.endswith(".pdf"):
        if not head.startswith(b"%PDF-"):
            raise ValidationError("Tệp PDF không hợp lệ.")
        return
    if name.endswith((".jpg", ".jpeg", ".png", ".webp")):
        try:
            Image.open(f).verify()
        except Exception:
            raise ValidationError("Tệp ảnh không hợp lệ hoặc bị hỏng.")
        finally:
            f.seek(0)
        return
    raise ValidationError("Chỉ chấp nhận ảnh (JPG, PNG, WebP) hoặc PDF.")


def client_ip(request):
    if settings.TRUST_X_FORWARDED_FOR:
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if xff:
            return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")
