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
    type = fields.CharField()
    name = fields.CharField()
    text = fields.TextField()
    lang = fields.CharField(default="ru")  # if don't need - delete it later.

    def __str__(self):
        return f"Locale: [{self.type}] - {self.lang} / {self.text[:30]}..."

    class Meta:
        table = "tenant_locale"
