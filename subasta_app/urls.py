from django.urls import path
from .views import crear_subasta_api, keep_alive
# create_superuser
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('api/subastas/crear/', crear_subasta_api, name='crear_subasta_api'),

    # Endpoint para mantener el servidor vivo
    path('keep-alive/', keep_alive, name='keep_alive'),

    # This route should be commented for security reasons
    # path('create-superuser/', create_superuser, name='create_superuser'),  
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
