from django.urls import path

from . import views

app_name = "content"
urlpatterns = [
    path("tin-tuc/", views.article_list, name="articles"),
    path("tin-tuc/chuyen-muc/<slug:cat>/", views.article_list, name="article_category"),
    path("tin-tuc/<slug:slug>/", views.article_detail, name="article"),
    path("cong-trinh/", views.project_list, name="projects"),
    path("cong-trinh/<slug:slug>/", views.project_detail, name="project"),
]
