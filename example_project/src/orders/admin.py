from django.contrib import admin

from .models.order import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ("id", "product", "quantity", "price_at_purchase")
    readonly_fields = ("id",)
    extra = 0
    show_change_link = True
    raw_id_fields = ("product",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "date", "total")
    list_per_page = 25
    search_fields = ("id",)
    readonly_fields = ("id", "date")
    ordering = ("-date",)
    date_hierarchy = "date"
    fieldsets = (
        (None, {"fields": ("id", "date")}),
        ("Totals", {"fields": ("total",)}),
    )
    inlines = [OrderItemInline]
