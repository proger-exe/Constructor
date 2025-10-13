# tgbot/services/vault.py
import time
from typing import Dict, Optional, Tuple

import hvac


class VaultClient:
    """
    Minimal Vault KV v2 client with optional AppRole auth and a simple TTL cache.
    Works with modern hvac (client.auth.approle.login).
    """

    def __init__(
        self,
        *,
        addr: str,
        mount: str = "kv",
        token: Optional[str] = None,
        role_id: Optional[str] = None,
        secret_id: Optional[str] = None,
        ttl: int = 60,
        verify: bool | str = False,  # bool or path to CA bundle
    ):
        self.addr = addr
        self.mount = mount
        self._token = token
        self._role_id = role_id
        self._secret_id = secret_id
        self._ttl = ttl
        self._cache: Dict[str, Tuple[float, Dict]] = {}

        # Do NOT default to verify=False in prod. Pass a CA path if needed.
        self._client = hvac.Client(url=addr, verify=verify)

        self._login()

    def _login(self) -> None:
        """
        Authenticate either with a pre-issued token or via AppRole.
        Modern hvac uses client.auth.approle.login(role_id=..., secret_id=...).
        """
        if self._token:
            self._client.token = self._token
            return

        if self._role_id and self._secret_id:
            # hvac >= 0.11 supports this style
            self._client.auth.approle.login(
                role_id=self._role_id,
                secret_id=self._secret_id,
            )
            if not self._client.is_authenticated():
                raise RuntimeError("Vault AppRole login failed")
            return

        raise RuntimeError("Vault credentials missing (token or AppRole)")

    def _fresh(self, key: str) -> Optional[Dict]:
        item = self._cache.get(key)
        if not item:
            return None
        ts, value = item
        if (time.time() - ts) > self._ttl:
            return None
        return value

    def read_kv(self, path: str) -> Dict:
        """
        Read KV v2 secret at `path` (relative to mount), with TTL cache.
        Returns the inner 'data' dict (not metadata).
        """
        cached = self._fresh(path)
        if cached is not None:
            return cached

        resp = self._client.secrets.kv.v2.read_secret_version(
            mount_point=self.mount,
            path=path,
        )
        data = resp["data"]["data"]
        self._cache[path] = (time.time(), data)
        return data

    def write_kv(self, path: str, data: Dict) -> None:
        """
        Create/update KV v2 secret and refresh local cache.
        """
        self._client.secrets.kv.v2.create_or_update_secret(
            mount_point=self.mount,
            path=path,
            secret=data,
        )
        self._cache[path] = (time.time(), data)

    def delete_kv(self, path: str) -> None:
        """
        Delete KV v2 secret metadata and all versions; drop from cache.
        """
        self._client.secrets.kv.v2.delete_metadata_and_all_versions(
            mount_point=self.mount,
            path=path,
        )
        self._cache.pop(path, None)

    def clear_cache(self, prefix: Optional[str] = None) -> None:
        """
        Clear entire cache or only entries with a given prefix.
        """
        if prefix is None:
            self._cache.clear()
            return
        for k in list(self._cache.keys()):
            if k.startswith(prefix):
                del self._cache[k]
