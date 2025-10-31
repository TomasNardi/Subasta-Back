# auctions/views.py
from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes, parser_classes, action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import generics

from django.contrib.auth.models import User
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Auction, Item, Participant, Bid, Rule, MessageTemplate, WhatsAppGroup
)
from .serializers import (
    AuctionSerializer, ItemSerializer, ParticipantSerializer, BidSerializer,
    RuleSerializer, MessageTemplateSerializer, WhatsAppGroupSerializer,
    MyTokenObtainPairSerializer, AdminRegisterSerializer,
    BulkAuctionRulesInputSerializer,
    AssignGroupToAuctionSerializer,
)
from .services import wa_start, wa_close


# Auth / Admin
class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = AdminRegisterSerializer  # o AdminRegisterSerializer (ver abajo)
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        if not s.is_valid():
            return Response({"ok": False, "errors": s.errors}, status=400)
        user = s.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {"ok": True, "user": s.data, "refresh": str(refresh), "access": str(refresh.access_token)},
            status=201,
        )


# Utilidades
@api_view(["GET"])
def keep_alive(request):
    return Response(status=status.HTTP_200_OK)


class BaseAdminPermission(permissions.IsAuthenticated):
    pass


class BaseViewSet(viewsets.ModelViewSet):
    permission_classes = [BaseAdminPermission]

    def get_serializer_context(self):
        # Para que DRF construya URLs absolutas de imágenes
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class AuctionViewSet(BaseViewSet):
    queryset = Auction.objects.all().select_related("wa_group")
    serializer_class = AuctionSerializer

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        auction = self.get_object()
        if auction.status == Auction.Status.RUNNING:
            return Response({"ok": True, "message": "Auction already RUNNING"}, status=200)

        auction.status = Auction.Status.RUNNING
        auction.save(update_fields=["status"])
        try:
            wa_resp = wa_start(auction.id)
        except Exception as e:
            # La subasta en Django queda RUNNING, reportamos el problema
            return Response(
                {"ok": False, "message": "Auction set to RUNNING, but WA start failed", "error": str(e)},
                status=502,
            )
        return Response({"ok": True, "auction_id": auction.id, "wa": wa_resp}, status=200)

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        auction = self.get_object()
        if auction.status != Auction.Status.RUNNING:
            return Response({"ok": False, "message": "Auction is not RUNNING"}, status=409)
        auction.status = Auction.Status.PAUSED
        auction.save(update_fields=["status"])
        return Response({"ok": True, "auction_id": auction.id}, status=200)
    ##POST /auctions/<auction_id>/rules
    @action(detail=True, methods=["post"], url_path="rules")
    def create_rules(self, request, pk=None):
        """
        Carga en bloque las 'reglas visibles' de la subasta.
        Espera:
        {
            "rules": [
                "No ofertas fantasma.",
                "Tenés 5 minutos para reclamar.",
                "Pago inmediato por transferencia."
            ]
        }

        Devuelve las reglas creadas.
        """
        # 1. validar body
        body_serializer = BulkAuctionRulesInputSerializer(data=request.data)
        body_serializer.is_valid(raise_exception=True)
        rule_texts = body_serializer.validated_data["rules"]

        # 2. obtener la subasta
        auction = get_object_or_404(Auction, pk=pk)

        # 3. generar keys únicas tipo RULE_1, RULE_2, ...
        #
        #    - buscamos las que ya existen para esta subasta con ese formato
        #      para continuar numeración y no chocarnos con otras Rule
        #      que usen keys técnicas como "claim_keyword", etc.
        #
        existing_keys = list(
            auction.rules.filter(key__startswith="RULE_").values_list("key", flat=True)
        )

        # sacar el número máximo ya usado en RULE_x
        max_n = 0
        for k in existing_keys:
            # k esperado "RULE_12"
            try:
                n = int(k.split("_", 1)[1])
                max_n = max(max_n, n)
            except (IndexError, ValueError):
                pass

        # 4. crear objetos Rule en memoria
        new_rule_objs = []
        for i, text in enumerate(rule_texts, start=1):
            key = f"RULE_{max_n + i}"
            new_rule_objs.append(
                Rule(
                    auction=auction,
                    key=key,
                    value=text,
                )
            )

        # 5. persistir en bulk
        Rule.objects.bulk_create(new_rule_objs)

        # 6. preparar respuesta con las recién creadas
        created_rules = Rule.objects.filter(
            auction=auction,
            key__in=[r.key for r in new_rule_objs],
        ).order_by("key")

        data_out = RuleSerializer(created_rules, many=True, context={"request": request})

        return Response(
            {
                "auction_id": auction.id,
                "created_rules": data_out.data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["patch"], url_path="assign-group")
    def assign_group(self, request, pk=None):
        """
        Asocia un WhatsAppGroup existente a esta subasta.

        Request body:
        {
            "wa_group_id": 7
        }

        Donde '7' es el ID interno de WhatsAppGroup (PK en tu tabla).
        """
        # 1. validar body
        serializer = AssignGroupToAuctionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        wa_group_id = serializer.validated_data["wa_group_id"]

        # 2. buscar auction y grupo
        auction = get_object_or_404(Auction, pk=pk)
        wa_group = get_object_or_404(WhatsAppGroup, pk=wa_group_id)

        # 3. asociar
        auction.wa_group = wa_group
        auction.save(update_fields=["wa_group"])

        # 4. responder la subasta actualizada
        response_data = AuctionSerializer(auction, context={"request": request}).data
        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def finish(self, request, pk=None):
        auction = self.get_object()
        if auction.status in (Auction.Status.FINISHED, Auction.Status.CANCELLED):
            return Response({"ok": True, "message": f"Auction already {auction.status}"}, status=200)

        auction.status = Auction.Status.FINISHED
        auction.ends_at = auction.ends_at or auction.created_at  # o timezone.now()
        auction.save(update_fields=["status", "ends_at"])

        # Avisar a Node para que cierre si corresponde
        try:
            wa_resp = wa_close(auction.id)
        except Exception as e:
            return Response(
                {"ok": True, "message": "Auction finished in Django, WA close failed", "error": str(e)},
                status=200,
            )
        return Response({"ok": True, "auction_id": auction.id, "wa": wa_resp}, status=200)


class ItemViewSet(BaseViewSet):
    queryset = Item.objects.all().select_related("auction", "sold_to")
    serializer_class = ItemSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)


