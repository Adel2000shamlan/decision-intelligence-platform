# Backup, recovery, monitoring, and go-live runbook

This runbook is an operational checklist, not evidence that a live deployment has already been tested. Do not declare production ready until the restore drill and application smoke test have passed in the target environment.

## 1. Preconditions and secret handling

- Use a dedicated host/VM, a non-root deployment account, patched Docker/Compose, firewall rules, and a TLS reverse proxy.
- Store distinct high-entropy PostgreSQL and Redis credentials in the deployment secret store or an untracked .env file readable only by the deployment account (for example, mode 600). Never paste secrets into issues, logs, or Git.
- DATABASE_URL must target the postgres service and match POSTGRES_DB, POSTGRES_USER, and POSTGRES_PASSWORD; REDIS_URL must authenticate to redis.
- Keep PostgreSQL and Redis ports off the public host interface. The API is bound to host loopback; expose it only through a configured TLS reverse proxy.
- Verify Dockerfile.prod starts Uvicorn and Compose reports the API healthy. The health endpoint currently reports process/API availability only; it is not a database or Redis readiness check.

## 2. PostgreSQL backup

Create an encrypted backup outside the repository and outside the Docker volume. Run from the deployment host with Compose variables available:

```sh
umask 077
mkdir -p backups
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
docker compose -f docker-compose.prod.yml exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "backups/postgres-$stamp.dump"
test -s "backups/postgres-$stamp.dump"
```

Encrypt the dump with the organization-approved key management process and transfer a copy to a separate account/location. The command above creates a plaintext dump until encryption is complete; protect the directory and encrypt immediately. Define and record RPO/RTO targets before launch. Schedule backups and alert on failed/missing backups; a backup file existing is not proof it can be restored.

## 3. Restore drill (destructive if aimed at production)

Perform this only against a separate disposable database/service, never the live production database:

```sh
# Create a disposable target database using the configured PostgreSQL service.
docker compose -f docker-compose.prod.yml exec -T postgres sh -c 'createdb -U "$POSTGRES_USER" restore_drill'
# Restore a verified dump into the disposable database.
docker compose -f docker-compose.prod.yml exec -T postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d restore_drill --clean --if-exists' < backups/VERIFIED_BACKUP.dump
# Validate schema and representative business records, then record elapsed time.
docker compose -f docker-compose.prod.yml exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d restore_drill -v ON_ERROR_STOP=1 -c "\dt"'
# Drop only the disposable database after review.
docker compose -f docker-compose.prod.yml exec -T postgres sh -c 'dropdb -U "$POSTGRES_USER" restore_drill'
```

Replace the dump path with the exact verified artifact. If backups are encrypted, decrypt to a protected temporary stream/file first. Never run restore/clean against the production database as a test. Record backup timestamp, checksum, encryption/key version, restore start/end, validation results, RPO/RTO achieved, operator, and corrective actions. Repeat quarterly and after material schema/backup changes.

## 4. Redis and state boundaries

Redis has append-only persistence enabled, but its named volume is not a backup and should not be treated as the authoritative record for business decisions. Confirm which data is cache/ephemeral and which is durable before relying on Redis persistence. If Redis stores non-reconstructible state, add a separate backup/restore procedure and restore drill before launch.

## 5. Monitoring and alerting

At minimum, collect and alert on:
- API health endpoint failures and container restart loops.
- HTTP 5xx rate, request latency (p50/p95/p99), traffic, and request IDs.
- Host CPU, memory, disk/inode usage, container memory, and PostgreSQL volume disk space.
- PostgreSQL connectivity, connection saturation, slow queries, locks, failed migrations, backup age/failure, and restore-drill outcomes.
- Redis availability, memory/evictions, persistence status, and authentication errors.
- Authentication/authorization failures, tenant-boundary violations, and suspicious access, without logging credentials or sensitive payloads.

Use an external uptime check through the TLS endpoint. Keep structured logs centrally with retention/access controls; synchronize host clocks. Set named owners and escalation routes. The health endpoint is liveness only; implement separate dependency/readiness checks before claiming full operational observability.

## 6. Go-live checklist

- [ ] CI passes on the exact release commit, including PostgreSQL integration tests.
- [ ] Review and approve PRs; release from a known, tagged commit. Do not deploy stacked feature branches directly.
- [ ] Compose config validates and all containers become healthy.
- [ ] TLS, reverse proxy, firewall, domain, security headers, and rate limits are verified externally.
- [ ] No default/committed secrets; secret rotation and emergency access are documented.
- [ ] Migration plan reviewed, tested against a copy, and has an approved recovery path.
- [ ] Encrypted off-host backup completed and a restore drill passed; RPO/RTO recorded.
- [ ] Monitoring, alert routing, log retention, on-call ownership, and incident runbook verified.
- [ ] API smoke tests and security/tenant-isolation checks pass against staging.
- [ ] Rollback/release procedure tested; data rollback strategy is explicit and does not assume code rollback reverses schema/data changes.
- [ ] Human approval remains required for consequential decisions; AI analysis must not autonomously approve or execute them.

## 7. Current limits

Automated CI verifies code/tests against a temporary PostgreSQL service. It does not prove live backup scheduling, encryption, off-site retention, successful recovery of real data, external monitoring, TLS/reverse proxy, load capacity, or production security. Mark those items complete only with dated evidence from the target environment.
