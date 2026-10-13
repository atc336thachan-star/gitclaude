from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import ContactMessage, Lead, QuoteRequest


@admin.register(QuoteRequest)
class QuoteRequestAdmin(admin.ModelAdmin):
    list_display = ["id", "lead", "phone", "product_label", "quantity", "unit", "province", "status",
                    "assigned_to", "created_at"]
    list_editable = ["status"]
    list_filter = ["status", "need_delivery", "need_installation", "created_at"]
    search_fields = ["lead__name", "lead__phone", "product_text", "product__name", "product__sku", "province"]
    list_select_related = ["lead", "product", "assigned_to"]
    date_hierarchy = "created_at"
    raw_id_fields = ["product"]
    readonly_fields = ["lead", "created_at", "updated_at", "attachment_link", "lead_contact"]
    exclude = ["attachment"]
    fieldsets = [
        ("Khách hàng", {"fields": ["lead", "lead_contact"]}),
        ("Yêu cầu", {"fields": ["product", "product_text", "quantity", "unit", "province", "need_delivery",
                                "need_installation", "message", "attachment_link"]}),
        ("Xử lý", {"fields": ["status", "assigned_to", "internal_note", "created_at", "updated_at"]}),
    ]
    actions = ["mark_contacting", "mark_quoted", "mark_won", "mark_lost"]

    @admin.display(description="SĐT")
    def phone(self, o):
        return o.lead.phone

    @admin.display(description="Liên hệ")
    def lead_contact(self, o):
        return format_html('<a href="tel:{}">{}</a> · {}', o.lead.phone, o.lead.phone, o.lead.email or "—")

    @admin.display(description="Tệp đính kèm")
    def attachment_link(self, o):
        if not o.attachment:
            return "—"
        return format_html('<a href="{}">Tải về</a>', reverse("leads:attachment", args=[o.pk]))

    def has_add_permission(self, request):  # yêu cầu chỉ đến từ form công khai
        return False

    def _set(self, request, qs, status):
        n = qs.update(status=status)
        self.message_user(request, f"Đã cập nhật {n} yêu cầu.")

    @admin.action(description="Đánh dấu: Đang liên hệ")
    def mark_contacting(self, request, qs): self._set(request, qs, "contacting")

    @admin.action(description="Đánh dấu: Đã gửi báo giá")
    def mark_quoted(self, request, qs): self._set(request, qs, "quoted")

    @admin.action(description="Đánh dấu: Thành công")
    def mark_won(self, request, qs): self._set(request, qs, "won")

    @admin.action(description="Đánh dấu: Thất bại")
    def mark_lost(self, request, qs): self._set(request, qs, "lost")


class QuoteInline(admin.TabularInline):
    model = QuoteRequest
    extra = 0
    fields = ["product_label", "status", "created_at"]
    readonly_fields = fields
    can_delete = False
    show_change_link = True

    def has_add_permission(self, *a, **k):
        return False


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ["name", "phone", "email", "customer_type", "source", "created_at"]
    list_filter = ["source", "customer_type", "created_at"]
    search_fields = ["name", "phone", "email"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [QuoteInline]


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ["lead", "subject", "status", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["lead__name", "lead__phone", "subject", "message"]
    list_editable = ["status"]
    list_select_related = ["lead"]
    readonly_fields = ["lead", "subject", "message", "created_at", "updated_at"]

    def has_add_permission(self, request):
        return False
