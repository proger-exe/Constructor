"""Database model definition module."""

from tortoise import fields
from tortoise.models import Model


class User(Model):
    """User database model."""

    numeric_id = fields.BigIntField(pk=True)
    tg_id = fields.BigIntField(unique=True)
    balance = fields.BigIntField(default=0)
    ban = fields.BooleanField(default=False)
    register_date = fields.DatetimeField(auto_now_add=True)

    def __str__(self):
        return f"User: {self.tg_id}"


class Tenant(Model):
    """
    Tenant data. Unique identifier for webhook - UUID.
    """

    numeric_id = fields.BigIntField(pk=True)
    owner_id = fields.BigIntField()
    uuid = fields.CharField(max_length=255, unique=True)
    name = fields.CharField(max_length=255, null=True)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "tenants"


class TenantUser(Model):
    id = fields.BigIntField(pk=True)
    full_name = fields.CharField()

    def __str__(self):
        return f"Tenant User: {self.id}"

    class Meta:
        table = "tenant_user"


class TenantLocale(Model):
    id = fields.BigIntField(pk=True)
    tenant = fields.ForeignKeyField(
        "models.Tenant", related_name="locales", on_delete=fields.CASCADE
    )
    type = fields.CharField(max_length=255)
    name = fields.CharField(max_length=255)
    text = fields.TextField()
    lang = fields.CharField(default="ru", max_length=10)

    def __str__(self):
        tenant = getattr(self, "tenant", None)
        tenant_repr = getattr(tenant, "uuid", None) or getattr(tenant, "numeric_id", "-")
        return (
            "Locale: "
            f"tenant={tenant_repr} "
            f"[{self.type}] - {self.lang} / {self.text[:30]}..."
        )

    class Meta:
        table = "tenant_locale"
        unique_together = ("tenant", "type", "lang")
