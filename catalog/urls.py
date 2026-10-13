from django.urls import path

from . import views

app_name = "catalog"
urlpatterns = [
    path("san-pham/", views.product_list, name="list"),
    path("nha-cung-cap/", views.supplier_list, name="suppliers"),
    path("danh-muc/<slug:slug>/", views.category_detail, name="category"),
    path("san-pham/<slug:slug>/", views.product_detail, name="product"),
]
