from django.http import HttpResponsePermanentRedirect

# URL cũ của vatlieunoithat.vn -> URL mới (301). Các URL còn lại lấy từ bảng core.Redirect (nạp bởi import_legacy).
LEGACY = {
    "/gioi-thieu": "/ve-chung-toi/",
    "/dang-ky": "/lien-he/",
    "/nha-cung-cap-portal/dang-nhap": "/lien-he/",
}


class LegacyRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path.rstrip("/") or "/"
        if path in LEGACY:
            return HttpResponsePermanentRedirect(LEGACY[path])
        response = self.get_response(request)
        if response.status_code == 404:
            from .models import Redirect
            r = Redirect.objects.filter(old_path__in=[request.path, path]).first()
            if r:
                return HttpResponsePermanentRedirect(r.new_path)
        return response
