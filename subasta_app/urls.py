from django.urls import path
from .views import crear_subasta_api, keep_alive, RegisterView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("api/subastas/crear/", crear_subasta_api, name="crear_subasta_api"),
    path("keep-alive/", keep_alive, name="keep_alive"),

    # Auth
    path("api/register/", RegisterView.as_view(), name="register"),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
