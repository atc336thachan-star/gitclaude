import re

from django import forms

from catalog.models import Product
from core.utils import validate_quote_attachment

from .models import Lead

PHONE_RE = re.compile(r"^(?:\+84|0)\d{9,10}$")


class HoneypotMixin(forms.Form):
    website = forms.CharField(required=False, label="", widget=forms.TextInput(
        attrs={"tabindex": "-1", "autocomplete": "off", "aria-hidden": "true"}))

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("spam")
        return ""


class PhoneMixin:
    def clean_phone(self):
        raw = re.sub(r"[\s.\-()]", "", self.cleaned_data["phone"])
        if not PHONE_RE.match(raw):
            raise forms.ValidationError("Số điện thoại không hợp lệ (VD: 0988123456).")
        return raw


class QuoteForm(PhoneMixin, HoneypotMixin):
    name = forms.CharField(label="Họ tên", max_length=120)
    phone = forms.CharField(label="Số điện thoại", max_length=20)
    email = forms.EmailField(label="Email (không bắt buộc)", required=False)
    customer_type = forms.ChoiceField(label="Bạn là", required=False, choices=[("", "— Chọn —")] + Lead.TYPES)
    product = forms.ModelChoiceField(label="Sản phẩm", queryset=Product.objects.filter(is_active=True),
                                     required=False, widget=forms.HiddenInput)
    product_text = forms.CharField(label="Sản phẩm quan tâm", max_length=250, required=False)
    quantity = forms.DecimalField(label="Số lượng", required=False, min_value=0, max_digits=12, decimal_places=2)
    unit = forms.CharField(label="Đơn vị tính", max_length=30, required=False)
    province = forms.CharField(label="Tỉnh/thành – khu vực công trình", max_length=120, required=False)
    need_delivery = forms.BooleanField(label="Cần vận chuyển", required=False)
    need_installation = forms.BooleanField(label="Cần thi công", required=False)
    message = forms.CharField(label="Nội dung yêu cầu", required=False, max_length=3000,
                              widget=forms.Textarea(attrs={"rows": 4}))
    attachment = forms.FileField(label="Đính kèm ảnh/PDF (tối đa 5 MB)", required=False,
                                 validators=[validate_quote_attachment])

    def clean(self):
        data = super().clean()
        if not data.get("product") and not data.get("product_text") and not data.get("message"):
            raise forms.ValidationError("Vui lòng cho biết sản phẩm quan tâm hoặc mô tả nhu cầu của bạn.")
        return data


class ContactForm(PhoneMixin, HoneypotMixin):
    name = forms.CharField(label="Họ tên", max_length=120)
    phone = forms.CharField(label="Số điện thoại", max_length=20)
    email = forms.EmailField(label="Email (không bắt buộc)", required=False)
    subject = forms.CharField(label="Chủ đề", max_length=200, required=False)
    message = forms.CharField(label="Nội dung", max_length=3000, widget=forms.Textarea(attrs={"rows": 5}))
    source = forms.ChoiceField(choices=[("contact", ""), ("consult", "")], required=False, widget=forms.HiddenInput)
