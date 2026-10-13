from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from catalog.models import Category, Product
from content.models import Article, Project


class StaticSitemap(Sitemap):
    priority = 0.6

    def items(self):
        return ["core:home", "core:about", "core:contact", "catalog:list", "content:articles",
                "content:projects", "leads:quote", "catalog:suppliers"]

    def location(self, item):
        return reverse(item)


class CategorySitemap(Sitemap):
    priority = 0.8

    def items(self):
        return Category.objects.filter(is_active=True)

    def lastmod(self, o):
        return o.updated_at


class ProductSitemap(CategorySitemap):
    priority = 0.7

    def items(self):
        return Product.objects.filter(is_active=True, category__is_active=True)


class ArticleSitemap(CategorySitemap):
    priority = 0.5

    def items(self):
        return Article.objects.filter(is_published=True)


class ProjectSitemap(CategorySitemap):
    priority = 0.5

    def items(self):
        return Project.objects.filter(is_published=True)


SITEMAPS = {"static": StaticSitemap, "categories": CategorySitemap, "products": ProductSitemap,
            "articles": ArticleSitemap, "projects": ProjectSitemap}
