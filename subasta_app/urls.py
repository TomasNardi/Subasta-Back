from django.urls import path
from .views import crear_subasta_api
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('api/subastas/crear/', crear_subasta_api, name='crear_subasta_api'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
