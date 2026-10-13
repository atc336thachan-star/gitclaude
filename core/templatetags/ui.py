from pathlib import Path

from django import template
from django.conf import settings
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()
_ICON_DIR = Path(settings.BASE_DIR) / "static" / "icons"
_cache = {}


@register.simple_tag
def icon(name, size=20, cls=""):
    """Inline SVG Lucide (static/icons/<name>.svg)."""
    key = (name, size, cls)
    if key not in _cache or settings.DEBUG:
        p = _ICON_DIR / f"{name}.svg"
        if not p.exists():
            return ""
        svg = p.read_text(encoding="utf8")
        inner = svg[svg.index(">", svg.index("<svg")) + 1: svg.rindex("</svg>")]
        _cache[key] = format_html(
            '<svg class="icon {}" xmlns="http://www.w3.org/2000/svg" width="{}" height="{}" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            'aria-hidden="true" focusable="false">{}</svg>', cls, size, size, mark_safe(inner))
    return _cache[key]


@register.filter
def vnd(value):
    try:
        return f"{int(value):,}".replace(",", ".") + " ₫"
    except (TypeError, ValueError):
        return ""


@register.simple_tag
def qs(request, **kw):
    """Giữ query-string hiện tại, ghi đè/xóa khóa (giá trị rỗng = xóa). Đổi bộ lọc thì reset trang."""
    q = request.GET.copy()
    for k, v in kw.items():
        if v in ("", None):
            q.pop(k, None)
        else:
            q[k] = v
    if "page" not in kw:
        q.pop("page", None)
    s = q.urlencode()
    return "?" + s if s else "?"
