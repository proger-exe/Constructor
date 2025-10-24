from .admin import admin_router
from .tenant.admin import admin_router as tenant_admin_router
from .tenant.user import user_tenant_router
from .user import user_router

__all__ = (
    "admin_router",
    "tenant_admin_router",
    "user_tenant_router",
    "user_router",
)
