from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Agregar info adicional al token
        token['username'] = user.username
        return token


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
        return user


# auctions/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Auction, Item, Rule, MessageTemplate, Participant, WhatsAppGroup, Bid


# ----------------------------
# Auth / Admin
# ----------------------------

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        return token


class AdminRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )
        user.is_staff = True  # marcar como admin del panel
        user.save()
        return user


# Core domain

class WhatsAppGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppGroup
        fields = ("id", "wa_chat_id", "name")


class RuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rule
        fields = ("id", "key", "value")


class MessageTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageTemplate
        fields = ("id", "key", "template")


class ItemSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, allow_null=True)
    highest_bid = serializers.SerializerMethodField()
    bids_count = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = (
            "id",
            "auction",
            "name",
            "description",
            "image",
            "base_price",
            "increment",
            "order",
            "is_sold",
            "sold_to",
            "sold_at",
            # 👇 campos que usa el servicio de WhatsApp (solo lectura)
            "wa_message_id",
            "wa_stanza_id",
            "claim_expires_at",
            # métricas
            "highest_bid",
            "bids_count",
        )
        read_only_fields = (
            "is_sold",
            "sold_to",
            "sold_at",
            "wa_message_id",
            "wa_stanza_id",
            "claim_expires_at",
            "highest_bid",
            "bids_count",
        )

    def get_highest_bid(self, obj):
        b = obj.bids.order_by("-amount").only("amount").first()
        return str(b.amount) if b else None

    def get_bids_count(self, obj):
        return obj.bids.count()

class AuctionSerializer(serializers.ModelSerializer):
    wa_group = WhatsAppGroupSerializer(read_only=True)
    wa_group_id = serializers.PrimaryKeyRelatedField(
        queryset=WhatsAppGroup.objects.all(), source="wa_group", write_only=True, required=False
    )
    items = ItemSerializer(many=True, read_only=True)
    rules = RuleSerializer(many=True, read_only=True)
    messages = MessageTemplateSerializer(many=True, read_only=True)

    class Meta:
        model = Auction
        fields = (
            "id",
            "title",
            "description",
            "status",
            "starts_at",
            "ends_at",
            "wa_group",
            "wa_group_id",
            "items",
            "rules",
            "messages",
            "created_at",
        )
        read_only_fields = ("created_at",)


class ParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participant
        fields = ("id", "display_name", "phone", "wa_user_id")
        extra_kwargs = {
            "phone": {"required": False, "allow_null": True, "allow_blank": True},
            "wa_user_id": {"required": False, "allow_null": True, "allow_blank": True},
        }


class BidSerializer(serializers.ModelSerializer):
    participant = ParticipantSerializer(read_only=True)

    class Meta:
        model = Bid
        fields = (
            "id",
            "item",
            "participant",
            "amount",
            "created_at",
            "is_valid",
            "source_message_id",
            "source_chat_id",
        )
        read_only_fields = ("created_at",)