class ParticipantViewSet(BaseViewSet):
    queryset = Participant.objects.all()
    serializer_class = ParticipantSerializer


class BidViewSet(BaseViewSet):
    queryset = Bid.objects.select_related("item", "participant").all()
    serializer_class = BidSerializer
    http_method_names = ["get", "head", "options", "delete"]  # Node inserta directo; admin puede borrar si es necesario


class RuleViewSet(BaseViewSet):
    queryset = Rule.objects.select_related("auction").all()
    serializer_class = RuleSerializer


class MessageTemplateViewSet(BaseViewSet):
    queryset = MessageTemplate.objects.select_related("auction").all()
    serializer_class = MessageTemplateSerializer


class WhatsAppGroupViewSet(BaseViewSet):
    queryset = WhatsAppGroup.objects.all()
    serializer_class = WhatsAppGroupSerializer
    http_method_names = ["get", "post", "head", "options"]


#
# Carga múltiple de items desde un form-data con estructura:
#   productos[0][title], productos[0][price], productos[0][image]
# Opcionales:
#   productos[i][description], productos[i][increment], productos[i][order]
#   auction_id (si no se envía, se crea una Auction con título 'Untitled Auction')
#   auction_title (solo si no se envía auction_id)
#
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def crear_subasta_api(request):
    productos = []
    i = 0
    while True:
        key_title = f"productos[{i}][title]"
        key_price = f"productos[{i}][price]"
        key_image = f"productos[{i}][image]"
        if key_title in request.data or key_price in request.data or key_image in request.data:
            producto_data = {
                # mapeo a Item:
                "name": request.data.get(key_title),
                "base_price": request.data.get(key_price),
                "image": request.data.get(key_image),
                "description": request.data.get(f"productos[{i}][description]", ""),
                "increment": request.data.get(f"productos[{i}][increment]", 0),
                "order": request.data.get(f"productos[{i}][order]", i),
            }
            productos.append(producto_data)
            i += 1
        else:
            break

    if not productos:
        return Response({"error": "No products received"}, status=status.HTTP_400_BAD_REQUEST)

    auction_id = request.data.get("auction_id")
    auction = None
    if auction_id:
        auction = get_object_or_404(Auction, pk=auction_id)
    else:
        title = request.data.get("auction_title", "Untitled Auction")
        auction = Auction.objects.create(title=title)

    created = 0
    errors = []

    # Usamos transaction para que o bien se creen todos los items o ninguno
    with transaction.atomic():
        for idx, producto_data in enumerate(productos):
            # Inyectar FK al serializer
            producto_data["auction"] = auction.id
            serializer = ItemSerializer(data=producto_data)
            if serializer.is_valid():
                serializer.save()
                created += 1
            else:
                errors.append({"index": idx, "errors": serializer.errors})

        if errors:
            # rollback
            transaction.set_rollback(True)
            return Response(
                {"ok": False, "auction_id": auction.id, "created": created, "errors": errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    return Response(
        {"ok": True, "auction_id": auction.id, "created": created},
        status=status.HTTP_201_CREATED,
    )
