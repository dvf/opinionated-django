from django.contrib import admin

from .models.product import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price", "stock")
    list_per_page = 25
    search_fields = ("id", "name")
    readonly_fields = ("id",)
    ordering = ("-id",)
    fieldsets = (
        (None, {"fields": ("id",)}),
        ("Details", {"fields": ("name", "price", "stock")}),
    )
