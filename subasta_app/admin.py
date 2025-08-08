from django.contrib import admin

from .models import (Title , Product) 

class TitleAdmin(admin.ModelAdmin):
    pass
    

class ProductAdmin(admin.ModelAdmin):
    pass


admin.site.register(Title, TitleAdmin)
admin.site.register(Product, ProductAdmin)

