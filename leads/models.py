from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.db import models
from django.utils.deconstruct import deconstructible
import secrets
import os

from core.models import TimeStamped
from core.utils import validate_quote_attachment


@deconstructible
class PrivateStorage(FileSystemStorage):
    """Tệp khách tải lên: lưu ngoài MEDIA_ROOT, chỉ nhân viên đăng nhập mới tải được."""

    def __init__(self):
        super().__init__(location=settings.PRIVATE_MEDIA_ROOT, base_url=None)


def attachment_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"quotes/{secrets.token_hex(12)}{ext}"  # tên ngẫu nhiên, bỏ tên gốc


class Lead(TimeStamped):
    """Khách hàng tiềm năng, gom theo số điện thoại."""
    SOURCE = [("quote", "Yêu cầu báo giá"), ("contact", "Liên hệ"), ("consult", "Đăng ký tư vấn")]
    TYPES = [("personal", "Khách cá nhân"), ("architect", "Kiến trúc sư / thiết kế"),
             ("contractor", "Nhà thầu"), ("partner", "Đối tác")]
    name = models.CharField("Họ tên", max_length=120)
    phone = models.CharField("Số điện thoại", max_length=20, db_index=True)
    email = models.EmailField("Email", blank=True)
    customer_type = models.CharField("Nhóm khách", max_length=12, choices=TYPES, blank=True)
    source = models.CharField("Nguồn", max_length=10, choices=SOURCE, default="contact")
    notes = models.TextField("Ghi chú nội bộ", blank=True)
    zoho_lead_id = models.CharField("ID Lead trong Zoho CRM", max_length=40, blank=True, editable=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Khách hàng tiềm năng"
        verbose_name_plural = "Khách hàng tiềm năng"

    def __str__(self):
        return f"{self.name} – {self.phone}"


class ContactMessage(TimeStamped):
    STATUS = [("new", "Mới"), ("handled", "Đã xử lý")]
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="messages")
    subject = models.CharField("Chủ đề", max_length=200, blank=True)
    message = models.TextField("Nội dung")
    status = models.CharField(max_length=10, choices=STATUS, default="new", db_index=True)
    zoho_synced_at = models.DateTimeField("Đã đồng bộ Zoho lúc", null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Tin nhắn liên hệ"
        verbose_name_plural = "Tin nhắn liên hệ"

    def __str__(self):
        return f"{self.lead.name}: {self.subject or self.message[:40]}"


class QuoteRequest(TimeStamped):
    NEW, CONTACTING, SENT, WON, LOST = "new", "contacting", "quoted", "won", "lost"
    STATUS = [(NEW, "Mới"), (CONTACTING, "Đang liên hệ"), (SENT, "Đã gửi báo giá"),
              (WON, "Thành công"), (LOST, "Thất bại")]
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT, related_name="quotes")
    product = models.ForeignKey("catalog.Product", null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="quote_requests", verbose_name="Sản phẩm")
    product_text = models.CharField("Sản phẩm quan tâm (nhập tay)", max_length=250, blank=True)
    quantity = models.DecimalField("Số lượng", max_digits=12, decimal_places=2, null=True, blank=True)
    unit = models.CharField("Đơn vị tính", max_length=30, blank=True)
    province = models.CharField("Tỉnh/thành – khu vực công trình", max_length=120, blank=True)
    need_delivery = models.BooleanField("Cần vận chuyển", default=False)
    need_installation = models.BooleanField("Cần thi công", default=False)
    message = models.TextField("Nội dung yêu cầu", blank=True)
    attachment = models.FileField("Tệp đính kèm", upload_to=attachment_path, storage=PrivateStorage(),
                                  blank=True, validators=[validate_quote_attachment])
    status = models.CharField("Trạng thái", max_length=12, choices=STATUS, default=NEW, db_index=True)
    internal_note = models.TextField("Ghi chú nội bộ", blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    verbose_name="Người phụ trách")
    zoho_synced_at = models.DateTimeField("Đã đồng bộ Zoho lúc", null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Yêu cầu báo giá"
        verbose_name_plural = "Yêu cầu báo giá"
        indexes = [models.Index(fields=["status", "-created_at"])]

    def __str__(self):
        return f"BG-{self.pk} · {self.lead.name}"

    @property
    def product_label(self):
        return str(self.product) if self.product_id else self.product_text
