from __future__ import annotations

from tgbot.common.logging_setup import tenant_id_var
from tgbot.common.logging_setup import log
from tgbot.database.managers import TenantManager
from tgbot.database.models import Tenant


async def get_current_tenant() -> Tenant:
    """Resolve the current tenant using the context variable set by webhook handler."""

    tenant_uid = tenant_id_var.get()
    if not tenant_uid or tenant_uid == "-":
        raise LookupError("Tenant context is not available")

    tenant = await TenantManager.get_by_uid(tenant_uid)
    if tenant is None:
        log.warning("tenant_missing", extra={"tenant_uid": tenant_uid})
        raise LookupError(f"Tenant with uid '{tenant_uid}' was not found")

    return tenant
