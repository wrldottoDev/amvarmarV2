from django.contrib import admin
from django.urls import path, include
from core.urls import urlpatterns
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include(urlpatterns)),
    path('admin/', admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
