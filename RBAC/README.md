# RBAC integration

RBAC is now part of the main `events` app. Its roles, permissions, decorators,
authentication, context processor, and role-change service live under
`events/`; the integrated behavior is configured by `config/settings.py`.

See [`events/docs/rbac.md`](../events/docs/rbac.md) and run migrations/tests from
the repository root. Do not use the standalone project settings in this folder.
