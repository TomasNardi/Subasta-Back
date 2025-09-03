from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static

from .views import (
    AuctionViewSet, ItemViewSet, ParticipantViewSet, BidViewSet,
    RuleViewSet, MessageTemplateViewSet, WhatsAppGroupViewSet,
    keep_alive, crear_subasta_api,
    # Auth
    MyTokenObtainPairView, RegisterView,
)

router = DefaultRouter()
router.register(r"auctions", AuctionViewSet, basename="auction")
router.register(r"items", ItemViewSet, basename="item")
router.register(r"participants", ParticipantViewSet, basename="participant")
router.register(r"bids", BidViewSet, basename="bid")
router.register(r"rules", RuleViewSet, basename="rule")
router.register(r"messages", MessageTemplateViewSet, basename="message-template")
router.register(r"whatsapp-groups", WhatsAppGroupViewSet, basename="whatsapp-group")

urlpatterns = [
    # API REST principal
    path("api/", include(router.urls)),

    # (Opcional / legacy)
    path("api/subastas/crear/", crear_subasta_api, name="crear_subasta_api"),

    # Healthcheck local
    path("keep-alive/", keep_alive, name="keep_alive"),

    # Auth (admin-only)
    path("api/auth/login/", MyTokenObtainPairView.as_view(), name="auth_login"),
    path("api/auth/register/", RegisterView.as_view(), name="auth_register"),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]

# Servir media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
