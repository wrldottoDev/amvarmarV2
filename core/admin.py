from django.contrib import admin

from core.models import Warehouse, PieceWarehouse, DispatchRequest, DispatchRequestItem

admin.site.register(Warehouse)
admin.site.register(PieceWarehouse)
admin.site.register(DispatchRequest)
admin.site.register(DispatchRequestItem)