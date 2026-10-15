# Production deployment configuration

The production Compose file intentionally has no fallback passwords. Supply secrets through the deployment environment or an untracked `.env` file with restrictive permissions; never commit real credentials.

Required variables:

- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`: initialize the bundled PostgreSQL service.
- `DATABASE_URL`: full PostgreSQL URL consumed by the API, using URL-encoded username/password components when they contain reserved characters. It must point to the bundled service (host `postgres`) when using this Compose stack.
- `REDIS_PASSWORD`: password for the bundled Redis service.
- `REDIS_URL`: authenticated Redis URL consumed by the API, pointing to host `redis` when using this Compose stack.

Use distinct, randomly generated credentials for each service. Do not expose the database or Redis ports publicly. The API binds to loopback on port 8000 so a separately configured reverse proxy can terminate HTTPS. Configure that proxy, TLS certificates, firewall rules, and host-level secret management before public exposure.

The named database and Redis volumes persist data across container replacement; they are not backups. Configure and regularly test independent encrypted backups and recovery before production use. Image tags are pinned to major versions here; define an image-update and security-patching process.

Example URL shape (replace placeholders locally; do not use these credentials):
`postgresql://<user>:<url-encoded-password>@postgres:5432/<database>`
`redis://:<url-encoded-password>@redis:6379/0`

## Migration verification

The migration tests cover SQLite idempotence/rollback and, when `DATABASE_URL` points to PostgreSQL, execute the migration in a temporary schema and verify idempotence and rollback. CI provisions PostgreSQL for this test. Rollback drops the initial migration's tables and is destructive; it is only used against an isolated test schema in automated tests.
