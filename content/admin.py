from django.contrib import admin

from .models import Article, ArticleCategory, Project, ProjectImage


@admin.register(ArticleCategory)
class ArticleCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name"]


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "is_published", "published_at", "is_demo", "updated_at"]
    list_filter = ["is_published", "category", "is_demo"]
    search_fields = ["title"]
    autocomplete_fields = []
    filter_horizontal = ["related_products"]
    readonly_fields = ["created_at", "updated_at"]


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["title", "location", "project_type", "is_published", "sort_order", "is_demo", "updated_at"]
    list_filter = ["is_published", "is_demo"]
    search_fields = ["title", "location"]
    list_editable = ["is_published", "sort_order"]
    filter_horizontal = ["products"]
    inlines = [ProjectImageInline]
    readonly_fields = ["created_at", "updated_at"]
