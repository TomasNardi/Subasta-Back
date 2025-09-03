from django.db import models
from django.utils import timezone


class Participant(models.Model):
    display_name = models.CharField(max_length=120, blank=True, default="")
    phone = models.CharField(max_length=32, unique=True, null=True, blank=True)
    wa_user_id = models.CharField(max_length=64, unique=True, null=True, blank=True)  # ej "12345@whatsapp"

    class Meta:
        indexes = [
            models.Index(fields=["phone"]),
            models.Index(fields=["wa_user_id"]),
        ]

    def __str__(self):
        return self.display_name or self.phone or self.wa_user_id or "participant"


class WhatsAppGroup(models.Model):
    wa_chat_id = models.CharField(max_length=128, unique=True)  # e.g. "123456@g.us"
    name = models.CharField(max_length=120, blank=True, default="")

    def __str__(self):
        return self.name or self.wa_chat_id


class Auction(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT"
        SCHEDULED = "SCHEDULED"
        RUNNING = "RUNNING"
        PAUSED = "PAUSED"
        FINISHED = "FINISHED"
        CANCELLED = "CANCELLED"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    wa_group = models.ForeignKey(WhatsAppGroup, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name="auctions")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} [{self.status}]"


class Item(models.Model):  # Nueva versión de Product
    auction = models.ForeignKey(Auction, related_name="items", on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    image = models.ImageField(upload_to="products/%Y/%m/%d/", null=True, blank=True)
    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    increment = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    order = models.PositiveIntegerField(default=0)
    is_sold = models.BooleanField(default=False)
    # Opcional pero útil:
    sold_to = models.ForeignKey(Participant, null=True, blank=True, on_delete=models.SET_NULL, related_name="purchases")
    sold_at = models.DateTimeField(null=True, blank=True)

    # 🔽 NUEVOS (los usa Node para publicar/expirar)
    wa_message_id = models.CharField(max_length=128, blank=True, default="")
    wa_stanza_id = models.CharField(max_length=128, blank=True, default="")
    claim_expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["auction_id", "order", "id"]

    def __str__(self):
        return f"{self.name} - ${self.base_price}"


class Rule(models.Model):
    auction = models.ForeignKey(Auction, related_name="rules", on_delete=models.CASCADE)
    key = models.CharField(max_length=100)  # e.g. "claim_keyword", "min_increment", "anti_snipe_sec"
    value = models.CharField(max_length=500)

    class Meta:
        unique_together = ("auction", "key")

    def __str__(self):
        return f"{self.auction_id}:{self.key}={self.value}"


class MessageTemplate(models.Model):
    auction = models.ForeignKey(Auction, related_name="messages", on_delete=models.CASCADE)
    key = models.CharField(max_length=100)  # e.g. "welcome", "next_item", "winner", "outbid"
    template = models.TextField()

    class Meta:
        unique_together = ("auction", "key")

    def __str__(self):
        return f"{self.auction_id}:{self.key}"


class Bid(models.Model):
    item = models.ForeignKey(Item, related_name="bids", on_delete=models.CASCADE)
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(default=timezone.now)
    is_valid = models.BooleanField(default=True)
    source_message_id = models.CharField(max_length=128, blank=True, default="")  # WhatsApp msg id
