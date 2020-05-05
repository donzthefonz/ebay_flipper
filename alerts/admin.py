from django.contrib import admin
from .models import NotificationRoute, WantedItem, EbayItem


# Register your models here.
class WantedItemAdmin(admin.ModelAdmin):
    list_display = WantedItem.DISPLAY_FIELDS
    search_fields = ('name', 'keywords', 'id', 'customer', 'custcode')
    list_filter = ['deleted']
    ordering = ('-id', 'name')
    pass


admin.site.register(WantedItem, WantedItemAdmin)


class EbayItemAdmin(admin.ModelAdmin):
    list_display = EbayItem.DISPLAY_FIELDS
    search_fields = EbayItem.DISPLAY_FIELDS
    list_filter = ['deleted', 'listing_type', 'passed_filter']
    ordering = ('-id', 'name')
    pass


admin.site.register(EbayItem, EbayItemAdmin)


class NotificationRouteAdmin(admin.ModelAdmin):
    list_display = NotificationRoute.DISPLAY_FIELDS
    search_fields = NotificationRoute.DISPLAY_FIELDS
    list_filter = ['deleted']
    ordering = ('-id', 'name')
    pass


admin.site.register(NotificationRoute, NotificationRouteAdmin)
