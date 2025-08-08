from django.urls import path
from .views import crear_subasta_api, create_superuser
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('api/subastas/crear/', crear_subasta_api, name='crear_subasta_api'),
    path('create-superuser/', create_superuser, name='create_superuser'),  # NO ES API
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)