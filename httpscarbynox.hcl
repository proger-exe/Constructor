# Allow read-write access to secrets under kv/
path "kv/*" {
  capabilities = ["read", "create", "update"]
}
