from django.contrib import admin

from core.models import PieceWarehouse, Warehouse

# Register your models here.

admin.site.register(Warehouse)
admin.site.register(PieceWarehouse)