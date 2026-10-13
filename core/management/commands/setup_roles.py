from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

ROLES = {
    # Nhóm: {app_label: [model, ...]} -> add/change/delete/view; "view" cho model chỉ xem
    "Biên tập nội dung": {
        "full": {"catalog": ["category", "brand", "product", "productimage", "productspec"],
                 "content": ["articlecategory", "article", "project", "projectimage"]},
        "view": {},
    },
    "Kinh doanh": {
        "full": {},
        "change": {"leads": ["quoterequest", "contactmessage", "lead"]},
        "view": {"leads": ["quoterequest", "contactmessage", "lead"], "catalog": ["product", "category", "brand"]},
    },
    "Quản lý website": {  # biên tập + cài đặt doanh nghiệp + xem báo giá
        "full": {"catalog": ["category", "brand", "product", "productimage", "productspec"],
                 "content": ["articlecategory", "article", "project", "projectimage"]},
        "change": {"core": ["sitesetting"], "leads": ["quoterequest", "contactmessage", "lead"]},
        "view": {"core": ["sitesetting"], "leads": ["quoterequest", "contactmessage", "lead"]},
    },
}


class Command(BaseCommand):
    help = "Tạo/cập nhật các nhóm phân quyền (Biên tập nội dung, Kinh doanh, Quản lý website)."

    def handle(self, *args, **opts):
        for name, spec in ROLES.items():
            group, _ = Group.objects.get_or_create(name=name)
            codes = set()
            for kind, actions in (("full", ("add", "change", "delete", "view")), ("change", ("change",)), ("view", ("view",))):
                for app, models in spec.get(kind, {}).items():
                    for m in models:
                        for a in actions:
                            codes.add((app, f"{a}_{m}"))
            objs = [Permission.objects.get(content_type__app_label=app, codename=code) for app, code in codes]
            group.permissions.set(objs)
            self.stdout.write(f"{name}: {len(objs)} quyền")
