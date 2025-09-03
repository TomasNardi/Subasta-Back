from django.contrib import admin

from .models import (Auction , Item)

class TitleAdmin(admin.ModelAdmin):
    pass
    

class ProductAdmin(admin.ModelAdmin):
    pass


admin.site.register(Auction, TitleAdmin)
admin.site.register(Item, ProductAdmin)

