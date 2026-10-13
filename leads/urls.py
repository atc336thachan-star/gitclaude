from django.urls import path

from . import views

app_name = "leads"
urlpatterns = [
    path("bao-gia/", views.quote, name="quote"),
    path("bao-gia/da-gui/", views.quote_done, name="quote_done"),
    path("lien-he/gui/", views.contact_submit, name="contact_submit"),
    path("tep-bao-gia/<int:pk>/", views.download_attachment, name="attachment"),
]
