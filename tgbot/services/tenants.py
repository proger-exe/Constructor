import asyncio
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional

from cachetools import TTLCache

from tgbot.services.vault import VaultClient


@dataclass(frozen=True)
class TenantContext:
    tenant_uid: str
    bot_token: str
    version: int
    webhook_secret: Optional[str] = None


class TenantService:
    """
    Service for loading tenant-specific secrets from Vault:
    kv/tgbot/tenants/<uid>, with in-memory TTL cache.
    """

    def __init__(
        self, vault: VaultClient, ttl_seconds: int = 60, max_concurrency: int = 10
    ):
        self._vault = vault
        self._cache = TTLCache(maxsize=1000, ttl=ttl_seconds)
        # Limit concurrent Vault reads to avoid thundering herd
        self._sem = asyncio.Semaphore(max_concurrency)

    async def get_context(self, tenant_uid: str) -> TenantContext:
        """
        Get single tenant context from cache or Vault.
        """
        cached = self._cache.get(tenant_uid)
        if cached is not None:
            return cached

        data = await asyncio.to_thread(
            self._vault.read_kv, f"tgbot/tenants/{tenant_uid}"
        )
        token = data.get("bot_token")
        if not token:
            raise RuntimeError(f"Vault: bot_token missing for tenant {tenant_uid}")

        ctx = TenantContext(
            tenant_uid=tenant_uid,
            bot_token=token,
            version=data.get("version", 1),
            webhook_secret=self._extract_secret(data),
        )
        self._cache[tenant_uid] = ctx
        return ctx

    async def get_contexts(self, tenant_uids: List[str]) -> Dict[str, TenantContext]:
        """
        Bulk fetch contexts for many tenants:
        - Returns cached items immediately.
        - Fetches cache misses from Vault concurrently with a semaphore.
        - Preserves order by returning a dict keyed by tenant_uid.
        """
        result: Dict[str, TenantContext] = {}
        to_fetch: List[str] = []

        # First pass: pull from cache
        for uid in tenant_uids:
            cached = self._cache.get(uid)
            if cached is not None:
                result[uid] = cached
            else:
                to_fetch.append(uid)

        if not to_fetch:
            return result

        async def fetch_one(uid: str):
            # Semaphore limits parallelism against Vault
            async with self._sem:
                data = await asyncio.to_thread(
                    self._vault.read_kv, f"tgbot/tenants/{uid}"
                )
            token = data.get("bot_token")
            if not token:
                raise RuntimeError(f"Vault: bot_token missing for tenant {uid}")
            ctx = TenantContext(
                tenant_uid=uid,
                bot_token=token,
                version=data.get("version", 1),
                webhook_secret=self._extract_secret(data),
            )
            # Put into cache and result map
            self._cache[uid] = ctx
            result[uid] = ctx

        # Fetch all misses concurrently
        await asyncio.gather(*(fetch_one(uid) for uid in to_fetch))
        return result

    def put_context(self, ctx: TenantContext):
        """Manually put a tenant context into the cache."""
        self._cache[ctx.tenant_uid] = ctx

    def invalidate(self, tenant_uid: str):
        """Remove a tenant context from the cache."""
        self._cache.pop(tenant_uid, None)

    @staticmethod
    def _extract_secret(data: Mapping[str, object]) -> Optional[str]:
        """Return tenant-specific webhook secret if provided."""
        # support multiple common keys to stay compatible with existing Vault data
        for key in ("webhook_secret", "secret_token", "secret"):
            value = data.get(key)
            if value:
                return value
        return None
