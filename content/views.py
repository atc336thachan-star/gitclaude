from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .models import Article, ArticleCategory, Project


def article_list(request, cat=None):
    qs = Article.objects.filter(is_published=True).select_related("category")
    category = None
    if cat:
        category = get_object_or_404(ArticleCategory, slug=cat)
        qs = qs.filter(category=category)
    page = Paginator(qs, 9).get_page(request.GET.get("page"))
    return render(request, "content/article_list.html", {
        "page": page, "category": category, "categories": ArticleCategory.objects.all(),
        "items": [("Kiến thức vật liệu", None)] if not category else [("Kiến thức vật liệu", reverse("content:articles")), (category.name, None)]})


def article_detail(request, slug):
    article = get_object_or_404(Article.objects.select_related("category"), slug=slug, is_published=True)
    related = Article.objects.filter(is_published=True, category=article.category).exclude(pk=article.pk)[:3] if article.category_id else []
    return render(request, "content/article_detail.html", {
        "article": article, "related": related,
        "items": [("Kiến thức vật liệu", reverse("content:articles")), (article.title, None)],
        "products": article.related_products.filter(is_active=True).prefetch_related("images")[:4]})


def project_list(request):
    page = Paginator(Project.objects.filter(is_published=True), 9).get_page(request.GET.get("page"))
    return render(request, "content/project_list.html", {"page": page, "items": [("Công trình", None)]})


def project_detail(request, slug):
    project = get_object_or_404(Project.objects.prefetch_related("images"), slug=slug, is_published=True)
    return render(request, "content/project_detail.html", {
        "project": project, "items": [("Công trình", reverse("content:projects")), (project.title, None)],
        "products": project.products.filter(is_active=True).select_related("category").prefetch_related("images")[:4]})
